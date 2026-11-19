#!/usr/bin/env node
// Probe search on the LIVE docs site the way a visitor uses it.
//
// Search broke in production before with a green build, because CI never
// talks to the deployed site. This script does: it fetches the pages the
// deployed site serves, drives the real search modal of
// @easyops-cn/docusaurus-search-local in a headless browser, and opens the
// top hit pages the results link to. It holds no credentials: the search
// index is built from our own pages at deploy time, so there is nothing to
// read out of the bundle and no external search service to query.
//
// Usage: node website/scripts/check-live-search.mjs [--no-browser]
//   DOCS_URL       site to probe (default https://thor726.github.io/Thor-agent/docs)
//   PLAYWRIGHT_DIR directory holding node_modules/playwright (browser check)
// Exit 0 = search works; exit 1 = broken. Reasons go to stderr and, in
// Actions, to the step summary and `::error::` annotations (alert receivers
// read the annotations off the failed run).

import { appendFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

const DOCS_URL = (process.env.DOCS_URL || 'https://thor726.github.io/Thor-agent/docs').replace(/\/$/, '');
const ORIGIN = new URL(DOCS_URL).origin;
// Terms that must always match many pages; one per major area of the docs.
const QUERIES = ['telegram', 'install', 'skills'];
// Every request (body included) gets a deadline, and the whole probe gets one,
// so a slow-drip server fails the check with time left to retry and alert
// instead of running into the job's timeout.
const REQUEST_TIMEOUT_MS = 20_000;
// The browser check alone can take ~2 min: the lunr index is ~37 MB and the
// worker parses every block before the first hit renders. The deadline has to
// cover index download + parse + query, with headroom for the job's retry.
const PROBE_DEADLINE_MS = 420_000;
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36 thor-docs-search-monitor';

const failures = [];
const fail = (msg) => {
  failures.push(msg);
  console.error(`FAIL ${msg}`);
  if (process.env.GITHUB_ACTIONS) console.log(`::error title=Docs search::${msg.replace(/%/g, '%25').replace(/\r/g, '%0D').replace(/\n/g, '%0A')}`);
};
const ok = (msg) => console.log(`ok   ${msg}`);

async function get(url, headers = {}) {
  const res = await fetch(url, {
    headers: { 'user-agent': UA, ...headers },
    redirect: 'follow',
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  return { res, body: await res.text() };
}

// An auth wall or rate limiter answers 401/403/429 with an HTML page of its
// own; name that instead of "bad status".
function blockedBy(res) {
  if (res.status === 401) return 'auth wall (401)';
  if (res.status === 403 || res.status === 429) return `HTTP ${res.status}`;
  return null;
}

// The search-local plugin emits a search page (sitemap-excluded) plus
// per-locale index chunks the modal hydrates from. Verify the search page is
// served and looks like the docs site; the modal itself is exercised in the
// browser check below, which is the user-visible truth (index file naming
// differs across plugin versions, so guessing paths here only gives false
// alarms — the browser check fails loudly if the index is missing).
async function checkSearchPage() {
  const { res, body } = await get(`${DOCS_URL}/search/`);
  const block = blockedBy(res);
  if (block || !res.ok) {
    fail(`search page ${DOCS_URL}/search/ is not reachable for visitors: ${block || `HTTP ${res.status}`}`);
    return;
  }
  if (!body.includes('docusaurus')) {
    fail(`search page ${DOCS_URL}/search/ does not look like the docs site (no Docusaurus marker in HTML)`);
    return;
  }
  ok(`search page served (${DOCS_URL}/search/)`);
}

async function checkBrowser() {
  const require = createRequire(path.join(process.env.PLAYWRIGHT_DIR || process.cwd(), 'noop.js'));
  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ userAgent: UA });
    const failedRequests = [];
    page.on('requestfailed', (r) => {
      if (r.url().startsWith(ORIGIN)) failedRequests.push(`${r.failure()?.errorText} ${r.url().split('?')[0]}`);
    });
    await page.goto(`${DOCS_URL}/`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
    // search-local renders the input inline in the navbar on wide screens; on
    // narrow ones it is a button ('ctrl K') that opens it, and the input only
    // exists after hydration — give that a moment before probing.
    const input = page.locator('.navbar__search input, input[type=search]').first();
    try {
      await input.waitFor({ state: 'visible', timeout: 10_000 });
    } catch {
      await page.waitForTimeout(2_500);
      if (!(await input.isVisible().catch(() => false))) {
        await page.locator('.navbar__search button, button[class*=search i]').first().click({ timeout: 10_000 }).catch(() => {});
        await input.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {});
      }
    }
    if (!(await input.isVisible().catch(() => false))) {
      fail('search input never appeared in the navbar within 20s (search plugin not hydrated?)');
      return [];
    }
    // search-local only downloads the lunr index (docs/search-index.json —
    // ~37 MB on this site) when the modal first opens, and the worker then
    // parses all blocks before the first hit renders. On a CI runner that
    // easily outlives a short fixed wait, so: wait for the worker's index
    // request to finish, then give the query a generous deadline.
    await input.click({ timeout: 10_000 }).catch(() => {});
    await page
      .waitForResponse((r) => r.url().includes('search-index') && r.status() === 200, { timeout: 60_000 })
      .catch(() => {});
    await input.fill(QUERIES[1], { timeout: 10_000 });
    // Results render below the input as the worker finishes each query.
    const hit = page.locator('[class*="hit"] a, [class*="dropdown-item"], [role="option"]').first();
    try {
      await hit.waitFor({ state: 'visible', timeout: 60_000 });
    } catch {
      const shown = (await page.locator('.navbar__search').innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 200);
      fail(`search showed no results for "${QUERIES[1]}" (${failedRequests.slice(0, 2).join('; ') || 'no failed request seen'}; navbar: "${shown}")`);
      return [];
    }
    const hits = await page.locator('[class*="hit"] a, [class*="dropdown-item"], [role="option"]').count();
    ok(`browser: search lists ${hits} results for "${QUERIES[1]}"`);
    const href = await hit.getAttribute('href');
    return href ? [href.startsWith('http') ? href : new URL(href, DOCS_URL).href] : [];
  } finally {
    await browser.close();
  }
}

async function checkHitPagesOpen(urls) {
  for (const url of urls) {
    const { res } = await get(url);
    const block = blockedBy(res);
    if (block || !res.ok) fail(`search result ${url} does not open: ${block || `HTTP ${res.status}`}`);
    else ok(`result opens: ${url}`);
  }
}

async function probe() {
  await checkSearchPage();
  if (!process.argv.includes('--no-browser')) {
    const urls = await checkBrowser().catch((e) => {
      fail(`browser check crashed: ${e.message.split('\n')[0]}`);
      return [];
    });
    await checkHitPagesOpen(urls);
  }
}

// One exit path for clean failures, thrown errors and the deadline, so the
// alert always carries the real reason.
function finish() {
  if (process.env.GITHUB_STEP_SUMMARY) {
    const lines = failures.length ? failures.map((f) => `- ${f}`) : ['- all checks passed'];
    appendFileSync(process.env.GITHUB_STEP_SUMMARY, `### Docs search (${DOCS_URL})\n${lines.join('\n')}\n`);
  }
  process.exit(failures.length ? 1 : 0);
}

setTimeout(() => {
  fail(`probe did not finish within ${PROBE_DEADLINE_MS / 1000}s`);
  finish();
}, PROBE_DEADLINE_MS).unref();
probe()
  .catch((e) => fail(`probe crashed: ${e.cause?.message || e.message}`))
  .finally(finish);
