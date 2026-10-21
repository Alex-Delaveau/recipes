# Journal de progression

Tenu par Claude pendant les jalons : plan, avancement, blocages. Le plus récent en bas.
Questions bloquantes pour Alex : en tête de ce fichier, sous « En attente ».

## En attente
Questions ouvertes (non bloquantes, le travail a continué avec le choix indiqué) :
- M2 — Feuille « Ajouter aux courses » : les aliments « jamais en courses » (sel, eau) sont proposés **décochés**.
  Le critère dit « tous cochés ». Garder ce choix ? (DECISIONS.md)
- M3 — Rayons renommés : la suggestion par dictionnaire retrouve un rayon générique par son nom (« Frais »,
  « Crèmerie »…). Si un rayon est renommé librement (« Produits laitiers maison »), il ne reçoit plus de suggestions du
  dictionnaire. Faut-il une correspondance explicite rayon ↔ clé générique (réglable) ?
- M4 — Reconnaissance française selon la langue active : elle suit l'en-tête `Accept-Language` du navigateur (ou le
  choix de langue). Un téléphone réglé en anglais n'en profiterait pas. Faut-il plutôt l'activer pour tout l'espace ?
- M2 — Éditeur de recette upstream sur mobile : le bouton flottant « Enregistrer » peut recouvrir le bouton
  « Supprimer » de l'image selon le défilement. Non corrigé en M2 : l'éditeur mobile est refait en M4.
- Audit kitshn — Nouveau jalon M5 « Cuisine et courses au quotidien » (minuteurs, fin de cuisine, courses hors ligne,
  « Au menu », partage), inséré avant la livraison, devenue M6. À valider avant de lancer M5 (AUDIT-KITSHN.md,
  DECISIONS.md, SPEC.md § « Cuisine et courses au quotidien »).

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

## M2 — plan
Branche : `fork/m2-cuisine`, base `origin/main` (M1 fusionné). L'objectif de session demande une branche par jalon :
`fork/m<N>-<slug>` est utilisé (le push de cette branche est accepté). Environnement : `verify.sh --quick` →
`VERIFY: OK` avant tout changement (649 erreurs vue-tsc).

1. [x] Jeu de démo enrichi : photos générées (Pillow, sans service externe), gabarits de quantités dans les étapes
   (`{{ ingredients[0] }}`), historique de consultation et de cuisine, quelques articles de courses ; route
   `cook-mode` ajoutée à `routes.json`. Vérif : `dev_seed.py` deux fois sans doublon, captures.
2. [x] Endpoint `kitchen/` `GET /api/kitchen/recipes/` : recherche upstream (`RecipeSearch`) + classement par nombre
   d'ingrédients sous la main (sans stock, descendants compris), temps total maximal, modes `recent`, `forgotten`,
   `random`. Vérif : tests pytest dans `kitchen/tests`.
3. [x] P1 Accueil Recettes (`vue3/src/fork/pages/ForkRecipesHome.vue`) : recherche visible, raccourcis, feuille de
   filtres (ingrédients, temps, mots-clés), grandes cartes photo, états vide/chargement/erreur, filtres dans l'URL.
   Vérif : captures `start` mobile, 360 px, sombre, desktop.
4. [x] P2 Vue recette (`ForkRecipeView.vue`) : photo, temps total, portions ajustables (± 44 px), liste d'ingrédients
   (groupée par étape si la recette est découpée), étapes avec quantités recalculées. Vérif : captures `recipe-view`.
5. [x] P2 Mode cuisine (`/recipe/:id/cook`) : une étape par écran, plein écran, 24/20 px, balayage + deux boutons,
   ingrédients de l'étape, Wake Lock. Vérif : captures `cook-mode`.
6. [x] P3 Feuille « Ajouter aux courses » : ingrédients aux portions choisies, tous cochés, décochage, validation vers
   la liste du foyer. Vérif : test manuel headless (script Playwright ponctuel) + capture.
