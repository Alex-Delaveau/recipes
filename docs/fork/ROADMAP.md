# Feuille de route du fork

Chaque jalon = une session Claude Code autonome = une PR. Les critères ci-dessous sont la définition de « fini ».
M3 et M4 découlent de SPEC.md (cadrage du 2026-10-20) ; M2 reste la proposition initiale.
Statut : `[ ]` à faire, `[x]` fait. Un jalon est terminé quand sa PR est fusionnée.

## M0 — Socle et audit [ ]
Aucun changement visible pour l'utilisateur.
- [ ] `docs/fork/gitignore.append` est intégré à `.gitignore`.
- [ ] `scripts/fork/setup.sh` fonctionne dans la session cloud ; baseline enregistrée (`verify.sh --update-baseline`) et commitée dans `docs/fork/baseline/`.
- [ ] Captures de référence publiées : `verify.sh --ui m0-baseline --publish`.
- [ ] App Django `kitchen/` créée (vide, un test pytest trivial, enregistrée dans `INSTALLED_APPS`) ; `verify.sh` reste OK.
- [ ] `docs/fork/AUDIT.md` rédigé :
  - carte de l'UI (pages, composants partagés, thème Vuetify, navigation mobile/desktop, stores Pinia) ;
  - ce qui existe déjà pour les aliments (arbre `Food`, catégories de rayon, substituts, propriétés, pantry/inventaire, éditeur d'ingrédients, open data) et pour la création de recettes (éditeur, parseur d'ingrédients, import) ;
  - points de friction mobile vus sur les captures `m0-baseline` ;
  - évaluation du système de plugins Tandoor (`recipes/plugins`, `vue3/src/plugins`) face à l'app `kitchen/` ;
  - ajustements proposés pour M1–M4 (ajoutés en fin de ce fichier, section « Propositions M0 », sans modifier les jalons).

## M1 — Fondations visuelles [ ]
- [ ] Thème Vuetify clair et sombre construit à partir des tokens de DESIGN.md (couleurs, typographie, rayons, élévations, espacements).
- [ ] Transitions en fondu entre les vues (≤ 200 ms), désactivées si `prefers-reduced-motion`.
- [ ] Coquille d'application : barre du bas sur mobile (4–5 entrées max), en-tête compact, tiroir sur desktop ; zones tactiles ≥ 44 px.
- [ ] Aucune route de `routes.json` ne déborde horizontalement à 360 px ; toutes passent en `"strict": true`
      (exception justifiée dans DECISIONS.md si une erreur upstream ne peut pas être corrigée dans le fork).
- [ ] Aucune régression : `verify.sh --ui m1` OK, rapport `ui-auditor` sans problème bloquant.

## M2 — Parcours cuisine sur mobile [ ]
- [ ] Accueil/recherche : recherche visible immédiatement, filtres en bottom sheet, cartes de recette lisibles à une main.
- [ ] Vue recette en « mode cuisine » : ingrédients cochables, portions ajustables, étapes en gros caractères, écran maintenu allumé.
- [ ] Liste de courses : cocher en un tap, regroupement par rayon, ajout rapide d'un article, annulation possible.
- [ ] Pages refaites en `strict` ; `verify.sh --ui m2` OK.

## M3 — Organisation des aliments [ ]
Découle de SPEC.md, section « Organisation des aliments — attendu ».
- [ ] Écran Aliments en vue arbre à 2 niveaux (famille > aliment) :
  - familles repliables, recherche instantanée, filtre « sans rayon » ;
  - déplacement vers une autre famille en 2 taps ;
  - un aliment hérite du rayon de sa famille par défaut ;
  - aucun tableau à colonnes sur mobile.
- [ ] Rayon suggéré à chaque création d'aliment (import, saisie, liste de courses), puis confirmé en un tap :
  - ordre de suggestion : rayon de la famille, puis dictionnaire français d'aliments courants dans `kitchen/`, puis
    aliment au nom proche ;
  - file « à ranger » à vider en rafale, un tap par rayon.
- [ ] Ordre de rayons générique en français pré-rempli (fruits et légumes → … → hygiène/maison) et réglable. La liste de
      courses est groupée selon cet ordre.
- [ ] Écran « doublons probables » (pluriels, accents, mots en plus) :
  - fusion avec aperçu (recettes et articles concernés) et confirmation, via l'API de fusion existante ;
  - création automatique d'un alias `FOOD_ALIAS`.
- [ ] Relecture d'un import URL : pour chaque ingrédient d'aliment inconnu, proposition de l'aliment existant le plus
      proche. Le choisir crée un alias `FOOD_ALIAS`.
- [ ] Édition rapide d'un aliment dans une feuille du bas (nom, pluriel, famille, rayon, « jamais en courses »), sans
      changer de page.
- [ ] Rien n'est ajouté pour le stock ni le garde-manger (hors périmètre).
- [ ] Toute donnée nouvelle vit dans `kitchen/`. Tests pytest pour chaque endpoint ajouté, dont un test qui fait
      détecter les doublons par la règle de similarité sur un jeu d'exemples français. `verify.sh --ui m3` OK.

## M4 — Création et édition de recettes [ ]
Découle de SPEC.md, section « Création de recettes — attendu ».
- [ ] Reconnaissance des ingrédients en français, sans modifier `cookbook/helper/ingredient_parser.py` (alias d'unités et
      prétraitement dans `kitchen/`) :
  - unités françaises (c. à soupe, cs, càc, pincée, gousse, sachet, brin, botte…) ;
  - « de/d'/des » retirés ;
  - précisions placées en note ;
  - pluriels ramenés à l'aliment existant ;
  - fractions ½, 1/2, 1,5.

  Un jeu d'au moins 30 lignes réelles est testé en pytest. Il passe aussi par l'import URL et par la liste de courses.
- [ ] L'assistant d'import URL existant est conservé. Il bénéficie de la reconnaissance française et de la proposition
      d'aliment proche de M3.
- [ ] Saisie guidée sur mobile en 4 écrans :
  1. Nom et portions.
  2. Ingrédients (collage multi-ligne ou ligne à ligne, reconnaissance en direct, correction d'une ligne dans une
     feuille du bas).
  3. Étapes (un paragraphe chacune, réordonnables).
  4. Détails (temps, mots-clés, photo depuis la galerie).

  Navigation avant/arrière sans perte de saisie. Brouillon conservé si l'on quitte la page.
- [ ] Liste unique d'ingrédients pour les recettes créées dans le fork, stockée dans la première étape.
  - La vue recette l'affiche en une seule liste en haut.
  - Les recettes importées déjà découpées par étape gardent leur découpage.
- [ ] Bouton « Ajouter » de la barre du bas : une feuille à deux choix, « Depuis un site (URL) » et « Saisir une recette ».
- [ ] Une recette existante se modifie sur mobile avec le même découpage en écrans.
- [ ] Pages refaites en `strict`. `verify.sh --ui m4` OK.

## M5 — Livraison sur le homelab [ ]
- [ ] Workflow GitHub Actions qui construit l'image Docker du fork et la publie sur GHCR (tag = version upstream + suffixe fork).
- [ ] `docs/fork/DEPLOY.md` : stack compose pour Komodo, sauvegarde de la base avant bascule, test sur une copie, retour arrière vers l'image upstream.
- [ ] Vérification que les migrations de `kitchen/` s'appliquent sur une base Postgres créée par l'image upstream (service Postgres de la session).

## Récurrent — synchronisation upstream
À chaque release Tandoor : `/upstream-sync` (branche `sync/upstream-<tag>`, PR dédiée).

## Propositions M0
(rempli par la session M0)
