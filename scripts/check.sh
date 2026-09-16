#!/usr/bin/env bash
# Pre-push gate: deny-list grep, secret scan, frontmatter check. Exit non-zero on any hit.
# The deny-list is private and lives outside the repo: set DENYLIST_PATH (one regex per line).
set -u
cd "$(dirname "$0")/.."
fail=0
echo "== deny-list"
while IFS= read -r pat; do
  [ -z "$pat" ] && continue
  hits=$(grep -rIniE --exclude-dir=.git --exclude=check.sh -- "$pat" . || true)
  if [ -n "$hits" ]; then echo "HIT [$pat]"; echo "$hits" | head -5; fail=1; fi
done < "${DENYLIST_PATH:?set DENYLIST_PATH to a private deny-list file, one regex per line}"
echo "== gitleaks"
if command -v gitleaks >/dev/null; then gitleaks detect --no-banner --redact -s . || fail=1; else echo "gitleaks missing (brew install gitleaks)"; fail=1; fi
echo "== frontmatter"
for f in plugins/*/skills/*/SKILL.md; do
  [ -e "$f" ] || continue
  head -1 "$f" | grep -q '^---$' && grep -qE '^description:' "$f" || { echo "bad frontmatter: $f"; fail=1; }
done
echo "== root skills/ mirrors plugins"
for d in plugins/*/skills/*/; do [ -d "$d" ] || continue; n=$(basename "$d"); [ -L "skills/$n" ] || { echo "missing mirror: skills/$n"; fail=1; }; done
[ $fail -eq 0 ] && echo "CHECK PASSED" || echo "CHECK FAILED"
exit $fail
