# Shared clean-checkout assertion for the install/update E2E drivers.
#
# The drivers stage a bare clone of the checkout as serve.git, so the
# checkout must be a reviewable commit: any uncommitted TRACKED change
# means HEAD is not the code being reviewed. Untracked files cannot leak
# into the clone, so they are ignored (-uno).
#
# One exception: a file whose blob stores CRLF while .gitattributes says
# `text eol=crlf` (in this repo, only scripts/install.ps1) looks modified
# wholesale the moment anything invalidates git's stat cache for it -- a
# touch, a checkout race -- although no content changed. A bare clone
# serves committed objects, so such a worktree line-ending artifact cannot
# leak into serve.git anyway: the tree counts as clean when the only
# differences are CR at end of line.
#
# Usage: source this file, then
#   assert_clean_checkout "$REPO_ROOT" \
#     || fail "checkout has uncommitted tracked changes; ..."
# Exit status is the contract: 0 clean (or CR-only differences), 1 dirty.
# A dirty tree prints the `git status` list to stderr, so the next failure
# names the file instead of failing silently.

assert_clean_checkout() {
  local repo_root="$1"
  local status
  status="$(git -C "$repo_root" status --porcelain -uno)" || return 1
  [ -z "$status" ] && return 0
  if git -C "$repo_root" diff --ignore-cr-at-eol --quiet \
    && git -C "$repo_root" diff --cached --ignore-cr-at-eol --quiet; then
    printf '  [e2e] ignoring CR-at-EOL-only worktree differences:\n%s\n' "$status"
    return 0
  fi
  printf 'E2E ASSERTION FAILED: checkout has uncommitted tracked changes:\n%s\n' "$status" >&2
  return 1
}
