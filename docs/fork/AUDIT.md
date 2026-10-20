# Audit du code existant (M0)

Rédigé en M0, le 2026-10-20, sur la base `master` d'upstream (Tandoor 2.6).
Les chemins sont relatifs à la racine du dépôt. Les captures citées sont dans `docs/fork/screens/m0-baseline/`.

## 1. Carte de l'UI (vue3)

### Point d'entrée, routes
- L'application Vue est créée dans `vue3/src/apps/tandoor/main.ts`, avec Pinia, Vuetify, vue-router (`createWebHistory`),
  vue-i18n et mavon-editor.
- Django la sert via `cookbook/templates/frontend/tandoor.html` ; la route attrape-tout est `path('<path:resource>', views.index)`
  à la fin de `cookbook/urls.py`. La page de connexion reste un template Django (`/accounts/login/`).
- Routes (`main.ts`, l. 17-75), toutes dans `vue3/src/pages/` :

  | Domaine | Routes |
  |---|---|
  | Accueil, recherche | `/` StartPage, `/advanced-search` SearchPage, `/search` (redirige vers `/`) |
  | Recettes | `/recipe/:id` RecipeViewPage, `/recipe/import` RecipeImportPage, `/edit/:model/:id?` ModelEditPage (éditeur générique, `Recipe` compris) |
  | Courses, plan | `/shopping` ShoppingListPage, `/mealplan` MealPlanPage |
  | Données | `/list/:model?` ModelListPage (tableau générique), `/delete/:model/:id?`, `/database`, `/ingredient-editor`, `/property-editor` |
  | Garde-manger | `/pantry`, `/inventory/booking` |
  | Livres | `/books`, `/book/:bookId` |
  | Mise en route | `/welcome`, `/household-setup`, `/space-setup`, `/help`, `/test`, 404 |
  | Réglages | `/settings/{account,cosmetic,shopping,meal-plan,search,space,open-data-import,export,api}` (`components/settings/`) |

  Les plugins ajoutent leurs routes à la fin (voir § 5).

### Coquille (`vue3/src/apps/tandoor/Tandoor.vue`)
- **En-tête** `v-app-bar` : logo, recherche globale (`GlobalSearchDialog`), menu « + » (créer / importer une recette),
  avatar avec le menu utilisateur. Couleur réglable par espace ou par utilisateur (`navBgColor`), barre collante en option.
- **Tiroir** de navigation seulement si `lgAndUp` (≥ 1280 px) ; **barre du bas** sinon, avec 3 entrées fixes
  (Accueil, Plan, Courses) et un bouton « ☰ » qui ouvre une feuille avec le reste.
- Les entrées viennent de `vue3/src/composables/useNavigation.ts` (`getNavigationDrawer`, `getBottomNavigation`,
  `getUserNavigation`), plugins compris.
- Mobile/desktop : seuils Vuetify par défaut (sm 600, md 960, lg 1280). `useDisplay().mobile` (= < 1280 px) pilote les
  dialogues plein écran dans de nombreux composants ; `breakpoint_utils.ts` règle le nombre de colonnes de l'accueil.
- Au montage : `useUserPreferenceStore().init()`, puis redirection vers l'assistant d'espace ou de foyer si non terminé.

### Composants partagés (`vue3/src/components/`)
- `model_editors/` : `ModelEditorBase.vue` (carte ou dialogue, enregistrer/supprimer) + un `*Editor.vue` par modèle
  (Food, Recipe, Unit, Keyword, SupermarketCategory, Supermarket, Automation, ShoppingListEntry…).
- `inputs/` : `ModelSelect.vue` (vueform/multiselect), `VModelSelect.vue`, `StepEditor.vue`, `StepMarkdownEditor.vue`,
  `HierarchyEditor.vue`, `CategorySelectChip.vue`, `ShoppingListEntryInput.vue`, `GlobalSearchDialog.vue`…
- `dialogs/` : `ModelMergeDialog` (fusion + alias), `BatchEditFoodDialog`, `AddToShoppingDialog`,
  `RecipeScalingDialog`, `StepIngredientSorterDialog`, `DeleteConfirmDialog`…
- `display/` : `RecipeView`, `RecipeCard`, `StepView`, `IngredientsTable`, `ScalableNumber`, `ShoppingListView`,
  `ShoppingLineItem`, `MealPlanView`, `HorizontalRecipeWindow`…
