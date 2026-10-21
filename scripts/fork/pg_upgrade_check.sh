#!/usr/bin/env bash
# Upgrade check on PostgreSQL: the fork must run on a database that the upstream image created,
# and going back to the upstream image must stay possible (docs/fork/DEPLOY.md).
#
#   1. a fresh database is migrated by the upstream image, which also writes some data;
#   2. the fork's code applies its own migrations (kitchen/) on top, nothing else is pending;
#   3. rollback: the fork removes its tables (migrate kitchen zero), then the upstream image
#      finds no pending migration and can delete a food that the fork had extended.
#
# Needs Docker and a reachable PostgreSQL server (default: 127.0.0.1:5432, postgres/postgres).
#   UPSTREAM_IMAGE  upstream image to start from (default: the release the fork is based on)
#   FORK_IMAGE      run the fork side from this image instead of the local .venv
#   PGHOST PGPORT PGUSER PGPASSWORD   PostgreSQL server; the database tandoor_upgrade_check is recreated
# Last line: "PG UPGRADE CHECK: OK" or "PG UPGRADE CHECK: FAIL (<step>)".
set -uo pipefail
cd "$(dirname "$0")/../.."
PGHOST=${PGHOST:-127.0.0.1}; PGPORT=${PGPORT:-5432}; PGUSER=${PGUSER:-postgres}; PGPASSWORD=${PGPASSWORD:-postgres}
export PGPASSWORD
DB=tandoor_upgrade_check
BASE=$(git describe --tags --abbrev=0 --match '[0-9]*.[0-9]*.[0-9]*' --exclude '*-*' HEAD)
UPSTREAM_IMAGE=${UPSTREAM_IMAGE:-ghcr.io/tandoorrecipes/recipes:$BASE}

fail() { echo "  [FAIL] $1"; echo; echo "PG UPGRADE CHECK: FAIL ($1)"; exit 1; }
ok() { echo "  [ok]   $*"; }
DB_ENV=(-e DB_ENGINE=django.db.backends.postgresql -e POSTGRES_HOST="$PGHOST" -e POSTGRES_PORT="$PGPORT"
        -e POSTGRES_USER="$PGUSER" -e POSTGRES_PASSWORD="$PGPASSWORD" -e POSTGRES_DB="$DB" -e SECRET_KEY=upgrade-check)
upstream() { # upstream <manage.py args...>
  docker run --rm --network host "${DB_ENV[@]}" --entrypoint /opt/recipes/venv/bin/python "$UPSTREAM_IMAGE" manage.py "$@"
}
fork() { # fork <manage.py args...>
  if [ -n "${FORK_IMAGE:-}" ]; then
    docker run --rm --network host "${DB_ENV[@]}" --entrypoint /opt/recipes/venv/bin/python "$FORK_IMAGE" manage.py "$@"
  else
    env DJANGO_SETTINGS_MODULE=recipes.settings DB_ENGINE=django.db.backends.postgresql POSTGRES_HOST="$PGHOST" \
      POSTGRES_PORT="$PGPORT" POSTGRES_USER="$PGUSER" POSTGRES_PASSWORD="$PGPASSWORD" POSTGRES_DB="$DB" \
      SECRET_KEY=upgrade-check .venv/bin/python manage.py "$@"
  fi
}
LOG=.fork/pg-upgrade-check.log; mkdir -p .fork; : > "$LOG"
quiet() { "$@" >> "$LOG" 2>&1; }

echo "== PostgreSQL upgrade check (upstream $UPSTREAM_IMAGE -> fork ${FORK_IMAGE:-local code})"
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -qc "DROP DATABASE IF EXISTS $DB" -c "CREATE DATABASE $DB" >> "$LOG" 2>&1 \
  || fail "postgres-unreachable"
quiet docker pull -q "$UPSTREAM_IMAGE" || fail "upstream-image-pull"

# 1. upstream creates the database and some data
quiet upstream migrate --noinput || fail "upstream-migrate"
quiet upstream shell -c "
from django_scopes import scopes_disabled
with scopes_disabled():
    from django.contrib.auth.models import User
    from cookbook.models import Space, UserSpace, Food
    u = User.objects.create_user('check', password='check')
    s = Space.objects.create(name='Check', created_by=u)
    UserSpace.objects.create(user=u, space=s, active=True)
    Food.objects.create(name='oignon', space=s)
    Food.objects.create(name='carotte', space=s)
" || fail "upstream-data"
ok "upstream image $UPSTREAM_IMAGE created the database (last cookbook migration: $(upstream showmigrations cookbook 2>/dev/null | grep '\[X\]' | tail -1 | sed 's/ *\[X\] //'))"

# 2. the fork applies its migrations on top
quiet fork migrate --noinput || fail "fork-migrate"
quiet fork migrate --check || fail "fork-pending-migrations"
quiet fork makemigrations --check --dry-run kitchen || fail "fork-missing-migration"
quiet fork shell -c "
from django_scopes import scopes_disabled
with scopes_disabled():
    from cookbook.models import Food
    from kitchen.models import KitchenFood
    for f in Food.objects.all():
        KitchenFood.objects.get_or_create(food=f, defaults={'space': f.space, 'is_family': True})
    assert KitchenFood.objects.count() == 2, KitchenFood.objects.count()
    assert Food.objects.filter(name='oignon').exists()
" || fail "fork-data"
ok "fork migrations applied: $(fork showmigrations kitchen 2>/dev/null | grep '\[X\]' | sed 's/ *\[X\] //' | tr '\n' ' ')"
ok "upstream data intact, fork rows written, no pending or missing migration"

# 3. rollback to the upstream image
quiet fork migrate kitchen zero --noinput || fail "fork-rollback"
LEFT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB" -tAc "SELECT count(*) FROM pg_tables WHERE tablename LIKE 'kitchen\_%'")
[ "$LEFT" = 0 ] || fail "fork-tables-left"
quiet upstream migrate --check || fail "upstream-pending-after-rollback"
quiet upstream shell -c "
from django_scopes import scopes_disabled
with scopes_disabled():
    from cookbook.models import Food
    Food.objects.get(name='oignon').delete()
    assert Food.objects.count() == 1
" || fail "upstream-after-rollback"
ok "rollback: kitchen tables removed, upstream image runs and deletes data on the same database"

psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -qc "DROP DATABASE IF EXISTS $DB" >> "$LOG" 2>&1
echo
echo "PG UPGRADE CHECK: OK"
