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
6. [x] Porte finale `verify.sh --ui m1 --publish` (libellé demandé par Alex), `reviewer` + `ui-auditor`, PR.

### Avancement M0
- 1 : `.gitignore` contenait déjà le bloc de `gitignore.append` (commit du kit) ; `package-lock.json` des outils UI commité.
- 2 : `verify.sh` complet ne terminait jamais. Les connecteurs externes démarraient, car le `DJANGO_SETTINGS_MODULE`
  exporté prenait le pas sur `pytest.ini`. Corrigé avec `--ds recipes.test_settings`. Baseline : 650 erreurs vue-tsc,
  1 test en échec (`test_markdown_renderer`). pytest prend environ 50 s.
- 3 : le jeu de démo crée désormais un foyer, sinon l'accueil était l'assistant « Foyers ». Captures `m0-baseline`
  republiées.
- 4 : `kitchen/` créée, dans `INSTALLED_APPS`, test `kitchen/tests/test_app.py` lancé par `verify.sh`.
- 5 : `docs/fork/AUDIT.md` rédigé, propositions ajoutées en fin de ROADMAP.md.

## M0 — summary
- Socle prêt : baseline (650 erreurs vue-tsc, 1 test upstream en échec), captures `m0-baseline`, app `kitchen/` vide
  et testée, `verify.sh` complet fonctionnel (environ 2 min 30 avec l'UI).
- `docs/fork/AUDIT.md` décrit la carte de l'UI, l'existant aliments et recettes, la friction mobile et les plugins.
  Les propositions pour M1 à M4 sont en fin de ROADMAP.md, à valider par Alex.
- Relectures : `reviewer` n'a trouvé aucun point bloquant (références corrigées) ; `ui-auditor` donne SHIP (aucun
  changement visible, compléments ajoutés à l'audit § 4).
- Porte finale : `verify.sh --ui m1 --publish` → `VERIFY: OK`.
- Prochain jalon : M1, après validation des propositions M0.

## M1 — plan
Branche : `claude/busy-heisenberg-yf2zw3` (branche imposée par la session cloud, comme en M0), base `origin/main`
(M0 fusionné). Environnement : `verify.sh --quick` → `VERIFY: OK` avant tout changement (650 erreurs vue-tsc).

1. [x] Captures fiables (`screenshots.mjs`) : capture « écran visible » en plus de la pleine page ; `Math.random`
   à graine fixe et attente de la fin des chargements ; capture sombre (mobile, `prefers-color-scheme: dark`) ;
   publication des captures `small`. Vérif : deux passes `--ui wip` donnent les mêmes images d'accueil.
2. [x] Thème Vuetify clair/sombre depuis les tokens de DESIGN.md (couleurs, police système, rayons, élévation 0/1 avec
   contours, espacements) ; thème par défaut = système. Vérif : `verify.sh --quick --ui wip`, captures clair et sombre.
3. [x] Fondu entre les vues (≤ 200 ms), coupé avec `prefers-reduced-motion`. Vérif : build + lecture du CSS appliqué.
4. [x] Coquille : barre du bas à 4 entrées avec libellés (Recettes, Courses, Ajouter, Plus), feuilles « Ajouter » et
   « Plus », hauteur réservée dans `v-main`, en-tête compact, tiroir dès `mdAndUp`. Vérif : captures « écran visible »
   mobile et desktop, zones tactiles ≥ 44 px dans la barre.
5. [x] Erreurs upstream : `POST /api/view-log/` en 403 et `TypeError` dans `AccountSettings`, corrigées au plus près.
   Vérif : rapport UI sans erreur JS sur `recipe-view`, `mealplan`, `settings`.
6. [x] Page de connexion alignée sur les tokens (CSS du fork, sans toucher au template upstream si possible).
   Vérif : captures `login`.
7. [x] Toutes les routes de `routes.json` en `"strict": true`, aucun débordement à 360 px. Vérif : `verify.sh --ui wip`.
8. [x] Porte finale `verify.sh --ui m1 --publish`, `reviewer` + `ui-auditor`, corrections, PR.

### Avancement M1
- 1 : captures « écran visible » (`*-screen.jpg`), viewport `dark` (390 px, `prefers-color-scheme: dark`), graine fixe,
  paramètre `random` retiré des appels API, attente des chargements, cookie CSRF obtenu comme lors d'une vraie
  connexion, requêtes en échec listées dans le rapport, tout publié (360 px compris).
- 2 : thème depuis les tokens (`vue3/src/fork/theme.ts`, `fork.css`). Le thème suit le système par défaut ; le choix
  Système, Clair ou Sombre est dans les réglages « Cosmétique ».
- 3 : fondu `fork-fade`, 100 ms à la sortie et 100 ms à l'entrée (`mode="out-in"`), coupé par `prefers-reduced-motion`.
- 4 : `ForkBottomNav.vue` (4 entrées avec libellés, feuilles « Ajouter » et « Plus », 64 px), en-tête `compact`,
  tiroir `mdAndUp`.
- 5 : le 403 sur `view-log` venait du cookie CSRF absent dans les captures (voir DECISIONS.md) ; le `TypeError` dans
  `AccountSettings` est corrigé en attendant l'id utilisateur.
- 6 : connexion stylée (`kitchen/static/kitchen/login.css`).
- 7 : les 9 routes passent en `strict` sans débordement ni erreur. Baseline vue-tsc abaissée de 650 à 649.
- 8 : porte `verify.sh --ui m1 --publish` → `VERIFY: OK`. Les deux relectures ont été traitées :
  - `reviewer` : 1 point bloquant, corrigé. Le fondu `out-in` laissait une page vide en quittant une page à plusieurs
    racines (import de recette). La vue est désormais enveloppée dans un `div` à clé, et `screenshots.mjs` vérifie la
    navigation interne (`in-app-navigation`).
  - `ui-auditor` : « FIX FIRST » avec 3 points bloquants, corrigés :
    - contraste du texte secondaire et des placeholders ;
    - lien du logo à 44 px ;
    - bouton flottant d'enregistrement remonté au-dessus de la barre.

    Corrections peu coûteuses ajoutées : cellule « 1er du mois » et lignes du calendrier en sombre, « Profil » en
    français. Le reste est listé dans la PR.

## M1 — summary
- Thème clair et sombre issu des tokens ; thème du système par défaut, réglable (Système, Clair, Sombre).
- Police système, rayons et contours ; couleurs upstream codées en dur ramenées aux tokens.
- Coquille mobile : barre du bas à 4 entrées avec libellés (Recettes, Courses, Ajouter, Plus), feuilles « Ajouter » et
  « Plus », en-tête compact. Tiroir dès 960 px. Fondu de 200 ms entre les vues, coupé avec `prefers-reduced-motion`.
- Connexion alignée sur les tokens, avec un champ d'étoiles en sombre.
- Erreurs upstream (`view-log` en 403, `AccountSettings`) corrigées ; les 9 routes passent en `strict`.
- Captures : « écran visible », sombre, 360 px publiées, reproductibles, contrôle de navigation interne.
- Prochain jalon : M2.