- Registre des modèles : `vue3/src/types/Models.ts` (`registerModel`, `editorComponent`, `isTree`, `isMerge`,
  `mergeAutomation: 'FOOD_ALIAS'` pour `TFood`). C'est lui qui pilote `ModelListPage` et `ModelEditPage`.
- Client API généré dans `vue3/src/openapi` (ne pas éditer).

### Thème Vuetify (`vue3/src/vuetify.ts`)
- Icônes Font Awesome (`defaultSet: 'fa'`) avec des alias métier (save, delete, shopping, mealplan…).
- Défauts globaux : `VCardActions` en `float-right`, `VContainer` max 1400 px, `VSwitch` primaire.
- Thèmes `light` (défaut) et `dark`, mêmes couleurs de marque : `primary #b98766`, `secondary #b55e4f`,
  `tandoor #ddbf86`, `background #f5efea` (clair seulement), plus des couleurs d'action `save/create/edit/delete/cancel`.
- Bascule sombre via `UserPreferenceStore.updateTheme()` selon le réglage `TANDOOR_DARK`.
- Pas de police propre (Roboto par défaut de Vuetify), pas de SCSS. Le CSS global est un gros bloc `<style>` de
  `Tandoor.vue` (l. 189-465 : liens en sombre, calendrier, mavon-editor, multiselect) + `assets/vueform.css`
  + un CSS par espace optionnel injecté dans `tandoor.html`.
- **Conséquence pour M1** : le thème est déjà le point d'entrée naturel (couleurs, `defaults`) ; les rayons,
  typographie et élévations ne sont pas tokenisés aujourd'hui.

### i18n
- `vue3/src/i18n.ts` : `en.json` chargé d'emblée, la langue de `<html lang>` chargée à la demande ; les langues sous
  25 % de couverture sont exclues. Les plugins peuvent fusionner leurs propres fichiers de traduction.

### Stores Pinia (`vue3/src/stores/`)
| Store | Contenu |
|---|---|
| `UserPreferenceStore` | réglages appareil (`deviceSettings`, en localStorage), utilisateur, serveur, espace actif, thème |
| `ShoppingStore` | entrées de courses, rayons, magasins, listes ; regroupement (rayon / auteur / recette), synchro automatique, file de synchro, pile d'annulation |
| `MealPlanStore` | cache du plan de repas par période |
| `MessageStore` | messages et snackbars |

## 2. Aliments : ce qui existe déjà

| Besoin du fork | Existant upstream | Où |
|---|---|---|
| Arbre famille > aliment | `Food` est un `TreeModel` treebeard (chemin matérialisé) ; API `PUT /api/food/{id}/move/{parent}/` (0 = racine) ; paramètres `root`, `tree` | `cookbook/models.py` (`TreeModel` l. 65, `Food` l. 774), `views/api.py` `TreeMixin` l. 441 |
| Hériter du rayon de la famille | héritage de champs `inherit_fields` / `child_inherit_fields`, défauts par espace `Space.food_inherit`, appliqué par signaux `post_save` ; `api/reset-food-inheritance/` | `models.py` l. 250 et 318, `cookbook/signals.py` |
| Rayon | `Food.supermarket_category` (FK `SupermarketCategory`) | `models.py` l. 642 |
| Ordre des rayons | **par magasin** : `Supermarket` + `SupermarketCategoryRelation.order` | `models.py` l. 669-690, `SupermarketEditor.vue` |
| Liste groupée par rayon | `ShoppingStore.getEntriesStructure()` groupe par rayon ; l'ordre suit le magasin sélectionné, sinon l'ordre alphabétique ; le groupe « sans rayon » vient en premier | `stores/ShoppingStore.ts` l. 74-125, 398 |
| Changer le rayon depuis la liste | `CategorySelectChip.vue` → `ShoppingStore.updateCategories` | |
| Fusion de doublons | `PUT /api/food/{id}/merge/{target}/` (ingrédients et articles déplacés) ; `ModelMergeDialog` peut créer l'alias `FOOD_ALIAS` | `views/api.py` `MergeMixin` l. 345, `Food.merge_into` |
| Alias | `Automation` : `FOOD_ALIAS`, `UNIT_ALIAS`, `KEYWORD_ALIAS`, `NEVER_UNIT`, `TRANSPOSE_WORDS`, remplacements regex… ; moteur `AutomationEngine` | `models.py` l. 1669, `cookbook/helper/automation_helper.py` |
| Pluriel | `Food.plural_name`, `Unit.plural_name` | |
| Substituts | `substitute` (M2M), `substitute_siblings`, `substitute_children` | `helper/food_availability_helper.py` |
| « Jamais en courses » | `Food.ignore_shopping` (héritable) | |
| Édition groupée | `PUT /api/food/batch_update/`, `BatchEditFoodDialog.vue` | `views/api.py` l. 1315 |
| Propriétés / nutrition | `PropertyType`, `Property`, `FoodProperty`, import USDA FDC, `PropertyEditorPage` | hors périmètre |
| Stock, garde-manger | `onhand_users` (« en stock » par utilisateur), `InventoryLocation`, `InventoryEntry`, `InventoryLog`, `PantryPage`, `InventoryBookingPage` | hors périmètre |
| Open Data | `api/import-open-data/` + `OpenDataImporter` (unités, rayons, propriétés, magasins, aliments, conversions) ; réglage `/settings/open-data-import` | `helper/open_data_importer.py` |
| Écrans | `/list/Food` (tableau paginé générique), `FoodEditor.vue` à onglets (aliment, propriétés, conversions, hiérarchie, divers), `IngredientEditorPage` | |

