#!/usr/bin/env bash
# Verification gate for the fork. Last line is always "VERIFY: OK" or "VERIFY: FAIL (...)".
#
#   scripts/fork/verify.sh                   full: fork rules + vue-tsc ratchet + build + backend tests
#   scripts/fork/verify.sh --quick           skip backend tests (fast loop while coding)
#   scripts/fork/verify.sh --ui LABEL        also start the app and run screenshot/mobile checks
#   scripts/fork/verify.sh --ui LABEL --publish   copy screenshots to docs/fork/screens/LABEL (for the PR)
#   scripts/fork/verify.sh --update-baseline record current vue-tsc count + failing tests as the baseline
#
# Ratchets (committed in docs/fork/baseline/): the number of vue-tsc errors may only go down,
# and no test may fail unless it already failed upstream when the baseline was recorded.
set -uo pipefail
cd "$(dirname "$0")/../.."
export DJANGO_SETTINGS_MODULE=recipes.settings
BASE_DIR=docs/fork/baseline
mkdir -p .fork "$BASE_DIR"
QUICK=0; UI_LABEL=""; PUBLISH=""; UPDATE=0
while [ $# -gt 0 ]; do
  case $1 in
    --quick) QUICK=1 ;;
    --ui) UI_LABEL=${2:?label required}; shift ;;
    --publish) PUBLISH="--publish" ;;
    --update-baseline) UPDATE=1 ;;
    *) echo "unknown option $1"; exit 2 ;;
  esac
  shift
done
FAILS=()
ok() { printf '  [ok]   %s\n' "$*"; }
ko() { printf '  [FAIL] %s\n' "$*"; FAILS+=("$1"); }
YARN="yarn"; command -v yarn >/dev/null 2>&1 || YARN="npx --yes yarn"

UPSTREAM_REF="upstream/${FORK_UPSTREAM_BRANCH:-master}"
echo "== fork rules"
if git rev-parse --verify -q "$UPSTREAM_REF" >/dev/null; then
  MB=$(git merge-base HEAD "$UPSTREAM_REF")
  MIG=$( { git diff --name-only "$MB" -- cookbook/migrations; git status --porcelain cookbook/migrations | awk '{print $2}'; } | sort -u)
  if [ -n "$MIG" ]; then ko "cookbook-migrations" ; echo "$MIG" | sed 's/^/         /'; else ok "no migration added to cookbook/ (use the fork's own Django app)"; fi
  GEN=$(git diff --name-only "$MB" -- vue3/src/openapi vue3/src/authapi | head -5)
  [ -n "$GEN" ] && echo "  [info] generated API client changed (must come from regeneration, not hand edits): $(echo $GEN | tr '\n' ' ')"
else
  echo "  [skip] $UPSTREAM_REF not fetched (git fetch upstream ${FORK_UPSTREAM_BRANCH:-master})"
fi

echo "== frontend"
TSC_OUT=.fork/vue-tsc.txt
(cd vue3 && npx vue-tsc --noEmit -p tsconfig.app.json) > "$TSC_OUT" 2>&1
TSC_COUNT=$(grep -c 'error TS' "$TSC_OUT" || true)
if [ "$UPDATE" = 1 ]; then
  echo "$TSC_COUNT" > "$BASE_DIR/vue-tsc.count"; ok "baseline vue-tsc = $TSC_COUNT"
else
  TSC_BASE=$(cat "$BASE_DIR/vue-tsc.count" 2>/dev/null || echo "")
  if [ -z "$TSC_BASE" ]; then ko "vue-tsc-baseline-missing (run --update-baseline once)"
  elif [ "$TSC_COUNT" -gt "$TSC_BASE" ]; then
    ko "vue-tsc: $TSC_COUNT errors > baseline $TSC_BASE"
    echo "         new errors are listed in $TSC_OUT; files touched on this branch:"
    { git diff --name-only "${MB:-HEAD}" -- vue3/src; git ls-files --others --exclude-standard vue3/src; } | sort -u \
      | while read -r f; do grep -F "${f#vue3/}" "$TSC_OUT" | head -3 | sed 's/^/         /'; done
  else ok "vue-tsc: $TSC_COUNT errors (baseline $TSC_BASE)"; [ "$TSC_COUNT" -lt "$TSC_BASE" ] && echo "  [info] fewer errors than baseline: you may lower it with --update-baseline"; fi
fi
if (cd vue3 && $YARN build) > .fork/build.txt 2>&1; then ok "vite build"; else ko "vite-build"; tail -15 .fork/build.txt | sed 's/^/         /'; fi

if [ "$QUICK" = 0 ]; then
  echo "== backend tests (pytest, ~2 min)"
  PT_OUT=.fork/pytest.txt
  .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts="" -n 4 cookbook/tests -rfE > "$PT_OUT" 2>&1
  SUMMARY=$(grep -E '^(=+ )?[0-9]+ (passed|failed)|passed|no tests ran' "$PT_OUT" | tail -1)
  grep -E '^(FAILED|ERROR) cookbook/' "$PT_OUT" | sed -E 's/ - .*//' | sort -u > .fork/pytest-failures.txt
  if ! grep -qE '[0-9]+ passed' "$PT_OUT"; then
    ko "pytest-did-not-run"; tail -15 "$PT_OUT" | sed 's/^/         /'
  elif [ "$UPDATE" = 1 ]; then
    cp .fork/pytest-failures.txt "$BASE_DIR/pytest-failures.txt"; ok "baseline failing tests = $(wc -l < "$BASE_DIR/pytest-failures.txt") ($SUMMARY)"
  else
    NEW=$(comm -13 "$BASE_DIR/pytest-failures.txt" .fork/pytest-failures.txt 2>/dev/null)
    if [ -n "$NEW" ]; then ko "pytest: new failures"; echo "$NEW" | sed 's/^/         /'; else ok "pytest: no new failure ($SUMMARY)"; fi
  fi
fi

if [ -n "$UI_LABEL" ]; then
  echo "== UI checks ($UI_LABEL)"
  if scripts/fork/serve.sh restart > .fork/serve.txt 2>&1; then
    if node scripts/fork/ui/screenshots.mjs --label "$UI_LABEL" $PUBLISH > .fork/ui.txt 2>&1; then
      ok "UI checks (report: .fork/screens/$UI_LABEL/report.md)"
    else ko "ui-checks"; grep -E 'FAIL|ERROR|\| yes \|' .fork/ui.txt | grep -v '| OK |' | head -15 | sed 's/^/         /'; fi
  else ko "dev-server"; tail -10 .fork/serve.txt | sed 's/^/         /'; fi
fi

echo
if [ ${#FAILS[@]} -eq 0 ]; then echo "VERIFY: OK"; exit 0; else echo "VERIFY: FAIL (${FAILS[*]})"; exit 1; fi
