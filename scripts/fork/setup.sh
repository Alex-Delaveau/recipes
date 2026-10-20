#!/usr/bin/env bash
# Idempotent dev setup for the fork (cloud session or local Linux/WSL/macOS).
# Python deps with uv, frontend deps with yarn, SQLite dev DB, demo data.
# Usage: scripts/fork/setup.sh [--no-seed]
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$PWD"
STAMPS="$ROOT/.fork/stamps"
mkdir -p "$STAMPS"
export DJANGO_SETTINGS_MODULE=recipes.settings DEBUG=1

log() { printf '[setup] %s\n' "$*"; }
changed() { # changed <stamp-name> <file>... : true if files changed since last run
  local name=$1; shift
  local sum; sum=$(cat "$@" | sha256sum | cut -d' ' -f1)
  [ "$(cat "$STAMPS/$name" 2>/dev/null)" != "$sum" ] && echo "$sum" > "$STAMPS/$name.new" && return 0
  return 1
}
commit_stamp() { mv "$STAMPS/$1.new" "$STAMPS/$1"; }

# 1. System libraries needed to build python-ldap / xmlsec wheels (Debian/Ubuntu)
if command -v dpkg >/dev/null 2>&1 && ! dpkg -s libldap2-dev libsasl2-dev libxmlsec1-dev pkg-config >/dev/null 2>&1; then
  if [ "$(id -u)" = 0 ]; then
    log "installing system libraries"
    apt-get update -qq && apt-get install -y -qq libldap2-dev libsasl2-dev libxmlsec1-dev pkg-config gettext >/dev/null
  else
    log "WARN missing system libs: sudo apt install libldap2-dev libsasl2-dev libxmlsec1-dev pkg-config gettext"
  fi
fi

# 2. Python (uv)
command -v uv >/dev/null 2>&1 || { log "ERROR uv not found (https://docs.astral.sh/uv/)"; exit 1; }
[ -x .venv/bin/python ] || { log "creating .venv (Python 3.12)"; uv venv -q --python 3.12 .venv; }
if changed python requirements.txt; then
  log "installing Python requirements"
  uv pip install -q --python .venv/bin/python -r requirements.txt
  commit_stamp python
fi

# 3. Frontend (vue3) and UI-check tooling
YARN="yarn"; command -v yarn >/dev/null 2>&1 || YARN="npx --yes yarn"
if [ ! -d vue3/node_modules ] || changed yarn vue3/yarn.lock; then
  log "installing vue3 dependencies"
  (cd vue3 && $YARN install --frozen-lockfile --silent --ignore-engines)
  [ -f "$STAMPS/yarn.new" ] && commit_stamp yarn || true
fi
if [ ! -d scripts/fork/ui/node_modules ] || changed ui scripts/fork/ui/package.json; then
  log "installing UI-check tooling"
  (cd scripts/fork/ui && npm install --silent --no-audit --no-fund)
  [ -f "$STAMPS/ui.new" ] && commit_stamp ui || true
fi
if [ ! -f cookbook/static/vue3/manifest.json ]; then
  log "building frontend"
  (cd vue3 && $YARN build >/dev/null 2>&1)
fi

# 4. Database + demo data (SQLite db.sqlite3, gitignored)
log "migrating"
.venv/bin/python manage.py migrate --noinput -v0 2>&1 | grep -v -E 'SyntaxWarning|expressions =|django-vite' || true
if [ "${1:-}" != "--no-seed" ]; then
  .venv/bin/python scripts/fork/dev_seed.py 2>&1 | grep -E '^seed' || true
fi

# 5. Git remotes: upstream for syncs and the migration guard
if git rev-parse --git-dir >/dev/null 2>&1; then
  git remote get-url upstream >/dev/null 2>&1 || git remote add upstream https://github.com/TandoorRecipes/recipes.git
  # upstream "master" = stable releases (the fork follows releases, not "develop")
  git fetch -q upstream "${FORK_UPSTREAM_BRANCH:-master}" 2>/dev/null || log "WARN could not fetch upstream (offline?)"
fi

log "done. Start the app: scripts/fork/serve.sh start   (user demo / demo)"