À retenir :
- **Presque tout le modèle de données nécessaire à M3 existe.** Il manque :
  - un ordre de rayons « sans magasin » ;
  - un dictionnaire de rayons ;
  - la notion « rayon confirmé / à ranger » ;
  - une règle de similarité de noms.

  Tout cela peut vivre dans `kitchen/`.
- L'ordre de rayons générique peut s'appuyer sur un `Supermarket` unique créé par le fork (« Ordre générique »),
  sélectionné par défaut. Cela réutilise `SupermarketCategoryRelation.order` sans changer le modèle upstream.
  Autre option : une table d'ordre dans `kitchen/`. Le choix est à trancher en M3.

## 3. Création de recettes : ce qui existe déjà

- **Éditeur** `components/model_editors/RecipeEditor.vue` (via `/edit/Recipe/:id`) :
  - onglets Recette (nom, image, mots-clés, temps, portions, diamètre…), Étapes, Propriétés, Divers ;
  - les étapes sont des `StepEditor.vue` : instructions Markdown, tableau d'ingrédients par étape avec tri par
    glisser-déposer, dialogue d'édition d'un ingrédient sur mobile ;
  - un collage multi-ligne (`parseAndInsertIngredients`) appelle `POST /api/ingredient-parser/` ;
  - `StepIngredientSorterDialog` déplace des ingrédients entre étapes.
- **Parseur** `cookbook/helper/ingredient_parser.py`, classe `IngredientParser` :
  - `parse()` renvoie `(quantité, unité, aliment, note)` et `parse_as_ingredient()` un dictionnaire ;
  - il applique les automatisations (`TRANSPOSE_WORDS`, `NEVER_UNIT`, `UNIT_ALIAS`, `FOOD_ALIAS`) ;
  - `get_unit` et `get_food` créent les objets manquants ;
  - l'API est `IngredientParserView`, sur `/api/ingredient-parser/`.
- **Mesure sur des lignes françaises** (base démo, sans automatisations) :

  | Entrée | Sortie (quantité, unité, aliment, note) |
  |---|---|
  | `2 c. à soupe d'huile d'olive` | 2, `c.`, `à soupe d'huile d'olive`, — |
  | `1 cs de sucre` | 1, `cs`, `de sucre`, — |
  | `3 oignons émincés` | 3, `oignons`, `émincés`, — |
  | `½ citron` | 0,5, —, `citron`, — ✅ |
  | `1,5 kg de pommes de terre` | 1,5, `kg`, `de pommes de terre`, — |
  | `200 g de farine T55` | 200, `g`, `de farine T55`, — |
  | `2 gousses d'ail` | 2, `gousses`, `d'ail`, — |
  | `2-3 tomates bien mûres` | 2, `tomates`, `bien mûres`, note `2-3` |

  Constats :
  - les fractions et la virgule décimale passent ;
  - les unités françaises en plusieurs mots ne passent pas ;
  - « de / d' » reste collé à l'aliment ;
  - sans unité connue, le premier mot de l'aliment est pris pour l'unité (`oignons`, `tomates`) ;
  - les précisions finissent dans l'aliment ;
  - les pluriels créent de nouveaux aliments.

  C'est exactement le périmètre de M4. Un prétraitement dans `kitchen/` (normaliser l'unité, retirer l'article,
  séparer la précision) avant `IngredientParser.parse()`, avec des `UNIT_ALIAS` semés, couvre ces cas.
