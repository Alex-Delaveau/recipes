---
name: upstream-sync
description: Merge the latest Tandoor release (upstream master) into the fork on a dedicated branch and open a PR. Invoke as /upstream-sync.
disable-model-invocation: true
---

Bring the latest upstream release into the fork without losing the fork's changes.

1. `git fetch upstream master --tags && git fetch origin`. Note the latest release tag
   (`git describe --tags --abbrev=0 upstream/master`) and the commits it brings (`git log --oneline origin/main..upstream/master | head -50`).
2. `git switch -c sync/upstream-<tag> origin/main && git merge --no-ff upstream/master`.
3. Resolve conflicts with this rule: upstream wins for backend logic, models, migrations and the generated API client;
   the fork wins for visual changes (theme, layout, fork components). When both changed the same behaviour, keep upstream's
   behaviour and re-apply the fork's presentation on top. Log every non-trivial resolution in `docs/fork/DECISIONS.md`.
4. If upstream changed serializers or endpoints, regenerate the API client (see CLAUDE.md) instead of merging generated files by hand.
5. `scripts/fork/setup.sh` (new dependencies, migrations), then `scripts/fork/verify.sh --ui sync-<tag> --publish`.
   A test that fails upstream too (check on a clean checkout of `upstream/master`) may be added to the baseline; say so in the PR.
6. Push and open a PR against the fork's `main` titled `Sync upstream <tag>`, listing: upstream highlights,
   conflicts and how they were resolved, the `verify.sh` summary, and anything Alex must check on the phone.
