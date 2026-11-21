#!/usr/bin/env bash
# Publish site/ to the gh-pages branch, then make sure Pages is on.
#
#   bash scripts/deploy_pages.sh
#
# gh-pages carries only the built page (index.html), because that is what the
# report needs; the sources stay on main. GitHub's Pages build is "legacy", same
# as the other repos in this account, so the URL is
# https://<owner>.github.io/<repo>/ .
set -euo pipefail
cd "$(dirname "$0")/.."

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
URL="https://${REPO%%/*}.github.io/${REPO##*/}/"

if [ ! -f site/index.html ]; then
  echo "site/index.html missing — run: python scripts/build_site.py" >&2
  exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp -r site/. "$tmp/"
touch "$tmp/.nojekyll"
git -C "$tmp" init -q
git -C "$tmp" checkout -q -b gh-pages
git -C "$tmp" add -A
git -C "$tmp" -c user.name="cb-lead" -c user.email="cb-lead@users.noreply.github.com" \
  commit -q -m "site: 六十秒的演算法 (FrontierOR testing stage)"
git -C "$tmp" push -q -f "https://github.com/${REPO}.git" gh-pages

gh api "repos/${REPO}/pages" >/dev/null 2>&1 || \
  gh api -X POST "repos/${REPO}/pages" -f "source[branch]=gh-pages" -f "source[path]=/" >/dev/null

echo "$URL"