7. [x] P4 Courses (`ForkShoppingList.vue`) : groupé par rayon, un tap coche, « Dans le panier », annuler, ajout
   rapide en texte libre, message de fin, synchro automatique et au retour sur l'écran. Vérif : captures `shopping`.
8. [x] Routes refaites en `strict`, porte `verify.sh --ui m2 --publish`, `reviewer` + `ui-auditor`, PR.

### Avancement M2
- 1 : photos générées (Pillow), gabarits `{{ scale(…) }}` dans deux étapes, historique de consultation et de cuisine,
  6 articles de courses, unité « pièce » au pluriel ; route `cook-mode` ajoutée (strict).
- 2 : `GET /api/kitchen/recipes/` (10 tests pytest : espace, anonyme, classement par ingrédients, familles, temps,
  texte, récentes, oubliées, hasard).
- 3 : accueil `ForkRecipesHome` (recherche, raccourcis, feuille de filtres, cartes 16:9, états vide/erreur/chargement).
- 4 : `ForkRecipeView` (photo, temps total et détail, portions ± 44 px, ingrédients, étapes recalculées).
- 5 : mode cuisine `/recipe/:id/cook` (plein écran, 24/20 px, balayage, boutons de 56 px, Wake Lock).
- 6 : feuille « Ajouter aux courses » (cases cochées, portions ajustables, liste du foyer).
- 7 : `ForkShoppingList` (rayons, un tap, « Dans le panier », annuler, ajout rapide, message de fin, synchro au retour).
  Deux défauts trouvés par les tests de parcours et corrigés : Entrée ne validait pas l'ajout rapide ; la file de
  synchro upstream pouvait laisser un article coché après une annulation rapide (voir DECISIONS.md).
