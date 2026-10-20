# Feuille de route du fork

Chaque jalon = une session Claude Code autonome = une PR. Les critères ci-dessous sont la définition de « fini ».
M2 à M4 sont une proposition par défaut : l'entretien de cadrage (SPEC.md) les précise avant leur lancement.
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
Proposition par défaut, à remplacer par la section correspondante de SPEC.md.
- [ ] Écran Aliments repensé : navigation par rayon et par hiérarchie, recherche instantanée, aliments sans rayon mis en évidence.
- [ ] Édition rapide d'un aliment dans une feuille (rayon, parent, substituts, en stock) sans changer de page.
- [ ] Actions groupées : déplacer, changer de rayon, fusionner des doublons avec aperçu et confirmation.
- [ ] Toute donnée nouvelle vit dans `kitchen/` ; tests pytest pour chaque endpoint ajouté ; `verify.sh --ui m3` OK.

## M4 — Création et édition de recettes [ ]
Proposition par défaut, à remplacer par la section correspondante de SPEC.md.
- [ ] Éditeur mobile en étapes : infos, ingrédients, étapes, photo ; navigation sans perte de saisie.
- [ ] Saisie d'ingrédients en texte libre (« 200 g de pâtes ») via le parseur existant, création d'aliment à la volée.
- [ ] Réordonner ingrédients et étapes par glisser-déposer ; brouillon conservé si on quitte la page.
- [ ] Import par URL intégré au même flux ; `verify.sh --ui m4` OK.

## M5 — Livraison sur le homelab [ ]
- [ ] Workflow GitHub Actions qui construit l'image Docker du fork et la publie sur GHCR (tag = version upstream + suffixe fork).
- [ ] `docs/fork/DEPLOY.md` : stack compose pour Komodo, sauvegarde de la base avant bascule, test sur une copie, retour arrière vers l'image upstream.
- [ ] Vérification que les migrations de `kitchen/` s'appliquent sur une base Postgres créée par l'image upstream (service Postgres de la session).

## Récurrent — synchronisation upstream
À chaque release Tandoor : `/upstream-sync` (branche `sync/upstream-<tag>`, PR dédiée).

## Propositions M0
(rempli par la session M0)
