#!/usr/bin/env bash
# SessionStart hook. In cloud sessions it prepares the environment; locally it only prints context.
# Stdout is added to Claude's context, so it is phrased as facts.
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0

if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  if scripts/fork/setup.sh > .fork-setup.log 2>&1; then
    echo "Fork dev environment is ready (.venv, vue3/node_modules, SQLite DB seeded with user demo/demo)."
  else
    echo "Fork setup script failed; the last lines of .fork-setup.log are:"
    tail -15 .fork-setup.log
  fi
  mkdir -p .fork && mv -f .fork-setup.log .fork/setup.log 2>/dev/null
fi

BRANCH=$(git branch --show-current 2>/dev/null)
NEXT=$(grep -m1 -E '^## M[0-9]+.*\[ \]|^- \[ \] \*\*M[0-9]+' docs/fork/ROADMAP.md 2>/dev/null)
echo "Current branch: ${BRANCH:-unknown}. First open milestone in docs/fork/ROADMAP.md: ${NEXT:-none found}."
echo "Verification gate: scripts/fork/verify.sh (last line VERIFY: OK / VERIFY: FAIL)."
exit 0