- **Import URL** :
  - côté serveur, `RecipeUrlImportView` (`POST /api/recipe-from-source/`) appelle recipe-scrapers puis
    `cookbook/helper/recipe_url_import.py:get_from_scraper()`, qui passe par l'`IngredientParser`. La recette n'est
    pas enregistrée : elle est renvoyée pour relecture ;
  - côté client, `RecipeImportPage.vue` (≈ 1 000 lignes) est un `v-stepper` : Import → Doublons → Image → Mots-clés →
    Étapes → Enregistrer.
- **Autres imports** : IA (`/api/ai-import/`), ~25 applications (`cookbook/integration/`), bookmarklet. Hors périmètre.

## 4. Points de friction mobile (captures `m0-baseline`)

Contrôle automatique (`report.md`) : aucun débordement horizontal à 360 et 390 px. Les problèmes sont ailleurs.

| Écran | Constat | Capture |
|---|---|---|
| Toute l'app | La barre du bas n'a **que des icônes, sans libellés**. Le menu « ☰ » mélange réglages, import, base de données. Seules 3 vraies destinations. SPEC.md note qu'elle **recouvre le contenu**. Ce point n'est pas vérifiable ici : en capture pleine page, la barre fixe apparaît au milieu de l'image (artefact connu). M1 ajoutera une capture limitée à l'écran visible. | toutes |
| Toute l'app | En-tête haut de 56 px avec « + » et recherche en haut à droite, hors de portée du pouce. | toutes |
| Accueil | L'accueil montre le plan du jour et une seule recette « au hasard » en carrousel, puis un bouton « Voir les recettes ». **Pas de champ de recherche visible**, cartes sans photo (placeholder), flèches de carrousel. | `start-mobile.jpg` |
| Vue recette | L'en-tête de recette est dense (chips minuscules, temps en 3 colonnes de petit texte). Les ingrédients sont **par étape** avec des cases à cocher de 24 px. Les portions et la note sont tout en bas, après les métadonnées « Créé par / Créé / Mis à jour » en gros encadrés. Il n'y a pas de mode cuisine. 15 zones tactiles < 44 px. | `recipe-view-mobile.jpg` |
| Éditeur de recette | Onglets **tronqués** (« Propriétés », le 4ᵉ coupé). Le formulaire est long : diamètre, texte des portions, aide sur le diamètre. Le bouton Enregistrer est un bouton flottant isolé à droite, au milieu du formulaire. Champs numériques avec flèches haut/bas. 11 petites zones tactiles. | `recipe-edit-mobile.jpg` |
| Aliments | Tableau paginé (10 par page) à 4 colonnes, noms et rayons sur deux lignes, cases à cocher et menus « ⋮ ». Le bloc d'en-tête prend un tiers de l'écran avec un texte d'aide. Pas d'arbre, pas de filtre « sans rayon ». | `food-list-mobile.jpg` |
| Courses | Barre d'outils de boutons-icônes sans libellés, plus deux menus (« Supermarché », « Liste de courses ») qui **sortent de l'écran** dans un défilement horizontal. Le champ d'ajout s'appuie sur un exemple en placeholder. Liste vide sans état vide explicite. | `shopping-mobile.jpg` |
| Plan de repas | Calendrier mensuel à 7 colonnes de 50 px, illisible sur téléphone. Hors périmètre, à part le thème (SPEC). | `mealplan-mobile.jpg` |
| Garde-manger | Tableau à 4 colonnes aux en-têtes coupés sur 3 lignes, pagination. Hors périmètre. | `pantry-mobile.jpg` |
| Réglages | Menu de réglages puis page Profil dans le même flux. Boutons pleine couleur alignés à gauche et de couleurs variées (marron, jaune, bleu) : pas de hiérarchie d'action. | `settings-mobile.jpg` |

