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
const PROBE_DEADLINE_MS = 240_000;
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

// The search-local plugin emits a search page (sitemap-excluded) plus the
// per-locale index chunks the modal hydrates from. Verify the search page is
// served and links at least one index chunk that actually downloads.
async function checkSearchPage() {
  const { res, body } = await get(`${DOCS_URL}/search/`);
  const block = blockedBy(res);
  if (block || !res.ok) {
    fail(`search page ${DOCS_URL}/search/ is not reachable for visitors: ${block || `HTTP ${res.status}`}`);
    return [];
  }
  if (!body.includes('docusaurus')) {
    fail(`search page ${DOCS_URL}/search/ does not look like the docs site (no Docusaurus marker in HTML)`);
    return [];
  }
  ok(`search page served (${DOCS_URL}/search/)`);

  // The worker chunk references search-index{dir}.json; the index itself is
  // split per locale. Probe the locales the site builds (en + zh-Hans).
  const locales = ['en', 'zh-Hans'];
  const reachable = [];
  for (const locale of locales) {
    // search-local names the file after the htmlLang: en.json, zh-Hans.json.
    const url = `${DOCS_URL}/search-index/${locale}.json`;
    const { res: idxRes } = await get(url);
    if (idxRes.ok) {
      ok(`search index chunk downloads: /search-index/${locale}.json`);
      reachable.push(locale);
    } else {
      fail(`search index chunk /search-index/${locale}.json returns HTTP ${idxRes.status}; the modal will find no documents`);
    }
  }
  return reachable;
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
    // search-local renders the input inline in the navbar (no button to click
    // first like DocSearch); wait for it to appear after hydration.
    const input = page.locator('.navbar__search input, input[type=search]').first();
    try {
      await input.waitFor({ state: 'visible', timeout: 20_000 });
    } catch {
      fail('search input never appeared in the navbar within 20s (search plugin not hydrated?)');
      return [];
    }
    await input.fill(QUERIES[1], { timeout: 10_000 });
    // Results render below the input as the worker finishes each query.
    const hit = page.locator('[class*="hit"] a, [class*="dropdown-item"], [role="option"]').first();
    try {
      await hit.waitFor({ state: 'visible', timeout: 20_000 });
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
