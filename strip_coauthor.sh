#!/bin/sh
# Remove AI attribution from commit messages: every "Co-Authored-By:" trailer (any case) and the
# "Generated with [Claude Code](...)" footer line.
#
#   ./strip_coauthor.sh                  # commits not yet on the upstream (@{upstream}..HEAD);
#                                        # without an upstream: the whole branch
#   ./strip_coauthor.sh --all            # every branch and tag of the repository
#   ./strip_coauthor.sh v1.0..HEAD       # any rev-list range
#
# This rewrites history. Rewritten commits that were already pushed need
# `git push --force-with-lease`; GPG signatures of rewritten commits are dropped.
set -e
cd "$(dirname "$0")"

if [ $# -eq 0 ]; then
    if git rev-parse --verify -q '@{upstream}' >/dev/null; then
        set -- '@{upstream}..HEAD'
    else
        set -- HEAD
    fi
fi

PATTERN='^[[:space:]]*co-authored-by:|generated with \[claude code\]'
count_left() {
    # --exclude keeps the refs/original backup out of an --all count
    git log --format='%H' -i -E --grep="$PATTERN" --exclude='refs/original/*' "$@" | wc -l | tr -d ' '
}

before=$(count_left "$@")
echo "Commits with attribution lines in range '$*': $before"
if [ "$before" = "0" ]; then
    exit 0
fi

export FILTER_BRANCH_SQUELCH_WARNING=1
# sed: drop the two kinds of lines (case-insensitive), then trailing blank lines
git filter-branch -f --tag-name-filter cat \
    --msg-filter 'sed -E "/^[[:space:]]*[Cc][Oo]-[Aa][Uu][Tt][Hh][Oo][Rr][Ee][Dd]-[Bb][Yy]:/d; /[Gg]enerated with \[[Cc]laude [Cc]ode\]/d" | sed -e :a -e "/^\n*$/{\$d;N;ba" -e "}"' \
    -- "$@"

after=$(count_left "$@")
echo "Commits with attribution lines after the rewrite: $after"
if [ "$after" = "0" ]; then
    # the rewrite did what it should: drop the refs/original backup so the old commits stop
    # being reachable (works in worktrees and with packed refs, unlike rm -rf .git/refs)
    git for-each-ref --format='%(refname)' refs/original/ | while read -r ref; do
        git update-ref -d "$ref"
    done
    echo "Backup refs removed. Push with: git push --force-with-lease"
else
    echo "Some commits still carry attribution; the backup is kept under refs/original/"
    git log --format='%h %s' -i -E --grep="$PATTERN" --exclude='refs/original/*' "$@" | head
    exit 1
fi
