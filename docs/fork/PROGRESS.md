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

1. [ ] `.gitignore` : vérifier l'intégration de `docs/fork/gitignore.append`, committer le `package-lock.json` des
   outils UI. Vérif : `git status` propre après `setup.sh`.
2. [ ] Baseline : `verify.sh --update-baseline` (vue-tsc + échecs pytest) commitée dans `docs/fork/baseline/`.
   Vérif : `verify.sh` → `VERIFY: OK`.
3. [ ] Captures de référence : `verify.sh --ui m0-baseline --publish`. Vérif : `docs/fork/screens/m0-baseline/` rempli.
4. [ ] App `kitchen/` vide, dans `INSTALLED_APPS`, avec un test pytest trivial lancé par `verify.sh`.
   Vérif : `verify.sh` → `VERIFY: OK`, test `kitchen` compté.
5. [ ] `docs/fork/AUDIT.md` (carte UI, aliments, création de recettes, friction mobile, plugins) + « Propositions M0 »
   en fin de ROADMAP.md. Vérif : relecture `reviewer`.
6. [ ] Porte finale `verify.sh --ui m1 --publish` (libellé demandé par Alex), `reviewer` + `ui-auditor`, PR.