- Outillage : `scripts/fork/ui/flows.mjs` (35 vérifications cliquées des parcours P1 à P4) lancé par `verify.sh --ui`.
- 8 : porte `verify.sh --ui m2 --publish` → `VERIFY: OK`. `reviewer` : 1 point bloquant (portée OAuth de l'endpoint),
  corrigé, plus 8 remarques mineures traitées (test des recettes privées, file de synchro, ajout rapide, sortie du mode
  cuisine, étapes à sous-recette, zones tactiles, retour depuis la vue détaillée). `ui-auditor` : « FIX FIRST »,
  corrigés : colonne des quantités alignée, portions lisibles en mode cuisine, raccourcis visibles à 360 px, contours
  des cartes, largeur des boutons du mode cuisine, onglet Recettes actif dans une recette. Reste listé dans la PR.

## M2 — summary
- Accueil Recettes : recherche visible, raccourcis (récentes, pas faites depuis longtemps, au hasard), feuille de
  filtres (ingrédients sous la main classés, temps total, mots-clés), grandes cartes photo. Endpoint
  `/api/kitchen/recipes/` testé.
- Vue recette : photo, temps, portions ± qui recalculent la liste et les étapes ; mode cuisine plein écran, une étape
  par écran, balayage et deux grands boutons, Wake Lock.
- Feuille « Ajouter aux courses » et liste de courses refaite (rayons, un tap, panier, annulation, ajout rapide,
  message de fin, synchro au retour sur l'écran). Correctif de la file de synchro upstream.
- `verify.sh --ui` lance désormais 35 vérifications cliquées des parcours P1 à P4.
- Prochain jalon : M3 (branche `fork/m3-aliments`, partie de `fork/m2-cuisine`).

## M3 — plan
Branche : `fork/m3-aliments`, partie de `fork/m2-cuisine` (PR M2 ouverte, non fusionnée). Environnement : porte M2
`VERIFY: OK` juste avant (649 erreurs vue-tsc).

1. [x] `kitchen/` : modèles `KitchenSpace` (ordre générique = un `Supermarket` upstream), `KitchenFood` (famille, rayon
   suggéré/confirmé), `NotDuplicate` ; règle de similarité française (`names.py`) et dictionnaire de rayons
   (`aisles.py`) ; suggestion de rayon à chaque création d'aliment (signal). Vérif : pytest (jeu d'exemples français).
2. [x] Endpoints `kitchen/` : arbre des aliments, déplacement vers une famille, rayon (confirmer/corriger), file
   « à ranger », ordre des rayons (lecture, réglage), doublons probables (+ « pas un doublon »), aliment le plus proche.
   Vérif : pytest par endpoint.
3. [x] Écran Aliments (`/foods`) : arbre famille > aliment, recherche, filtre « sans rayon », déplacer en 2 taps, édition
   rapide en feuille du bas, aucun tableau. Vérif : captures + flow.
4. [x] File « à ranger » (`/foods/to-sort`) : un aliment à la fois, un tap par rayon. Vérif : flow.
5. [x] Ordre des rayons (`/foods/aisles`) réglable ; la liste de courses suit l'ordre générique par défaut. Vérif : flow.
6. [x] Doublons probables (`/foods/duplicates`) : aperçu (recettes, articles), fusion upstream + alias `FOOD_ALIAS`.
   Vérif : flow (fusion puis contrôle de l'alias).
7. [x] Relecture d'import URL : proposition de l'aliment existant le plus proche, alias à la sélection. Vérif : flow sur
   une réponse d'import simulée.
8. [x] Navigation (Plus, tiroir), routes `strict`, porte `verify.sh --ui m3 --publish`, relectures, PR.

### Avancement M3
- 1 : modèles `kitchen/` (migration `0001` dans `kitchen/migrations`), similarité (`names.py`), dictionnaire de rayons
  (`aisles.py`, environ 300 aliments), signal de suggestion à la création d'un aliment.
- 2 : endpoints `/api/kitchen/foods/…`, `/aisles/`, `/duplicates/…`. 38 tests pytest de plus : 19 exemples français de
  similarité, détection des doublons, ordre générique, suggestions, file, familles, rapprochement d'import, fusion upstream.
- 3 à 6 : écrans `/foods`, `/foods/to-sort`, `/foods/aisles`, `/foods/duplicates` et feuille d'édition rapide. La liste de
  courses suit l'ordre générique. Navigation : « Aliment » mène à l'arbre ; « Doublons probables » ajouté.
- 7 : encart « Aliments inconnus » dans la relecture d'import.
- Défauts trouvés en route et corrigés :
  - la fusion upstream échouait (400) à cause de la relation `KitchenFood` (relation inverse désormais masquée) ;
  - le dictionnaire ne trouvait pas un aliment au milieu d'un nom plus long ;
  - cinq traductions manquaient pour l'encart d'import.
- Parcours cliqués M3 ajoutés à `flows.mjs` : arbre, déplacement en 2 taps, édition rapide, file, ordre, doublons
  avec alias, relecture d'import (64 vérifications au total avec M2).
- 8 : porte `verify.sh --ui m3 --publish` → `VERIFY: OK` (64 vérifications de parcours). Relectures :
  - `reviewer` : les points bloquants (comptes par rayon faux, porte non relancée) sont corrigés, comme les remarques
    mineures peu coûteuses : descendants qui suivent la famille, interrupteur « famille », 400 sur un id invalide,
    fusion puis alias, ordre restauré si l'enregistrement échoue, file sans les « jamais en courses », appels
    séquentiels, tests multi-espaces ;
  - `ui-auditor` : « FIX FIRST », corrigés : comptes par rayon, doublons regroupés autour d'un seul aliment à garder,
    actions de la file en bas d'écran, sous-titres sans répétition du rayon de la famille, icônes, libellés.

## M3 — summary
- Écran Aliments en arbre famille > aliment (recherche instantanée, filtre « sans rayon », déplacement en 2 taps, édition
  rapide en feuille du bas), file « à ranger » un tap par rayon, ordre générique des rayons réglable, suivi par la liste
  de courses.
- Rayon suggéré à chaque création d'aliment (famille, dictionnaire français, nom proche), appliqué tout de suite, puis
  confirmé.
- Doublons probables (règle de similarité française testée), fusion upstream avec aperçu et alias `FOOD_ALIAS`.
  Proposition de l'aliment existant le plus proche pendant la relecture d'import.
- Tout le nouveau stockage est dans `kitchen/` (une migration). 52 tests `kitchen` au total.
- Prochain jalon : M4 (branche `fork/m4-recettes`, partie de `fork/m3-aliments`).

## M4 — plan
Branche : `fork/m4-recettes`, partie de `fork/m3-aliments` (PR M3 ouverte, non fusionnée). Environnement : porte M3
`VERIFY: OK` juste avant (649 erreurs vue-tsc).

1. [x] Reconnaissance française dans `kitchen/french.py`, branchée sur `IngredientParser.parse` au démarrage de l'app
   (le fichier du parseur n'est pas modifié), active quand la langue est le français. Elle couvre les unités,
   « de/d' », les précisions en note, les pluriels vers l'aliment existant et les fractions. Vérif : 40 lignes réelles
   en pytest, plus l'API du parseur, l'import URL et le texte libre des courses.
2. [x] Endpoint `kitchen/` d'analyse **sans création** (reconnaissance en direct dans l'assistant) : `POST
   /api/kitchen/parse/`. Vérif : pytest (aucun aliment créé).
3. [x] Assistant de saisie en 4 écrans (`/recipe/new`) : nom et portions, ingrédients (collage multi-ligne ou ligne à
   ligne, reconnaissance en direct, correction en feuille du bas), étapes (réordonnables), détails (temps, mots-clés,
   photo de la galerie). Brouillon conservé (appareil), navigation sans perte. Enregistrement en liste unique (tous les
   ingrédients dans la première étape). Vérif : flow de bout en bout + contrôle API.
4. [x] Modification d'une recette existante avec les mêmes écrans (`/recipe/:id/edit`). Les recettes découpées par étape
   gardent leur découpage. Vérif : flow (modification puis contrôle du découpage).
5. [x] Bouton « Ajouter » : « Saisir une recette » ouvre l'assistant ; « Modifier » de la vue recette aussi (éditeur
   complet upstream accessible). Import URL : vérifier la reconnaissance française et la proposition d'aliment proche.
   Vérif : flow d'import.
6. [x] Routes `strict`, porte `verify.sh --ui m4 --publish`, relectures, PR.

### Avancement M4
- 1 : `kitchen/french.py` (40 lignes réelles testées, plus l'API du parseur, l'import URL, le texte libre des courses
  et les automatisations). Les tests upstream du parseur restent verts.
- 2 : `POST /api/kitchen/parse/` (test : aucun aliment créé).
- 3 à 5 : assistant `ForkRecipeWizard` (création et modification), feuille de correction d'une ligne, mots-clés
  créables, photo de la galerie, brouillon. « Saisir une recette » et « Modifier » y mènent.
- Parcours cliqués M4 : assistant de bout en bout (25 vérifications), relecture d'import en français. 91 vérifications
  au total. Les écrans 2 à 4 de l'assistant sont capturés par les flows et publiés avec les captures.
- Défaut trouvé sur capture et corrigé : libellé et exemple superposés sur l'écran Ingrédients.
- 6 : porte `verify.sh --ui m4 --publish` → `VERIFY: OK` (91 vérifications de parcours). Relectures :
  - `reviewer` : 6 points bloquants, tous corrigés :
    - « 1 ½ » mal lu ;
    - note de plus de 256 caractères ;
    - noms composés coupés (« pâte à tarte », « lait en poudre ») ;
    - brouillon périmé qui pouvait écraser une recette modifiée ailleurs ;
    - recette en double si l'envoi de la photo échouait ;
    - intertitres d'ingrédients déplacés.

    Remarques mineures traitées : lignes sans aliment conservées, `TRANSPOSE_WORDS` appliqué, pas d'unité sans quantité,
    formulaire masqué si le chargement échoue, fractions dans la feuille de correction, 400 sur un corps invalide,
    lignes jamais perdues à l'enregistrement.
  - `ui-auditor` : « FIX FIRST » (contraste du bouton « Ajouter N ingrédients »), corrigé, avec l'aide sous le nom, l'état
    vide, l'espacement des boutons d'étape et la largeur égale des boutons du bas.

## M4 — summary
- Reconnaissance française des ingrédients (`kitchen/french.py`), branchée sur le parseur upstream sans le modifier :
  unités, articles, précisions en note, pluriels vers l'aliment existant, fractions. 50 lignes testées. Elle sert l'import
  URL, le collage de l'éditeur, les courses et l'assistant.
- Assistant de saisie en 4 écrans (création et modification), reconnaissance en direct sans création d'aliment,
  correction d'une ligne en feuille du bas, étapes réordonnables, mots-clés, photo de la galerie, brouillon sur
  l'appareil. Liste unique d'ingrédients pour les recettes créées ; les recettes découpées gardent leur découpage.
- « Ajouter › Saisir une recette » et « Modifier » ouvrent l'assistant ; l'éditeur complet reste accessible.
- Prochain jalon : M5 (livraison sur le homelab), après fusion de M2 → M3 → M4.
  (Mis à jour le 2026-10-21 : la livraison devient M6, voir « Audit kitshn » ci-dessous.)

## 2026-10-21 — Audit kitshn
- kitshn (client natif Kotlin de Tandoor) audité : README, documentation des fonctions, code `shared/`. Rien de copié
  (GPL-3.0, autre stack) : seulement des idées. Résultat dans `docs/fork/AUDIT-KITSHN.md`.
- Constat principal : le mode cuisine du fork ne crée jamais de `CookLog`, donc « récentes » et « pas faites depuis
  longtemps » ne sont pas nourris ; et la file de coches des courses est en mémoire (perdue si l'app est fermée hors
  ligne). Le partage vers l'app échoue quand l'URL est noyée dans du texte.
- Nouveau jalon M5 « Cuisine et courses au quotidien » ajouté à ROADMAP.md ; la livraison devient M6.
- Prochain jalon : M5 (branche `fork/m5-quotidien`), puis M6 (livraison).

## M5 — plan
Branche : `claude/clever-fermat-h1cce1` (imposée par la session cloud, au lieu de `fork/m5-quotidien`), partie de
`origin/main` (M4 fusionné). Environnement : `verify.sh --quick` → `VERIFY: OK` avant tout changement (649 erreurs vue-tsc).

1. [x] Détection des durées en français : fonction pure `vue3/src/fork/timers/detect.ts`, testée par `node --test`
   (`scripts/fork/tests/`), lancé par `verify.sh` (même en `--quick`). Vérif : ≥ 20 phrases réelles, dont faux positifs.
2. [x] Minuteurs : store Pinia du fork (heure de fin, pause, +1 min, arrêt, persistance sur l'appareil), barre compacte
   globale montée dans la coquille, alarme (son, vibration, notification si autorisée). Vérif : `--quick --ui wip`, flow.
3. [x] Durées touchables dans le mode cuisine et la vue recette (balisage du HTML rendu, sans toucher `Instructions`),
   puce `step.time` qui lance un minuteur, feuille de choix pour une plage. Vérif : flow « minuteurs ».
4. [x] Écran « Bon appétit » après « Terminé » : étoiles et commentaire facultatifs, « Enregistrer » / « Passer », les deux
   créent un `CookLog` avec les portions, puis retour à la recette. Vérif : flow (CookLog créé puis supprimé).
5. [x] Courses en magasin : écran allumé (réglable, actif par défaut), file de coches persistée et rejouée au retour du
   réseau, indicateur « N modifications en attente », dernier état connu affiché hors ligne. Diff minimal dans
   `ShoppingStore` (logique dans `vue3/src/fork/`). Vérif : flow hors ligne (Playwright `setOffline`).
6. [x] Carte « Au menu » sur l'accueil téléphone (aujourd'hui, ou demain après 21 h), seulement s'il y a un repas prévu.
   Vérif : flow (repas créé puis supprimé).
7. [x] Partage vers l'app : première URL de `url`, `text` ou `title` (`vue3/src/fork/share.ts`, testé par node), branchée
   dans `RecipeImportPage.vue`. Vérif : test node + flow `/recipe/import?text=…`.
8. [x] Chaînes fr/en, routes `strict`, porte `verify.sh --ui m5 --publish`, `reviewer`, `ui-auditor`, PR.

### Avancement M5
- 1 : détection des durées françaises, 34 phrases réelles testées par `node --test` (étape ajoutée à `verify.sh`), plus le
  balisage HTML et l'extraction d'URL partagée (52 tests node au total).
- 2-3 : minuteurs (heure de fin, pause, +1 min, arrêt, persistance, son, vibration, notification), barre globale et
  barre du mode cuisine, durées touchables et puce `step.time` dans la recette et le mode cuisine, choix d'une plage.
- 4 : écran « Bon appétit » ; « Enregistrer » et « Passer » créent un `CookLog` avec les portions.
- 5 : courses hors ligne (file et dernier état sur l'appareil, rejoués au retour du réseau), indicateur, écran allumé.
- 6 : carte « Au menu » sur l'accueil téléphone. 7 : partage vers l'app sur la première URL trouvée.
- Parcours cliqués ajoutés : `timers`, `cookdone`, `share`, `menu`, `offline`. Les routes touchées étaient déjà `strict`.
- 8 : relectures :
  - `reviewer` : 1 point bloquant, corrigé : balisage des durées qui pouvait laisser sortir du balisage d'un attribut
    (`>` ou entités dans un attribut) ; le texte n'est plus décodé ni ré-encodé, test de non-régression ajouté.
    Majeurs corrigés : son après rechargement (débloqué au premier tap), nombres composés (« vingt-cinq »).
    Mineurs corrigés : heures du jour (« à 20 h »), fausses plages (« 2 et 10 min », « étape 1 - 10 min »), alarme
    tardive, repas sur plusieurs jours, instantané seulement sur erreur réseau, écriture échouée. Reste (dans la PR) :
    file et instantané des courses non cloisonnés par compte sur un appareil partagé.
  - `ui-auditor` : « FIX FIRST », corrigés : libellés des minuteurs (étape · durée), barre repliée dès 3 minuteurs,
    style des durées (soulignement plein et icône, sans fausse alerte orthographique), bannière hors ligne aux tokens,
    écran de fin (sous-titre « Terminé », champ), feuille de plage (milieu mis en avant, « Annuler »), captures sombres.

## M5 — summary
- Minuteurs dans les étapes : durées françaises repérées et touchables (plages comprises), puce du temps de l'étape,
  plusieurs minuteurs dans une barre qui suit d'une page à l'autre, fondés sur l'heure de fin, avec son, vibration et
  notification si autorisée.
- Fin de cuisine : écran « Bon appétit » (note et commentaire facultatifs), `CookLog` enregistré dans tous les cas.
- Courses en magasin : écran allumé (réglable), coches conservées hors ligne et envoyées au retour du réseau,
  indicateur « N modifications en attente », dernier état connu affiché hors ligne.
- Carte « Au menu » sur l'accueil téléphone ; partage d'un lien vers l'app corrigé.
- Aucun changement backend. Upstream touché : `ShoppingStore.ts` (points d'accroche « fork »), `RecipeImportPage.vue`
  (partage), `Tandoor.vue` (barre des minuteurs).
- Prochain jalon : M6 (livraison sur le homelab).

## M6 — plan
Branche : `claude/zen-ramanujan-cnfub4` (imposée par la session cloud, au lieu de `fork/m6-livraison`), partie de
`origin/main` (M5 fusionné). Environnement : `verify.sh --quick` → `VERIFY: OK` avant tout changement (649 erreurs
vue-tsc). Docker est disponible dans la session (démon lancé à la main), ainsi que PostgreSQL 16.

1. [x] Étiquette d'image calculée par un script (`scripts/fork/image_tag.sh`) : version upstream (dernier tag de release
   ancêtre) + suffixe fork. Vérif : sortie du script sur la branche.
2. [x] Workflow `fork-image.yml` : build du front, image Docker (Dockerfile upstream inchangé), publication GHCR sur
   `main` et à la demande ; build sans publication sur les PR. Vérif : build local de la même image avec Docker,
   démarrage du conteneur, page de connexion servie.
3. [x] Workflow `fork-verify.yml` : `setup.sh` puis `verify.sh` complet sur chaque PR vers `main`, échec si la dernière
   ligne n'est pas `VERIFY: OK`. Vérif : exécution réelle sur la PR du jalon.
4. [x] Contrôle Postgres (`scripts/fork/pg_upgrade_check.sh`) : base créée et migrée par l'image upstream, puis
   migrations du fork appliquées dessus, puis `migrate --check` et retour arrière de `kitchen` (`migrate kitchen zero`).
   Vérif : exécution dans la session ; job dans `fork-verify.yml`.
5. [x] `docs/fork/DEPLOY.md` : stack compose pour Komodo, sauvegarde avant bascule, essai sur une copie, retour arrière
   vers l'image upstream. Vérif : compose validé par `docker compose config`, commandes jouées dans le contrôle Postgres.
6. [ ] Porte `verify.sh --ui m6 --publish`, `reviewer`, `ui-auditor`, critères, PR.

### Avancement M6
- 1 : `scripts/fork/image_tag.sh` → `2.6.15-fork.<n>` sur cette branche.
- 2 : `fork-image.yml`. Image construite dans la session avec le Dockerfile upstream (base Python via le miroir
  `mirror.gcr.io` et le certificat du proxy de la session, à cause des limites de Docker Hub : rien de cela n'est
  commité). Conteneur démarré sur PostgreSQL : migrations `kitchen` appliquées par `boot.sh`, `/accounts/login/` en 200,
  endpoints `/api/kitchen/*` présents dans `/openapi/`. (Le nginx de l'image ne démarre pas dans la session faute
  d'IPv6 : contourné à la main pour le test, limite de la session, pas de l'image.)
- 3 : `fork-verify.yml` (`setup.sh --no-seed`, `verify.sh`, contrôle Postgres). Premier passage réel sur la PR du jalon.
- 4 : `pg_upgrade_check.sh` → `PG UPGRADE CHECK: OK`, avec le code local et avec l'image du fork. Constat : sans
  `migrate kitchen zero`, l'image upstream ne peut plus supprimer un aliment étendu par le fork (DECISIONS.md).
- 5 : `DEPLOY.md` et `docs/fork/deploy/`. Procédure jouée de bout en bout sur deux stacks compose (production simulée
  avec l'image upstream 2.6.15, puis sauvegarde, essai sur une copie, bascule vers le fork, retour arrière).
- 6 : `verify.sh --ui m6 --publish` → `VERIFY: OK` (pytest 1368 passés, 1 échec de la baseline ; 137 contrôles de
  parcours).
- Relectures :
  - `reviewer` : pas de point bloquant. Majeurs corrigés :
    - `.dockerignore` : la ligne upstream `venv` avait été collée au commentaire du fork ;
    - tags de release récupérés d'upstream dans `fork-image.yml` (sinon étiquette fausse après une synchro) ;
    - retour arrière par la sauvegarde : l'image upstream est remise dans `.env` avant de relancer, et vérifiée.

    Mineurs corrigés : journaux de CI (fichiers cachés), attente de `pg_isready`, « status check » requis sur `main`.
  - `ui-auditor` : « SHIP », aucune régression par rapport à M5 (aucun fichier d'UI touché). Les remarques mineures
    (zones tactiles de la vue et de l'éditeur upstream) datent d'avant M6.
