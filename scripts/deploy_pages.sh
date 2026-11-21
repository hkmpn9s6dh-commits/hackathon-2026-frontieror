#!/usr/bin/env bash
# Publish site/ to the gh-pages branch, then make sure Pages is on.
#
#   bash scripts/deploy_pages.sh
#
# gh-pages carries only the built page, because that is what a reader needs; the
# sources stay on main. Pages is a "legacy" build, same as the other repos in this
# account, so the URL is https://<owner>.github.io/<repo>/ .
#
# The staging directory is relative on purpose: absolute Windows temp paths trip
# the shell guard on `rm -rf`, and this also keeps the push inside the repo.
set -euo pipefail
cd "$(dirname "$0")/.."

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
URL="https://${REPO%%/*}.github.io/${REPO##*/}/"
PROXY=${PROXY:-http://127.0.0.1:7897}

if [ ! -f site/index.html ]; then
  echo "site/index.html missing — run: python scripts/build_site.py" >&2
  exit 1
fi

stage=_pages
rm -rf "$stage"
mkdir -p "$stage"
cp -r site/. "$stage/"
touch "$stage/.nojekyll"

git -C "$stage" init -q
git -C "$stage" checkout -q -b gh-pages
git -C "$stage" add -A
git -C "$stage" -c user.name="cb-lead" -c user.email="cb-lead@users.noreply.github.com" \
  commit -q -m "site: 六十秒的演算法 (FrontierOR testing stage)"
git -C "$stage" -c http.proxy="$PROXY" -c http.version=HTTP/1.1 \
  push -q -f "https://github.com/${REPO}.git" gh-pages
rm -rf "$stage"

gh api "repos/${REPO}/pages" >/dev/null 2>&1 || \
  gh api -X POST "repos/${REPO}/pages" -f "source[branch]=gh-pages" -f "source[path]=/" >/dev/null

echo "$URL"