Erreurs relevées pendant les captures (upstream, sans effet visible) :
- `POST /api/view-log/` → 403 à l'ouverture d'une recette, et sur le plan de repas en desktop ;
- `TypeError … reading 'id'` dans `AccountSettings` à 390 px.

Elles sont à garder en tête : une page passée en `strict` échouera sur ces erreurs JS.

## 5. Système de plugins Tandoor face à l'app `kitchen/`

**Ce que fait le système de plugins** :
- **Backend** (`recipes/settings.py`, l. 209-245) : chaque dossier de `recipes/plugins/` (ignoré par git, absent ici) est
  importé. Son `AppConfig` est ajouté à `INSTALLED_APPS`, ce qui permet modèles, migrations et admin. Le plugin
  déclare aussi :
  - `base_url`, monté dans `recipes/urls.py` (l. 46-56) ;
  - un routeur DRF, fusionné dans `/api/` (`cookbook/urls.py`, l. 76-81).

  La classe `AppConfig` est trouvée par une heuristique fragile (`dir(module)[1]`). `plugin.py` fait un `git pull`
  puis lance le `setup_repo.py` de chaque plugin, qui crée un lien vers son code Vue.
- **Frontend** (`vue3/src/types/Plugins.ts`) : `import.meta.glob('@/plugins/*/plugin.ts')`. Un plugin peut fournir :
  - des routes et des routes de réglages ;
  - des entrées de tiroir, de barre du bas et de menu utilisateur ;
  - des traductions ;
  - un composant pour la page Base de données et un pour la page Réglages ;
  - des entrées de build Vite supplémentaires.
- **Limites** :
  - aucun point d'injection dans les pages existantes (vue recette, liste de courses, éditeur d'aliment) ;
  - pas de remplacement de la coquille ni du thème ;
  - le code Vue d'un plugin vit hors du dépôt, dans un dossier ignoré, et se branche par lien symbolique.
- **Anomalie upstream** : `useNavigation.ts:6` importe `@/plugins/open_data_plugin/plugin.ts`, absent du dépôt. C'est
  une des 650 erreurs vue-tsc de la baseline ; le build Vite passe quand même.

**Évaluation** :

| Critère | Plugin Tandoor | App `kitchen/` + `vue3/src/fork/` |
|---|---|---|
| Backend (modèles, endpoints) | équivalent : c'est aussi une app Django | app Django normale, versionnée dans le fork |
| Refonte de la coquille, du thème, des pages existantes (M1, M2) | **impossible** sans toucher l'upstream | possible, avec des diffs ciblés |
| Code versionné et testé avec le fork | non (dépôt séparé, dossiers ignorés, liens symboliques) | oui (`verify.sh`, pytest, vue-tsc) |
| Image Docker du fork (M5) | demande d'embarquer le dépôt du plugin | rien à faire |
| Coût de synchro upstream | nul pour le plugin, mais la refonte UI touche l'upstream de toute façon | faible si les règles du fork sont tenues |

**Conclusion** : on garde `kitchen/` (backend) et `vue3/src/fork/` (front), comme prévu. Le système de plugins ne
couvre que l'ajout de pages et d'entrées de menu, pas la refonte demandée. Mécanismes qu'on peut réutiliser tels quels :
- le motif « routeur DRF de l'app fusionné dans `/api/` » ;
- éventuellement l'ajout d'entrées de navigation.

`kitchen/` est déclarée explicitement dans `INSTALLED_APPS` (une ligne), plutôt que d'être chargée comme plugin.

## 6. Notes d'outillage (M0)

- `verify.sh` lançait pytest avec `DJANGO_SETTINGS_MODULE=recipes.settings` exporté, ce qui prenait le pas sur
  `pytest.ini`. Les connecteurs externes démarraient, et pytest ne rendait jamais la main. Il utilise désormais
  `--ds recipes.test_settings`, comme upstream (1 test en échec seulement : `test_markdown_renderer`, rendu des
  citations par la version installée de la bibliothèque Markdown). Il lance aussi `kitchen/tests`.
- Baseline : 650 erreurs vue-tsc, 1 test en échec (voir `docs/fork/baseline/`).
- Le jeu de démo crée maintenant un foyer ; sans foyer, l'application s'ouvrait sur l'assistant « Foyers » et les
  captures de l'accueil étaient inutiles.
