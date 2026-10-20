# Journal de progression

Tenu par Claude pendant les jalons : plan, avancement, blocages. Le plus récent en bas.
Questions bloquantes pour Alex : en tête de ce fichier, sous « En attente ».

## En attente
_(aucune)_

## 2026-10-20 — Cadrage
- Entretien de cadrage terminé : SPEC.md rempli, DESIGN.md validé, critères M3 et M4 réécrits.
- Captures `m0-preview` produites. `verify.sh --quick --ui m0-preview` donne `VERIFY: FAIL (vue-tsc-baseline-missing)` :
  c'est attendu, la baseline est enregistrée en M0.
- M2 réécrit selon les parcours P1 à P4 (validé par Alex).
- Prochain jalon : M0.

## M0 — plan
Branche : `claude/gifted-cerf-5458vi` (branche imposée par la session cloud, voir DECISIONS.md), base `origin/main`.
Environnement : `verify.sh --quick` → `VERIFY: FAIL (vue-tsc-baseline-missing)` avant tout changement, attendu (la
baseline est l'objet de M0) ; `setup.sh` OK (seed `demo/demo`, 17 aliments, 4 recettes).

1. [x] `.gitignore` : vérifier l'intégration de `docs/fork/gitignore.append`, committer le `package-lock.json` des
   outils UI. Vérif : `git status` propre après `setup.sh`.
2. [x] Baseline : `verify.sh --update-baseline` (vue-tsc + échecs pytest) commitée dans `docs/fork/baseline/`.
   Vérif : `verify.sh` → `VERIFY: OK`.
3. [x] Captures de référence : `verify.sh --ui m0-baseline --publish`. Vérif : `docs/fork/screens/m0-baseline/` rempli.
4. [x] App `kitchen/` vide, dans `INSTALLED_APPS`, avec un test pytest trivial lancé par `verify.sh`.
   Vérif : `verify.sh` → `VERIFY: OK`, test `kitchen` compté.
5. [x] `docs/fork/AUDIT.md` (carte UI, aliments, création de recettes, friction mobile, plugins) + « Propositions M0 »
   en fin de ROADMAP.md. Vérif : relecture `reviewer`.
6. [ ] Porte finale `verify.sh --ui m1 --publish` (libellé demandé par Alex), `reviewer` + `ui-auditor`, PR.

### Avancement M0
- 1 : `.gitignore` contenait déjà le bloc de `gitignore.append` (commit du kit) ; `package-lock.json` des outils UI commité.
- 2 : `verify.sh` complet ne terminait jamais. Les connecteurs externes démarraient, car le `DJANGO_SETTINGS_MODULE`
  exporté prenait le pas sur `pytest.ini`. Corrigé avec `--ds recipes.test_settings`. Baseline : 650 erreurs vue-tsc,
  1 test en échec (`test_markdown_renderer`). pytest prend environ 50 s.
- 3 : le jeu de démo crée désormais un foyer, sinon l'accueil était l'assistant « Foyers ». Captures `m0-baseline`
  republiées.
- 4 : `kitchen/` créée, dans `INSTALLED_APPS`, test `kitchen/tests/test_app.py` lancé par `verify.sh`.
- 5 : `docs/fork/AUDIT.md` rédigé, propositions ajoutées en fin de ROADMAP.md.
