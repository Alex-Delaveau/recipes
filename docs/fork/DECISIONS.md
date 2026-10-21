# Décisions

Journal des choix faits en autonomie, à relire par Alex. Le plus récent en haut.
Format : `## AAAA-MM-JJ — Mx — titre` puis **Contexte**, **Choix**, **Alternative écartée**, **Réversible ?**

## 2026-10-21 — M7 — Branche de travail
**Contexte** : la session cloud impose la branche `claude/zen-ramanujan-cnfub4`.
**Choix** : M7 est développé sur cette branche, au lieu de `fork/m7-prix`, comme pour M5 et M6.
**Alternative écartée** : créer `fork/m7-prix`. La session ne peut pas pousser ailleurs.
**Réversible ?** Oui. Seul le nom de la branche change.

## 2026-10-21 — M7 — Dictionnaire de prix moyens : source et date
**Contexte** : la feuille de route demande ~150 prix moyens français, marqués « estimés », avec leur source et leur date.
**Choix** :
- `kitchen/price_dictionary.py` contient environ 200 aliments courants. Chacun a un prix en €/kg, €/L ou €/pièce et,
  quand c'est utile, le poids d'une pièce (oignon 150 g, œuf 60 g, citron 120 g).
- **Source** : des ordres de grandeur de prix en grande surface de milieu de gamme en France métropolitaine,
  2025-2026, arrondis.
  - Ils sont écrits de mémoire, d'après les prix moyens à la consommation publiés par l'INSEE et les relevés de
    FranceAgriMer (RNM).
  - Ce n'est pas un relevé fait pour ce jalon : la session n'a pas consulté ces sources.
- **Date** : octobre 2026.
- Ces prix servent de point de départ. Ils sont ensuite corrigés par l'ajustement après les courses, ou à la main.
- Ils ne sont **pas** appliqués d'office à la création d'un aliment :
  - l'écran « Aliments sans prix » les propose un par un, ou tous d'un coup (« Tout appliquer ») ;
  - la fiche aliment propose le prix moyen quand l'aliment n'a pas de prix ;
  - les données de démo les reçoivent, sauf « Lardons » et « Lait de coco », gardés sans prix pour montrer l'écran.
**Alternative écartée** :
- appliquer le dictionnaire à chaque nouvel aliment : l'écriture se ferait en arrière-plan pendant les imports, et
  certains tests upstream comptent les propriétés d'un aliment ;
- télécharger une base de prix : il n'existe pas de source publique et stable.
**Réversible ?** Oui. Pour appliquer d'office, il suffit d'appeler `apply_suggestion` dans `on_food_created`.

## 2026-10-21 — M7 — Où et comment le prix est stocké
**Contexte** : upstream exprime toutes les propriétés d'un aliment (nutrition, prix) pour une même référence :
`properties_food_amount` de `properties_food_unit`, souvent 100 g.
**Choix** :
- Le prix est la propriété du type de catégorie `PRICE`. `kitchen.prices.price_type` crée ce type (« Prix », €)
  quand il n'y en a aucun.
  Les écrans upstream continuent donc de le lire.
- Si l'aliment n'a pas encore de référence, ou s'il n'a que le prix comme propriété, la référence devient l'unité du
  prix. On réutilise une unité existante (`g` → 1000 g, `ml` → 1000 ml, `pièce`), sinon on crée `kg`, `l` ou `pièce`.
- Si l'aliment a déjà des valeurs nutritionnelles, le prix est converti dans leur référence (2,50 €/kg → 0,25 € pour
  100 g). Un prix à la pièce n'y est accepté que si l'on connaît le poids d'une pièce. Sinon, l'écran l'explique.
- `kitchen` ajoute à `KitchenFood` (migration 0003) :
  - l'origine du prix (estimé / confirmé) ;
  - son poids dans le lissage ;
  - le paquet : quantité, nature, prix ;
  - le poids d'une pièce.
- Un prix saisi ailleurs (écrans upstream) compte comme confirmé.
**Alternative écartée** : un champ prix dans `kitchen` seul. Upstream ne le verrait pas, et la feuille de route demande
la propriété upstream.
**Réversible ?** Oui. `migrate kitchen 0002` retire les champs ; les propriétés Prix restent des propriétés upstream
ordinaires.

## 2026-10-21 — M7 — Règles de calcul
**Contexte** : il faut convertir les quantités des recettes et des courses vers l'unité du prix, sans réglage préalable.
**Choix** :
- **Quantités** :
  - Tout est ramené en grammes, millilitres ou pièces.
  - D'abord les unités de base upstream et les noms français courants (g, kg, cl, l, c. à soupe = 15 ml, c. à café =
    5 ml, pincée = 0,5 g, gousse = 5 g). Une ligne sans unité compte des pièces.
  - Ensuite, les conversions d'unités de l'espace (upstream).
- **Passages entre unités** :
  - pièce ↔ poids : par le poids d'une pièce (celui de l'aliment, sinon celui du dictionnaire) ;
  - poids ↔ volume : densité 1. C'est une estimation : 20 cl de crème font 200 g.
- **Recette** :
  - Les aliments « jamais en courses » (sel, eau) et les lignes sans quantité ne comptent pas.
  - Le prix est proportionnel, pour les portions de la recette. La page le met à l'échelle des portions choisies.
- **Liste de courses** :
  - Les entrées sont regroupées par aliment.
  - Avec un paquet, on compte des paquets entiers : prix du paquet, sinon prix unitaire × taille du paquet.
  - Un paquet dont le prix est saisi compte comme confirmé.
- **Ce qui n'entre pas dans le total** : toujours affiché (« 2 articles sans prix »). Un tap donne la liste et la
  raison (sans prix, ou quantité non convertible).
- **Ajustement après les courses** :
  - Les prix confirmés sont tenus pour justes.
  - Le reste de l'écart porte sur les prix estimés : facteur = (payé − part confirmée) / part estimée.
  - Ce facteur est borné entre ×0,33 et ×3, pour qu'une faute de frappe ou un oubli ne fasse pas tout dériver.
  - **Lissage** : chaque prix va vers sa nouvelle valeur de 1 / (n + 1), où n est le nombre d'observations qu'il
    représente. L'estimation vaut 1 observation, chaque ticket en ajoute 1, avec un plafond de 4. Le premier ticket
    déplace donc le prix de moitié, puis d'un tiers, d'un quart, d'un cinquième.
  - L'écart affiché (« +21 % ») est celui du ticket, avant lissage.
- « Corriger » un article donne au prix de l'aliment ce qui a été payé pour la quantité de la liste, ou au prix du
  paquet si l'article se compte en paquets. Ce prix devient confirmé.
- Seuls les articles cochés et visibles sur l'appareil comptent dans « Courses terminées ».
**Alternative écartée** :
- appliquer tout l'écart d'un coup : une promo fausserait tous les prix ;
- répartir aussi l'écart sur les prix confirmés : contraire à la feuille de route.
**Réversible ?** Oui. Les constantes (`MAX_WEIGHT`, bornes du facteur) sont dans `kitchen/prices.py`.

## 2026-10-21 — cadrage — M7 « Estimation du prix des courses »
**Contexte** : Alex veut un estimateur de prix. Trois niveaux ont été proposés :
1. un prix par aliment saisi à la main ;
2. le même, avec un dictionnaire de prix moyens et le prix au paquet ;
3. les prix des enseignes en ligne.

**Choix** : Alex retient le niveau 2 et y ajoute une façon simple d'ajuster les prix après les courses, d'après le
total payé. Le jalon M7 est ajouté à ROADMAP.md.
- Les prix vivent dans la propriété Prix upstream. Ce qu'elle ne sait pas porter (origine estimé / confirmé, paquet,
  poids à la pièce) va dans `kitchen/`.
- L'ajustement au total payé ne touche que les prix « estimés », proportionnellement et lissé. Un prix corrigé à la main
  devient « confirmé » et ne bouge plus.

**Alternative écartée** : niveau 3 (pas d'API publique, fragile, contraire aux conditions des sites) ; saisir chaque
article du ticket (trop long).
**Réversible ?** Oui. Le jalon n'est pas commencé.

## 2026-10-21 — hors jalon — Page « Tirer au sort » en grille de grandes photos
**Contexte** : Alex trouve les vignettes de la liste tirée trop petites, une recette par ligne.
**Choix** :
- Une grille de grandes photos carrées : 2 colonnes sur téléphone, 3 sur tablette, 4 sur ordinateur. Le nom et la
  durée sont en dessous.
- « Remplacer » et « Retirer » sont deux boutons ronds de 44 px posés sur la photo, avec un fond clair lisible sur
  toute image.
- Les boutons du bas prennent les libellés courts de la carte de l'accueil, « Au menu » et « Aux courses » ; le
  libellé complet reste pour les lecteurs d'écran.
- La carte « Cette semaine » de l'accueil garde ses lignes compactes : elle doit rester courte au-dessus des étagères.
**Alternative écartée** : une bascule liste / grille (inutile pour 5 à 10 plats).
**Réversible ?** Oui.

## 2026-10-21 — hors jalon — Recadrer la photo d'une recette (import et saisie)
**Contexte** : à l'import depuis Jow, l'image est prise telle quelle. Alex veut pouvoir la recadrer et la redimensionner.
**Choix** :
- **Fenêtre « Recadrer la photo »** (`ForkImageCropper`) : on fait glisser la photo, on zoome (pincement, molette ou
  curseur, jusqu'à ×4), avec trois formats : 16:9 (par défaut, celui de la page recette), 4:3 ou 1:1. Une grille des
  tiers aide au cadrage.
  - On la trouve à l'étape Image et à la dernière étape de l'import (l'étape Image est sautée quand le site ne propose
    qu'une photo), ainsi que dans l'assistant de saisie (photo de la galerie ou photo déjà enregistrée).
  - Un aperçu montre le résultat avant l'enregistrement.
- **La coupe est faite par le serveur** (`PUT /api/kitchen/recipes/<id>/image/`, Pillow) au moment d'enregistrer.
  - Un navigateur ne peut pas lire les pixels d'une photo venant d'un autre site (Jow), il ne peut donc pas la couper.
  - Le serveur télécharge la photo comme l'endpoint upstream (`safe_request`) ou reprend la photo enregistrée.
  - Il respecte l'orientation des photos de téléphone, limite la largeur à 1 600 px et ré-encode en JPEG (ce qui
    retire aussi les métadonnées).
- Page d'import upstream : diff limité au composant de la photo et à l'appel d'enregistrement. Sans recadrage, c'est
  le chemin upstream inchangé.

**Alternative écartée** :
- Recadrer dans le navigateur avec un canvas : impossible pour les photos d'autres sites.
- Ajouter une librairie de recadrage : dépendance lourde pour un geste simple.
- Faire pivoter la photo : rare pour des photos du web ; à ajouter si besoin.

**Réversible ?** Oui.

## 2026-10-21 — hors jalon — « Toutes les recettes » : aperçu sur l'accueil, page dédiée pour parcourir
**Contexte** : Alex trouve pénible de parcourir toutes les recettes en défilant une par ligne sur l'accueil.
**Choix** :
- L'accueil n'en montre plus que 6 (par nom), avec « Tout voir » et « Voir les N recettes ».
- La page `/recipes/all` est faite pour parcourir :
  - grille de vignettes par défaut : 2 colonnes sur téléphone, 3 sur tablette, 5 sur ordinateur ;
  - bascule grille / liste, gardée sur l'appareil ;
  - recettes regroupées par lettre, avec une barre de lettres qui reste en haut et saute à la lettre d'un tap ;
  - recherche instantanée.
- Toutes les recettes sont chargées d'un coup (100 par page, jusqu'à 2 000).
**Alternative écartée** : un « Charger plus » sur l'accueil (toujours une ligne par recette) ; une grille directement
sur l'accueil (elle repousse les étagères loin vers le bas).
**Réversible ?** Oui.

## 2026-10-21 — hors jalon — Règles des étagères « En moins de 30 min » et « Pas faites depuis longtemps »
**Contexte** : Alex demande comment ces catégories sont calculées. En relisant, deux défauts sont apparus :
- une recette sans durée comptait comme « 0 min », donc « rapide » ;
- « Pas faites depuis longtemps » ne comptait que les cuissons de l'utilisateur connecté (`lastcooked` upstream).
**Choix** :
- **En moins de 30 min** : temps total = préparation + attente, entre 1 et 30 min. Une recette sans durée n'y est plus
  (inconnue, pas rapide). Même règle pour le filtre « ≤ 15/30/60 min ».
- **Pas faites depuis longtemps** : un tri, pas un seuil. Les recettes jamais cuisinées viennent d'abord (par nom),
  puis celles dont la dernière cuisson est la plus ancienne. Une cuisson compte quel que soit le membre du foyer qui
  l'a faite. Elle est enregistrée par « Terminé » / « Bon appétit » à la fin du mode cuisine (M5) ou par le bouton
  « cuisiné » upstream. L'étagère montre les 10 premières.
**Alternative écartée** : garder l'annotation upstream par utilisateur (la recette faite hier par l'autre membre du
foyer serait « oubliée ») ; un seuil fixe (6 semaines) qui viderait l'étagère au début.
**Réversible ?** Oui.

## 2026-10-21 — hors jalon — Accueil des recettes : piste D, la semaine d'abord
**Contexte** : Alex choisit la piste D des maquettes (https://claude.ai/artifact/1jE7ee7MLBGGFvTv8inbX3). Il veut
pouvoir réduire ou étendre la partie « au hasard ».
**Choix** : sans recherche ni filtre, l'accueil affiche dans l'ordre :
1. **« Cette semaine »** : les plats tirés au sort, repliable. Repliée, c'est une ligne avec les vignettes ; l'état est
   gardé sur l'appareil.
   - On retire ou remplace un plat, on en ajoute un, ou on refait un nouveau tirage, avec annulation.
   - « Au menu » et « Aux courses » ouvrent la page du tirage sur la bonne feuille.
   - Le dé ouvre la page du tirage (nombre de plats).
2. Deux étagères : « En moins de 30 min » et « Pas faites depuis longtemps ». « Tout voir » applique le filtre
   correspondant. Pas d'étagère par mot-clé : Alex ne fait que des plats principaux.
3. **« Toutes les recettes »**, triées par nom, une par ligne : vignette de 52 px, nom, durée. Sur ordinateur, deux
   colonnes.

Une recherche, un filtre ou un raccourci n'affichent que les résultats, en lignes. Une recette sans photo a une tuile
de couleur avec son initiale, au lieu d'un rectangle gris. Le chip « Tirer au sort » disparaît : la carte le remplace.
**Alternative écartée** : pistes A, B et C (voir RECETTES-ACCUEIL.md).
**Réversible ?** Oui. `ForkRecipeCard` reste dans le code.

## 2026-10-21 — hors jalon — Le tirage remplit le menu de la semaine et les courses
**Contexte** : Alex veut que le tirage alimente directement le menu de la semaine et la liste de courses, comme chez
Jow.
**Choix** : deux boutons sous la liste tirée.
- **« Ajouter au menu »** : une recette par jour à partir du premier jour (aujourd'hui, demain après 21 h, modifiable),
  pour un type de repas (« Dîner » par défaut s'il existe, sinon le plus tardif), aux portions de la recette.
  - L'option « Ajouter aussi les ingrédients aux courses » est cochée par défaut. Elle passe par `addshopping` de
    l'API upstream des repas.
  - Sans aucun type de repas, un bouton crée « Dîner » (19:30).
- **« Ajouter aux courses »** : toutes les recettes, sans planifier (`/api/recipe/<id>/shopping/`, comme la page
  recette upstream), après confirmation.
- Aucun changement backend. La liste tirée reste après l'ajout : on peut la vider soi-même.

**Alternative écartée** :
- Choisir le jour de chaque recette : plus lent. On déplace ensuite dans le menu de la semaine.
- Passer par la feuille « décocher ce qu'on a » pour chaque recette : trop d'étapes pour 5 recettes. On décoche dans
  la liste de courses.

**Réversible ?** Oui.

## 2026-10-21 — hors jalon — « Tirer au sort » remplace le chip « Au hasard »
**Contexte** : Alex veut tirer X recettes au hasard, puis en retirer au cas par cas. Le chip « Au hasard » restait
sélectionné (un nouveau clic relançait le tirage au lieu de le désélectionner). Les chips choisis montraient deux
icônes côte à côte.
**Choix** :
- Page `/recipes/draw`. On choisit X (1 à 14, 5 par défaut), on tire, puis on retire, remplace, ajoute une recette ou
  refait le tirage, avec annulation.
- Le tirage suit les filtres de l'accueil. La liste est gardée sur l'appareil (`localStorage`), pas partagée avec le
  foyer.
- Le chip « Au hasard » devient « Tirer au sort » (lien vers la page, avec le nombre de recettes tirées).
- « Récentes » et « Pas faites depuis longtemps » se désélectionnent par un deuxième clic. Un chip choisi est rempli
  de couleur, sans la coche Vuetify.

**Alternative écartée** :
- Garder un tri « au hasard » de la liste complète : il ne répond pas à « quoi manger cette semaine ».
- Partager le tirage avec le foyer : il faudrait un modèle `kitchen`. On le fera si le tirage alimente le menu de la
  semaine.

**Réversible ?** Oui.

## 2026-10-21 — hors jalon — Accueil des recettes : réflexion, pas encore de refonte
**Contexte** : l'accueil est jugé fatigant (« plein de plats dans lesquels on se perd »).
**Choix** : analyse et recommandation dans `docs/fork/RECETTES-ACCUEIL.md` :
- la décision d'abord (le tirage) ;
- des étagères thématiques ;
- la liste complète en lignes compactes.

L'écran n'est pas refait avant validation par Alex : c'est un choix produit qui change le parcours P1 de SPEC.md.
**Alternative écartée** : refaire tout de suite en grille dense (piste A). Elle réduit le défilement, mais pas
l'effet « liste plate ».
**Réversible ?** Oui.

## 2026-10-21 — hors jalon — Doublons : variétés d'un nom composé
**Contexte** : « Pomme de terre », « Pomme de terre à chair ferme » et « Pomme de terre Yukon Gold » n'étaient pas
proposés comme doublons. La règle « mêmes mots + au plus 2 de plus » était coupée dès que le nom long contenait une
préposition. Le but était de séparer « Pomme » de « Pomme de terre », mais la coupure touchait aussi les variétés.
**Choix** : la règle s'applique quand le nom long commence par le nom composé entier (« Pomme de terre » + « à chair
ferme »). « Pomme » / « Pomme de terre », « Lait » / « Lait de coco » et « Poulet » / « Poulet au curry » restent
séparés. Cas limite assumé : « Pomme de terre douce » serait proposé, et « Pas un doublon » l'écarte une fois pour
toutes.
**Alternative écartée** : les traiter en famille plutôt qu'en doublons. Si Alex veut garder les variétés, il les
écarte et les range dans une famille « Pomme de terre ».
**Réversible ?** Oui.

## 2026-10-21 — hors jalon — Nettoyage des aliments : noms abîmés, « À ranger », doublons
**Contexte** : Alex a 439 aliments « sans famille ». Beaucoup sont des noms abîmés par d'anciens imports (« à café
coriandre en poudre », « à soupe d'huile », « d'eau + 30 ml »). « À ranger » n'offre pas d'issue pour un aliment qui ne
se range pas (« nouveaux »). Les doublons doivent pouvoir être fusionnés en masse, ou sous un troisième nom.
**Choix** :
- **Noms à corriger** : nouvel écran, `kitchen.french.clean_food_name` ; la carte de la page Aliments le signale.
  - Il retire les restes d'unité (« à soupe », « à café »), la quantité suivie d'une unité, « + 30 ml » et l'article.
  - Il garde les vrais noms : « 4 épices », « 7 Up », « 100% cacao », « Du Barry », et « en poudre ».
  - Fusion avec l'aliment existant (pluriel, accents et casse ignorés), sinon renommage. Quand plusieurs noms donnent
    le même nom, le plus utilisé est renommé et les autres y sont fusionnés, par identifiant.
  - L'ancien nom devient un alias. « Garder ce nom » est mémorisé dans `kitchen` (champ `KitchenFood.kept_name`,
    migration `kitchen 0002`) tant que le nom ne change pas.
- **Le parseur** lit aussi « c.s. », « c.c. » et « cuillerée(s) ». « + 30 ml » va dans la note, plus dans le nom.
- **À ranger** : « Renommer » (fusionne si le nom existe), « Jamais en courses », « Supprimer ».
  - Supprimer passe par `kitchen` (`foods/<id>/delete/`), qui refuse au moment de supprimer une famille ou un aliment
    utilisé dans une recette. Chez Tandoor, supprimer un aliment supprime ses lignes d'ingrédients et ses
    sous-aliments.
- **Doublons** : « Tout fusionner » (confirmation, paires telles qu'affichées) et « Autre nom… ». Ce dernier fusionne
  les deux aliments, puis renomme ou fusionne avec l'aliment de ce nom ; les deux anciens noms deviennent des alias.
- Une fusion ne s'annule pas (upstream) : chaque action de masse demande une confirmation qui le dit.

**Alternative écartée** :
- Corriger les noms sans écran de validation : risque sur les vrais noms.
- Supprimer par l'API upstream : elle efface des lignes de recettes.
- Pour « Garder ce nom », réutiliser `NotDuplicate` : détourné de son sens.

**Réversible ?** Oui. Le champ `kept_name` se retire avec `migrate kitchen 0001`.

## 2026-10-21 — hors jalon — « Vider la liste de courses »
**Contexte** : Alex demande une fonction pour vider la liste de courses.
**Choix** : deux entrées dans le menu « ⋮ » de la liste :
- « Retirer les articles du panier » (ce qui est coché) ;
- « Vider la liste » (tout).

Chacune demande une confirmation qui donne le nombre d'articles, puis peut être annulée : bandeau « Annuler », et le
bouton ↶ garde les deux actions. On ne supprime que ce que l'appareil affiche (listes sélectionnées). Les entrées sont
supprimées une à une par l'API upstream, sans changement backend ni dans `ShoppingStore`. Les actions sont grisées
hors ligne.
**Alternative écartée** : seulement « tout vider » (on perd ce qui reste à acheter quand on veut juste ranger le
panier) ; un endpoint de suppression groupée dans `kitchen/` (inutile pour une liste de quelques dizaines d'articles).
**Réversible ?** Oui.

## 2026-10-21 — M6 — Branche et libellé de la porte finale
**Contexte** : comme en M5, la session cloud impose la branche `claude/zen-ramanujan-cnfub4` (au lieu de
`fork/m6-livraison`), et la consigne demande `verify.sh --ui m1 --publish`.
**Choix** : même règle qu'en M5. Les captures de la PR sont publiées sous `m6`. La porte est aussi lancée avec le libellé
`m1`, mais ses captures ne sont pas commitées, pour ne pas écraser l'historique de M1.
**Alternative écartée** : renommer la branche (interdit par la session) ; republier `docs/fork/screens/m1`.
**Réversible ?** Oui.

## 2026-10-21 — M6 — Étiquette de l'image : `<release>-fork.<n>`
**Contexte** : le critère demande « version upstream + suffixe fork ».
**Choix** : `scripts/fork/image_tag.sh` donne `<dernière release Tandoor contenue>-fork.<commits depuis ce tag>`, par
exemple `2.6.15-fork.97`. Le numéro augmente à chaque fusion dans `main` et se calcule sans état ni secret. On publie
aussi `fork-latest` et `sha-<commit>`. Les tags de pré-version (`-beta`) sont ignorés.
**Alternative écartée** : un numéro de run GitHub (pas reproductible en local) ; une date (deux images le même jour) ;
`2.6.15-fork` seul (écrasé à chaque fusion, pas de retour à une image précise).
**Réversible ?** Oui.

## 2026-10-21 — M6 — Image : Dockerfile upstream inchangé, `amd64` seulement, nouveau workflow
**Contexte** : le workflow upstream `build-docker.yml` ne tourne que pour `TandoorRecipes` et pousse aussi sur Docker Hub.
**Choix** : un workflow du fork, `fork-image.yml`, construit le front puis le Dockerfile upstream tel quel. Il publie sur
GHCR sur `main` et à la demande, et construit sans publier sur les PR qui touchent l'image. Plateforme `linux/amd64`
seulement : l'`arm64` par émulation multiplie la durée de build (compilation Rust/C). Seul ajout côté upstream : deux
lignes dans `.dockerignore` (`.venv`, `.fork`), pour qu'un build local n'embarque pas l'environnement de dev.
**Alternative écartée** : modifier `build-docker.yml` (conflits à chaque synchro) ; un Dockerfile du fork.
**Réversible ?** Oui (ajouter `linux/arm64` dans `platforms` si le homelab est en ARM).

## 2026-10-21 — M6 — CI : `verify.sh` complet sans les contrôles UI
**Contexte** : critère « `verify.sh` complet sur chaque PR vers `main` ».
**Choix** : la CI lance `verify.sh` sans option, donc complet : règles, vue-tsc, tests node, build et pytest. Le job ajoute
le contrôle PostgreSQL (`pg_upgrade_check.sh`) contre un service Postgres 16. Les contrôles UI (`--ui`) restent dans les
sessions : ils demandent Chromium et des données de démo, et leurs captures sont relues par `ui-auditor`, pas par la CI.
**Alternative écartée** : `--ui ci` en CI (plus long, plus fragile, captures sans relecture).
**Réversible ?** Oui.

## 2026-10-21 — M6 — Retour arrière : retirer les tables du fork avant de remettre l'image upstream
**Contexte** : en M6, sur PostgreSQL, l'image upstream ne pouvait plus supprimer un aliment étendu par le fork
(`IntegrityError` sur `kitchen_kitchenfood_food_id`). Django gère les suppressions en cascade dans le code, pas dans la
base : un code qui ignore les tables `kitchen_*` ne les nettoie pas.
**Choix** : `DEPLOY.md` impose `migrate kitchen zero` avec l'image du fork avant de remettre l'image upstream (ou la
restauration de la sauvegarde). `pg_upgrade_check.sh` joue ce retour arrière en CI.
**Alternative écartée** : des clés étrangères `ON DELETE CASCADE` côté base (migration SQL spécifique, plus difficile à
maintenir) ; ne rien dire (piège découvert au premier nettoyage d'aliments).
**Réversible ?** Oui.

## 2026-10-21 — M5 — Branche et libellé de la porte finale
**Contexte** : le skill prévoit la branche `fork/m5-quotidien` et la porte `verify.sh --ui m5 --publish`. La session cloud
impose la branche `claude/clever-fermat-h1cce1`, et la consigne de la session demande `verify.sh --ui m1 --publish`.
**Choix** : travail et PR sur `claude/clever-fermat-h1cce1`. Les captures du jalon sont publiées sous `m5` (celles de la
PR) ; la porte est aussi lancée avec le libellé `m1` comme demandé, sans commiter ses captures, pour ne pas écraser
l'historique de M1.
**Alternative écartée** : renommer la branche (interdit par la session) ; republier `docs/fork/screens/m1`.
**Réversible ?** Oui.

## 2026-10-21 — M5 — Tests de la détection des durées : `node --test`, sans vitest
**Contexte** : la détection doit être testée par `verify.sh`, et `vue3` n'a pas de vitest.
**Choix** : les fonctions pures (`fork/timers/detect.ts`, `fork/timers/markup.ts`, `fork/share.ts`) n'importent rien
d'autre que des fichiers du même genre. Node 22 lit le TypeScript tel quel (suppression des types), donc
`node --test scripts/fork/tests/*.test.mjs` les teste sans dépendance. `verify.sh` lance cette étape, même en `--quick`.
28 phrases françaises réelles, dont les faux positifs « 4 personnes », « 180 °C », « farine T55 », « 2 œufs », « 2 cm ».
**Alternative écartée** : ajouter vitest à `vue3` (dépendance et configuration de plus) ; seulement un test de parcours
(lent, et il ne couvre pas les cas limites).
**Réversible ?** Oui.

## 2026-10-21 — M5 — Durées touchables : balisage du HTML de l'étape, `Instructions` intact
**Contexte** : le texte des étapes arrive en HTML et passe par le composant upstream `Instructions`, qui le compile
comme un gabarit Vue (pour les quantités qui suivent les portions).
**Choix** : `ForkStepText` balise les durées dans ce HTML **avant** `Instructions` (`<span role="button">`), en ne
touchant qu'au texte, jamais aux balises, aux liens ni aux quantités. Le texte est ré-échappé, accolades comprises : aucun
texte d'étape ne peut devenir une expression du gabarit. Un clic sur une durée lance un minuteur ; une plage ouvre une
feuille « Quelle durée ? » avec le bas, le milieu (arrondi à la minute au-delà de 2 min) et le haut. La zone tactile fait
44 px de haut grâce à un rembourrage vertical qui ne déplace pas les lignes.
**Alternative écartée** : modifier les nœuds du DOM après rendu (fragile face aux mises à jour de Vue) ; modifier
`Instructions` (fichier upstream).
**Réversible ?** Oui.

## 2026-10-21 — M5 — Minuteurs : où ils s'affichent, comment ils sonnent
**Contexte** : la barre des minuteurs doit suivre l'utilisateur et ne jamais masquer le contenu.
**Choix** :
- Barre collante en dernier élément de `v-main`, au-dessus de la barre du bas : elle reste visible en défilant et prend
  sa propre place en bas de page. En mode cuisine (plein écran), elle s'affiche au-dessus des boutons « Précédent /
  Suivant ». Au-delà de 3 minuteurs, la barre défile.
- Libellé « Étape 2 · Curry… » (l'étape d'abord, car le nom de la recette est souvent tronqué).
- Fin : trois bips (Web Audio, aucun fichier son), vibration, répétés toutes les 3 s pendant 60 s au plus ou jusqu'à
  l'arrêt ou +1 min. Notification système seulement si l'app est en arrière-plan et que la permission est accordée. La
  permission est demandée **une fois**, au premier minuteur lancé ; un refus ne change rien d'autre.
- Un minuteur échu pendant que l'app dormait ou était fermée (plus d'une minute de retard) s'affiche « Terminé ! »
  au retour, avec une seule alarme courte, sans répétition. Après un rechargement, le son a besoin d'un nouveau geste :
  le premier tap n'importe où le réactive pour les minuteurs en cours.
- Les minuteurs sont propres à l'appareil (`localStorage`), ce qui est cohérent avec SPEC : c'est un état de cuisine,
  pas une donnée partagée.

**Alternative écartée** : barre flottante fixe (masque le contenu) ; minuteurs partagés entre les deux comptes.
**Réversible ?** Oui.

## 2026-10-21 — M5 — Fin de cuisine et raccourcis de l'accueil
**Contexte** : « Terminé » doit créer un `CookLog` qui nourrit « récentes » et « pas faites depuis longtemps ».
**Choix** : seul « Terminé » mène à « Bon appétit » ; la croix « Quitter le mode cuisine » sort sans rien enregistrer
(on peut quitter sans avoir cuisiné). « Pas faites depuis longtemps » trie déjà sur `lastcooked` (le `CookLog`), vérifié
par un parcours. « Récentes » trie sur la dernière **consultation** (M2) : ouvrir la recette pour la cuisiner l'y fait
déjà figurer ; on ne touche pas au backend.
**Alternative écartée** : trier « récentes » sur le dernier `CookLog` (changement d'endpoint `kitchen/`, et une recette
juste consultée disparaîtrait du raccourci).
**Réversible ?** Oui.

## 2026-10-21 — M5 — Courses hors ligne : file et dernier état sur l'appareil, au plus près de `ShoppingStore`
**Contexte** : la file de coches de `ShoppingStore` était en mémoire ; l'app fermée hors ligne perdait les coches.
**Choix** : la logique vit dans `vue3/src/fork/shoppingOffline.ts`. `ShoppingStore` reçoit seulement des points
d'accroche commentés « fork » :
- la file est relue au démarrage et enregistrée à chaque passage dans `runSyncQueue` et après chaque envoi ;
- elle est rejouée à l'événement `online` et au lancement suivant ;
- les entrées reçues du serveur reprennent l'état des coches encore en attente, pour qu'une synchro ne les défasse pas ;
- le dernier état connu de la liste est enregistré après chaque chargement ou synchro. Il est affiché si le chargement
  échoue hors ligne. En pratique, le service worker upstream sert déjà la page et la dernière réponse de l'API quand
  la liste a été ouverte une fois en ligne ; l'instantané couvre le cas où ce cache n'a plus la réponse (50 entrées).

L'indicateur « N modifications en attente » s'affiche hors ligne ou après un échec d'envoi, pas pendant un envoi
normal (il clignoterait à chaque coche). Il remplace, dans la page du fork, l'alerte upstream équivalente.
L'écran allumé est un réglage de l'appareil (`fork_shopping_keep_screen_on`, actif par défaut), dans le menu ⋮ de la
liste, sans toucher au type `DeviceSettings` upstream.
**Alternative écartée** : étendre la file d'arrière-plan du service worker à l'endpoint groupé (fichier upstream, et
deux files concurrentes) ; un nouveau store des courses.
**Réversible ?** Oui.

## 2026-10-21 — M5 — Carte « Au menu »
**Contexte** : afficher sur le téléphone le repas prévu aujourd'hui, ou demain après 21 h.
**Choix** : carte compacte sous la recherche, seulement sur téléphone (le desktop garde le bandeau de la semaine) et
seulement s'il y a un repas ce jour-là. Jusqu'à 3 repas, triés par l'heure puis l'ordre du type de repas. Un tap ouvre
la recette **aux portions du plan** ; une entrée sans recette affiche son titre, sans lien. En cas d'erreur de l'API,
la carte ne s'affiche pas.
**Alternative écartée** : afficher la carte vide (« Rien de prévu ») ; ouvrir le plan de repas.
**Réversible ?** Oui.

## 2026-10-21 — audit kitshn — Nouveau jalon M5, livraison décalée en M6
**Contexte** : avant la livraison, Alex a demandé d'auditer [kitshn](https://github.com/kitshn-app/kitshn) (client natif
de Tandoor) et d'en tirer un jalon pour les fonctions utiles. Détail dans `docs/fork/AUDIT-KITSHN.md`.
**Choix** :
- Jalon « M5 — Cuisine et courses au quotidien » inséré **avant** la livraison, qui devient M6 (critères inchangés).
  Ainsi la première image déployée contient déjà ces fonctions, et les jalons restent dans l'ordre d'exécution.
- Retenu : minuteurs détectés dans les étapes, écran de fin de cuisine qui crée un `CookLog`, écran allumé et coches
  conservées hors ligne sur la liste de courses, carte « Au menu » sur l'accueil téléphone, correctif du partage vers
  l'app. Tout passe par l'API upstream : aucun changement backend prévu.
- Écarté : accueil dynamique par mots-clés (trop peu de recettes), répartition des ingrédients par étape (contraire à la
  liste unique), import IA et réseaux sociaux (SPEC), favoris par livre (livres hors périmètre), fonctions propres à
  une app native. Les favoris et l'accueil par moment de la journée sont gardés « en réserve ».
- La carte « Au menu » sur téléphone **complète** la décision M2 « bandeau du plan de repas : desktop seulement » : le
  bandeau de la semaine reste réservé au desktop ; le téléphone n'affiche qu'une carte compacte, et seulement s'il y a
  un repas prévu.
- Minuteurs : une PWA n'a pas accès au minuteur du système. Le fork tient donc lui-même les minuteurs, à partir de leur
  heure de fin. L'alarme est garantie en mode cuisine (écran allumé) ; ailleurs, l'app affiche « terminé » au retour, et
  la notification système reste un bonus.

**Alternative écartée** : ajouter ces fonctions à la fin, après la livraison (M6) ; ou garder la numérotation avec un
« M4b ».
**Réversible ?** Oui : le jalon n'est pas commencé ; on peut retirer une fonction ou réordonner les jalons.

## 2026-10-20 — M4 — Reconnaissance française : enveloppe du parseur upstream, selon la langue
**Contexte** : ne pas modifier `cookbook/helper/ingredient_parser.py`, mais servir l'import URL, le collage
multi-ligne de l'éditeur, le texte libre des courses et l'assistant du fork.
**Choix** : au démarrage de l'app, `kitchen/french.py` enveloppe `IngredientParser.parse`. Tous les appelants partagent
la même classe et en profitent. La lecture française s'applique quand la **langue active est le français** : réglage de
Django, donc l'en-tête `Accept-Language` du téléphone ou le choix de langue. Les autres langues gardent le parseur
upstream tel quel, ce qui garde verts les tests upstream du parseur. Les automatisations upstream s'appliquent :
`TRANSPOSE_WORDS` avant la lecture, puis `UNIT_ALIAS`, `FOOD_ALIAS` (et leurs variantes regex) sur le texte nettoyé.
`NEVER_UNIT` n'est pas appliqué en français : la table des unités du fork ne prend jamais un aliment pour une unité.
**Alternative écartée** : un prétraitement par heuristique sur toutes les lignes (casse les lignes anglaises comme
« 2 large eggs ») ; un patch du parseur upstream.
**Réversible ?** Oui.

## 2026-10-20 — M4 — Unités françaises dans le code, pas en `UNIT_ALIAS` semés
**Choix** : la table des unités (« c. à soupe », « càs », « cs », « cuillère à café », « pincée », « gousse »…) vit dans
`kitchen/french.py`, avec un nom canonique stocké (« c. à soupe », « g », « pincée »…). Cela évite d'écrire des
automatisations dans chaque espace, et le comportement est identique et testé partout. Les `UNIT_ALIAS` de
l'utilisateur restent appliqués après. « filet » n'est une unité que devant un liquide : « un filet d'huile », mais
« 2 filets de poulet » est un aliment.
**Réversible ?** Oui.

## 2026-10-20 — M4 — Pluriels et variantes : seulement vers un aliment existant équivalent
**Choix** : un nom reconnu prend l'aliment existant dont le nom normalisé est identique (pluriel, accents, mot de
préparation) : « oignons » → « Oignon ». Un nom avec des mots en plus reste un nouvel aliment (« oignons rouges ») ;
c'est la relecture d'import (M3) qui propose alors l'aliment proche. Fourchettes : « 2-3 » / « 2 à 3 » donnent la
première quantité, et la fourchette va en note (comme upstream).
**Réversible ?** Oui.

## 2026-10-20 — M4 — Assistant de saisie
**Choix** :
- page plein écran (`/recipe/new`, `/recipe/:id/edit`) en 4 écrans, boutons Précédent/Suivant en bas ;
- la reconnaissance en direct passe par `POST /api/kitchen/parse/`, qui **ne crée aucun aliment ni unité** (l'API
  upstream en crée à chaque appel). Les aliments sont créés à l'enregistrement, avec un rayon suggéré (M3) ;
- brouillon gardé sur l'appareil (localStorage, une clé par recette, écran courant compris). C'est le seul état local
  autorisé par SPEC.md. Il n'est écrit qu'après une vraie modification, et il est écarté s'il est plus ancien que la
  recette (modifiée entre-temps ailleurs). La photo n'est pas gardée dans le brouillon (fichier). Si l'envoi de la
  photo échoue, la recette reste enregistrée et un message le signale ;
- recette créée : tous les ingrédients dans la première étape, les étapes suivantes en texte ;
- recette existante : ses champs non édités (sous-recettes, fichiers, nutrition…) sont conservés tels quels. Une recette
  découpée par étape garde son découpage : les ingrédients s'affichent groupés par étape, et une étape supprimée donne
  ses ingrédients à la première ;
- un aliment modifié dans une ligne est envoyé **par son nom seul** : l'aliment existant est retrouvé (ou créé), jamais
  renommé pour toutes les recettes ;
- mots-clés : choisis parmi les existants ou tapés (créés à l'enregistrement).

« Modifier » (menu ⋮ d'une recette) ouvre l'assistant ; l'éditeur complet upstream reste accessible depuis son menu.
Le « + » de l'en-tête desktop garde l'éditeur upstream.
**Réversible ?** Oui.

## 2026-10-20 — M3 — Héritage du rayon géré par le fork, pas par `Space.food_inherit`
**Contexte** : les propositions M0 suggéraient d'activer `supermarket_category` dans `Space.food_inherit`. En pratique :
- ce réglage n'est appliqué à aucun aliment existant ou nouveau ;
- il faut passer par `Food.reset_inheritance`, qui efface les liens d'héritage de **tous** les espaces (bug upstream) ;
- un membre suit ensuite toujours sa famille et ne peut plus avoir un autre rayon.

**Choix** : le fork applique la règle « un aliment hérite du rayon de sa famille par défaut » dans `kitchen/services.py` :
- un aliment créé dans une famille prend son rayon ;
- un aliment déplacé dans une famille prend son rayon ;
- quand le rayon d'une famille change, ses membres le suivent, sauf ceux dont l'utilisateur a choisi le rayon.

Les champs upstream ne changent pas de sens.
**Alternative écartée** : `Space.food_inherit` + `reset_inheritance` (bug multi-espaces, pas d'exception possible).
**Réversible ?** Oui.

## 2026-10-20 — M3 — Rayon suggéré appliqué tout de suite, puis confirmé
**Contexte** : SPEC.md veut un rayon suggéré à chaque création d'aliment, confirmé en un tap, et une file « à ranger ».
**Choix** :
- à la création d'un aliment (signal `post_save`, donc import, saisie, liste de courses et API), le fork calcule une
  suggestion : rayon de la famille, puis dictionnaire français (`kitchen/aisles.py`, environ 300 aliments courants),
  puis rayon d'un aliment au nom proche ;
- la suggestion est **appliquée aussitôt** : la liste de courses est triée sans attendre ;
- l'aliment reste « non confirmé » et entre dans la file « à ranger », où un tap confirme ou corrige le rayon.

Un aliment créé avec un rayon (choisi par l'utilisateur, ou venu de l'open data) est déjà confirmé. Les espaces qui
n'ont jamais ouvert les écrans du fork ne sont pas touchés, ce qui garde intacts les tests upstream.
**Alternative écartée** : ne rien écrire avant confirmation. Les articles resteraient « sans rayon » jusqu'au tri,
contre le critère de succès n° 1.
**Réversible ?** Oui.

## 2026-10-20 — M3 — Ordre générique = un `Supermarket` upstream
**Choix** :
- un `Supermarket` « Ordre générique », créé au premier usage, ordonne les rayons
  (`SupermarketCategoryRelation.order`) ;
- les catégories existantes sont reprises quand leur nom correspond (« Crèmerie » tient lieu de « Frais »,
  « Fruits & légumes » de « Fruits et légumes ») ; les rayons manquants sont créés ; les autres catégories viennent
  après ;
- la liste de courses du fork suit cet ordre quand aucun magasin n'est choisi sur l'appareil. L'ordre se règle dans
  Aliments › Ordre des rayons (boutons monter/descendre, sans glisser-déposer).

**Alternative écartée** : une table d'ordre dans `kitchen/` (doublon de ce que fait upstream).
**Réversible ?** Oui.

## 2026-10-20 — M3 — Familles
**Contexte** : dans l'arbre upstream, rien ne distingue une famille vide d'un aliment isolé.
**Choix** : une famille est un aliment de premier niveau qui a des enfants, ou qui est marqué « famille »
(`KitchenFood.is_family`, interrupteur dans la feuille d'édition). Les aliments de premier niveau qui ne sont pas des
familles sont regroupés sous « Sans famille ». Les niveaux plus profonds s'affichent dans leur famille de premier niveau.
Les familles sont dépliées par défaut tant qu'il y a 80 aliments au plus.
**Réversible ?** Oui.

## 2026-10-20 — M3 — Règle de similarité des doublons
**Choix** : `kitchen/names.py`, une règle simple et explicable, testée sur des exemples français. Deux noms sont
probablement le même aliment dans trois cas :
- ils ne diffèrent que par les majuscules, les accents, le pluriel, une quantité ou un mot de préparation
  (« émincé », « frais », « bio ») ;
- les mots de l'un sont tous dans l'autre, avec au plus deux mots en plus (« oignon » / « oignon jaune ») ;
- leur orthographe est proche (≥ 88 %).

Les noms composés avec une préposition restent distincts : « pomme de terre », « lait de coco », « huile d'olive ».
Côté écran, on garde l'aliment le plus utilisé, puis le nom le plus court ; un bouton inverse le choix. « Pas un
doublon » mémorise la paire (`NotDuplicate`).
**Réversible ?** Oui.

## 2026-10-20 — M3 — Fusion upstream, alias côté client
**Choix** : la fusion appelle l'API upstream (`PUT /api/food/{id}/merge/{target}/`), puis crée l'alias `FOOD_ALIAS`
(nom fusionné → nom gardé), exactement comme `ModelMergeDialog`. Pour que la fusion générique upstream fonctionne
encore, la relation inverse de `KitchenFood` est masquée (`related_name='+'`) : sinon `MergeMixin` rencontre un
OneToOne qu'il ne sait pas traiter. Un test pytest le garantit.
**Réversible ?** Oui.

## 2026-10-20 — M3 — Relecture d'import : proposition d'aliment proche
**Choix** : un encart « Aliments inconnus » est inséré dans l'étape « Étapes » de l'assistant d'import upstream
(3 lignes dans `RecipeImportPage.vue`). Pour chaque aliment inconnu (nom, pluriel ou alias), il propose l'aliment
existant le plus proche :
- « Utiliser l'existant » renomme l'ingrédient et crée l'alias ;
- « Garder le nouveau » laisse créer l'aliment, qui recevra un rayon suggéré.

**Réversible ?** Oui.

## 2026-10-20 — M2 — Branches par jalon
**Contexte** : l'objectif de session demande une branche et une PR par jalon (M2, M3, M4), chaque branche partant de
la précédente tant que sa PR n'est pas fusionnée. En M0 et M1, la session imposait une branche `claude/...`.
**Choix** : `fork/m2-cuisine`, puis `fork/m3-aliments` (depuis M2) et `fork/m4-recettes` (depuis M3), comme le prévoit
CLAUDE.md. Le push de ces branches est accepté par le dépôt.
**Réversible ?** Oui.

## 2026-10-20 — M2 — Client des endpoints `kitchen/` écrit à la main
**Contexte** : le client TypeScript `vue3/src/openapi` est généré à partir du schéma OpenAPI. Le régénérer ajouterait
les endpoints du fork dans les fichiers générés upstream (conflits à chaque synchronisation).
**Choix** : un petit client à la main dans `vue3/src/fork/api.ts` (fetch + cookie CSRF), qui réutilise les
convertisseurs générés (`RecipeOverviewFromJSON`). Les endpoints du fork sont montés sous `/api/kitchen/`
(une ligne dans `recipes/urls.py`).
**Alternative écartée** : régénérer le client (diff dans des fichiers générés upstream).
**Réversible ?** Oui.

## 2026-10-20 — M2 — Recherche de l'accueil : `GET /api/kitchen/recipes/`
**Contexte** : P1 demande les ingrédients sous la main (classement), un temps total maximal et trois raccourcis.
La recherche upstream n'a ni filtre de temps total ni classement sans stock (`makenow` repose sur `onhand`).
**Choix** : un endpoint `kitchen/` qui applique d'abord `RecipeSearch` upstream (texte, mots-clés…), puis :
- `have` : recettes utilisant au moins un des aliments (familles comprises : « Légumes » couvre « Courgette »),
  classées par nombre d'aliments trouvés, puis par nombre total d'aliments (les recettes courtes d'abord) ;
- `max_time` : temps de préparation + cuisson/repos ≤ N minutes ;
- `sort=recent` : seulement les recettes **consultées** par l'utilisateur, la plus récente d'abord ;
- `sort=forgotten` : jamais cuisinées d'abord, puis la date de dernière cuisine la plus ancienne ;
- `sort=random`.

**Alternative écartée** : modifier `RecipeSearch` upstream ; filtrer côté client (pagination fausse).
**Réversible ?** Oui.

## 2026-10-20 — M2 — Filtres de l'accueil gardés en mémoire, pas dans l'URL
**Choix** : les filtres vivent dans un état du module (`vue3/src/fork/homeFilters.ts`). Revenir d'une recette retrouve
la même recherche ; un rechargement repart de zéro. Ils restent propres à l'appareil.
**Alternative écartée** : les mettre dans l'URL (il faudrait recharger les noms des aliments et mots-clés).
**Réversible ?** Oui.

## 2026-10-20 — M2 — Bandeau du plan de repas sur l'accueil : desktop seulement
**Contexte** : le réglage upstream `start_showMealPlan` (activé par défaut) affiche le plan de la semaine sur l'accueil.
SPEC.md : le plan de repas sert sur ordinateur.
**Choix** : le bandeau reste affiché sur desktop (≥ 960 px) si le réglage est actif, jamais sur téléphone, où l'accueil
commence par la recherche.
**Réversible ?** Oui.

## 2026-10-20 — M2 — Vue recette du fork
**Choix** :
- `ForkRecipeView` remplace la vue upstream, sauf en impression (mise en page upstream conservée).
- Les ingrédients sont en haut. Une recette dont plusieurs étapes ont des ingrédients les garde groupés par étape
  (en-têtes) ; sinon, une seule liste. Les étapes n'affichent que le texte, dont les quantités suivent les portions
  (gabarits upstream `{{ ingredients[0] }}`, `{{ scale(100) }}`).
- Les étapes avec sous-recette ou fichier gardent l'affichage upstream (`StepView`). Le menu ⋮ upstream (modifier,
  plan, partage…), les propriétés et l'activité (note, commentaire) sont conservés.
- Le Wake Lock est demandé sur la vue recette (comme upstream) et en mode cuisine ; un refus du navigateur est ignoré.

**Réversible ?** Oui.

## 2026-10-20 — M2 — Mode cuisine en page plein écran
**Choix** : une route `/recipe/:id/cook?servings=N` (méta `forkFullscreen`, qui masque l'en-tête, le tiroir et la barre
du bas). Le retour arrière du téléphone ramène à la recette. Un premier écran « Préparez les ingrédients » liste tout
quand la recette a plusieurs étapes. Ensuite, chaque étape rappelle ses propres ingrédients, sauf pour une liste unique
(déjà vue au premier écran). Balayage gauche/droite, deux boutons de 56 px, flèches du clavier sur desktop.
**Alternative écartée** : un dialogue plein écran (pas d'URL, retour arrière qui quitte la recette).
**Réversible ?** Oui.

## 2026-10-20 — M2 — Feuille « Ajouter aux courses »
**Choix** :
- tous les ingrédients sont cochés, sauf les aliments marqués « jamais en courses » (sel, eau…), décochés et signalés ;
- les ingrédients sans aliment (titres, texte libre) ne sont pas proposés ;
- les portions de la recette sont reprises, et ajustables dans la feuille ;
- les articles vont dans la liste du foyer (aucune liste nommée) ; les sous-recettes sont ajoutées comme upstream.

**Alternative écartée** : cocher aussi les « jamais en courses » (le critère dit « tous cochés », mais ce drapeau
existe justement pour ne pas les acheter).
**Réversible ?** Oui. À valider par Alex.

## 2026-10-20 — M2 — Liste de courses du fork
**Choix** :
- l'affichage est refait (`ForkShoppingList.vue`) sur le `ShoppingStore` upstream (chargement, synchro, annulation) ;
- groupement par rayon dans l'ordre du magasin choisi, sinon alphabétique (M3 apporte l'ordre générique). Le groupe
  « Sans rayon » vient **en dernier** : en magasin, le parcours compte d'abord ;
- un tap sur la ligne coche tous les articles de l'aliment ; le bouton ⋮ ouvre le dialogue upstream (quantités,
  report, rayon) ; « Vue détaillée » (menu ⋮ de la page) rend la vue upstream complète ;
- l'ajout rapide est en haut de la liste, au-dessus des rayons ;
- synchro : la boucle upstream (5 s par défaut), plus une synchro immédiate au retour sur l'écran.

**Réversible ?** Oui.

## 2026-10-20 — M2 — Correctif upstream dans la file de synchro des courses
**Contexte** : `ShoppingStore._replaySyncQueue` envoie toutes les requêtes en attente en parallèle. Cocher puis annuler
vite envoie « coché » et « décoché » pour le même article, dans un ordre d'arrivée non garanti : la base pouvait garder
l'article coché (constaté par les tests de parcours). `splice(index)` retirait aussi le mauvais élément de la file.
**Choix** : correctif minimal et commenté dans le store : la file est fusionnée (dernier état par article) avant envoi,
et les requêtes terminées sont retirées par identité. À proposer upstream.
**Réversible ?** Oui.

## 2026-10-20 — M2 — Tests de parcours dans `verify.sh --ui`
**Choix** : `scripts/fork/ui/flows.mjs` clique les parcours P1 à P4 sur un téléphone simulé (recherche, filtres,
portions, mode cuisine, balayage, ajout aux courses, coche, annulation, ajout rapide, synchro depuis un autre appareil,
message de fin) et remet les données en l'état. `verify.sh --ui` le lance après les captures.
**Réversible ?** Oui.

## 2026-10-20 — M2 — Photos du jeu de démo générées localement
**Choix** : `dev_seed.py` dessine une photo par recette avec Pillow (assiette vue de dessus), pour juger les grandes
cartes et la vue recette. Aucune image externe.
**Réversible ?** Oui.

## 2026-10-20 — M1 — Thème « système » sans migration
**Contexte** : DESIGN.md veut le thème du système par défaut, forçable en clair ou en sombre. Le champ upstream
`UserPreference.theme` n'a pas de valeur « système », et en ajouter une créerait une migration dans `cookbook/`.
**Choix** : le fork réinterprète des valeurs existantes. `TANDOOR` (défaut upstream) suit le système, `TANDOOR_DARK`
force le sombre, `FLATLY` (valeur héritée, ignorée par vue3 et par `theming_tags`) force le clair. Code :
`vue3/src/fork/theme.ts`.
**Alternative écartée** : un modèle de préférences dans `kitchen/` (plus lourd pour un simple choix), ou un réglage par
appareil (localStorage), qui ne suivrait pas l'utilisateur d'un appareil à l'autre.
**Réversible ?** Oui.

## 2026-10-20 — M1 — Primaire claire assombrie
**Contexte** : la primaire claire `#C2552D` donne 4,28:1 sur la surface et 3,89:1 sur `surface-variant`, sous 4,5:1.
**Choix** : `#AF4A26` (5,17:1 sur la surface, 4,7:1 sur `surface-variant`, 5,48:1 avec du texte blanc). Les autres
tokens passent tels quels.
**Alternative écartée** : garder `#C2552D` et ne pas l'employer pour du texte (règle impossible à tenir avec Vuetify).
**Réversible ?** Oui.

## 2026-10-20 — M1 — Icônes Font Awesome conservées
**Contexte** : DESIGN.md cite Material Design Icons « déjà dans Vuetify ». En réalité, le projet n'embarque que
Font Awesome (`defaultSet: 'fa'`), et MDI n'est pas installé.
**Choix** : garder Font Awesome (style plein), déjà utilisé partout. Ajouter `@mdi/font` serait une dépendance de plus,
et il faudrait de toute façon reprendre toutes les icônes.
**Alternative écartée** : migrer vers MDI outlined en M1.
**Réversible ?** Oui. À valider par Alex.

## 2026-10-20 — M1 — Couleur d'en-tête
**Contexte** : l'en-tête upstream prend `navBgColor` (utilisateur ou espace), sable `#ddbf86` par défaut, hors tokens.
**Choix** : la valeur par défaut upstream est remplacée par le token `surface` avec un contour fin. Une couleur choisie
explicitement par l'utilisateur ou l'espace est respectée.
**Alternative écartée** : ignorer totalement `navBgColor` (retire une fonction upstream).
**Réversible ?** Oui.

## 2026-10-20 — M1 — Entrées de la barre du bas et de « Plus »
**Contexte** : DESIGN.md fixe 4 entrées : Recettes, Courses, Ajouter, Plus.
**Choix** :
- « Recettes » mène à l'accueil actuel (StartPage), que M2 refera.
- « Plus » contient : plan de repas, aliments, recherche, livres, garde-manger, base de données, réglages, puis les
  entrées des plugins. La recherche y reste tant que l'accueil n'a pas de champ de recherche (M2). Les doublons arrivent
  en M3.
- Sur mobile, le « + » de l'en-tête est masqué (doublon d'« Ajouter »).

Le tiroir desktop gagne une entrée « Aliment » directe, et « Home » devient « Recettes » (traduit).
**Alternative écartée** : garder le plan de repas dans la barre du bas (5 entrées).
**Réversible ?** Oui.

## 2026-10-20 — M1 — Le 403 sur `/api/view-log/`
**Contexte** : AUDIT.md signalait un 403 à l'ouverture d'une recette, et sur le plan de repas en desktop.
**Constat** : ce n'est pas un bug de permission. Les captures n'injectaient qu'un cookie `sessionid`, sans cookie
`csrftoken`, et DRF refusait donc les POST (CSRF). Un vrai utilisateur reçoit ce cookie en se connectant.
**Choix** :
- l'outil de captures obtient le cookie CSRF comme un vrai navigateur, sur le formulaire de connexion ;
- côté app, l'appel `view-log` (secondaire) est rendu silencieux en cas d'échec, au plus près de l'appel
  (`RecipeViewPage.vue`).

**Alternative écartée** : exempter l'endpoint du CSRF (affaiblit la sécurité).
**Réversible ?** Oui.

## 2026-10-20 — M1 — Page de connexion stylée par une feuille du fork
**Contexte** : la connexion est un template Django Bootstrap, avec un thème upstream minifié.
**Choix** : une feuille `kitchen/static/kitchen/login.css` (tokens, sombre via `prefers-color-scheme`, champ d'étoiles
statique en sombre) est chargée par une ligne dans `cookbook/templates/account/login.html`. Les sélecteurs sont
renforcés pour passer devant les règles `!important` du thème.
**Alternative écartée** : réécrire le template (gros diff upstream), ou surcharger `base.html` pour toutes les pages
Django.
**Réversible ?** Oui.

## 2026-10-20 — M1 — Branche
**Contexte** : CLAUDE.md prévoit `fork/m1-<slug>`, mais la session cloud impose `claude/busy-heisenberg-yf2zw3`.
**Choix** : travailler sur la branche imposée, comme en M0.
**Réversible ?** Oui.

## 2026-10-20 — M0 — Propositions M0 validées
**Contexte** : la session M0 a proposé des ajustements pour M1 à M5 (fin de ROADMAP.md). Alex les a toutes acceptées.
**Choix** : les propositions qui changent un critère sont intégrées aux jalons :
- M1 : tiroir dès 960 px, barre du bas avec libellés et hauteur réservée, correction ou contournement des deux erreurs
  JS upstream, captures fiables (écran visible, reproductibles, publication 360 px) ;
- M2 : la synchro automatique existante suffit pour voir les modifications de l'autre membre du foyer ;
- M5 : CI GitHub Actions avec `verify.sh`.

Les notes d'implémentation (réutiliser `ShoppingStore`, un `Supermarket` unique pour l'ordre des rayons,
`Space.food_inherit`, `ModelMergeDialog`, endpoint `kitchen/` sans stock pour P1, prétraitement branché au collage et à
l'import) restent dans la section « Propositions M0 ».
**Alternative écartée** : laisser chaque session de jalon trancher au cas par cas.
**Réversible ?** Oui.

## 2026-10-20 — M0 — Branche de travail imposée par la session cloud
**Contexte** : la règle du fork demande une branche `fork/m0-<slug>`, mais la session cloud impose de pousser sur
`claude/gifted-cerf-5458vi` et interdit toute autre branche sans permission.
**Choix** : le jalon M0 est développé sur `claude/gifted-cerf-5458vi`, partie de `origin/main` ; la PR vise `main`.
**Alternative écartée** : créer `fork/m0-socle` (refusé par la configuration de la session).
**Réversible ?** Oui : la branche peut être renommée avant fusion.

## 2026-10-20 — M0 — Libellé des captures finales
**Contexte** : la consigne de la session demande `verify.sh --ui m1 --publish` comme porte finale, alors que le skill
prévoit le libellé du jalon (`m0`).
**Choix** : la porte finale est lancée avec le libellé `m1`, comme demandé. M0 ne change rien de visible : ces captures
sont identiques à `m0-baseline`, et M1 les écrasera.
**Alternative écartée** : libellé `m0`.
**Réversible ?** Oui.

## 2026-10-20 — M0 — pytest avec `recipes.test_settings`
**Contexte** : avec `DJANGO_SETTINGS_MODULE=recipes.settings` exporté, pytest-django ignore `pytest.ini`. Les
connecteurs externes démarrent alors un thread qui bloque la sortie de pytest, et une quinzaine de tests échouent.
**Choix** : `verify.sh` passe `--ds recipes.test_settings`, ce qui reprend la configuration de test d'upstream.
**Alternative écartée** : modifier `pytest.ini` ou `recipes/settings.py` (fichiers upstream).
**Réversible ?** Oui.

## 2026-10-20 — M0 — `kitchen/` déclarée dans INSTALLED_APPS plutôt qu'en plugin
**Contexte** : le système de plugins de Tandoor charge des apps depuis `recipes/plugins/`, un dossier ignoré par git
(voir AUDIT.md § 5).
**Choix** : `kitchen/` est une app à la racine, ajoutée explicitement dans `INSTALLED_APPS`. Cela coûte une ligne de
diff upstream. Elle est versionnée et testée avec le fork.
**Alternative écartée** : un plugin, qui serait hors du dépôt, sans tests du fork et sans possibilité de refondre l'UI.
**Réversible ?** Oui.

## 2026-10-20 — cadrage — M2 aligné sur les parcours de SPEC.md
**Contexte** : la première version de M2 ne couvrait pas tous les parcours retenus dans SPEC.md :
- P1, la recherche par ingrédients sous la main ;
- P3, l'envoi aux courses en décochant ce qu'on a ;
- le mode cuisine « une étape à la fois ».

**Choix** : M2 est réécrit autour des parcours P1 à P4, ce qu'Alex a validé dans la PR de cadrage. Le Wake Lock est
gardé (peu coûteux), même s'il n'a pas été cité comme prioritaire. « Ingrédients cochables » est retiré : ce n'était
pas un besoin exprimé.
**Alternative écartée** : garder M2 générique et traiter ces parcours plus tard.
**Réversible ?** Oui.

## 2026-10-20 — cadrage — Liste unique d'ingrédients
**Contexte** : Alex veut une seule liste d'ingrédients. Or Tandoor stocke les ingrédients par étape.
**Choix** : pour les recettes créées dans le fork, tous les ingrédients sont stockés dans la première étape, et les
étapes suivantes n'ont que du texte. La vue recette affiche alors une liste unique en haut. Les recettes importées
gardent leur découpage d'origine. Aucun changement de modèle.
**Alternative écartée** : fusionner tous les ingrédients à l'affichage pour toutes les recettes (refusé par Alex), ou
un champ dédié dans `kitchen/` (inutile).
**Réversible ?** Oui.

## 2026-10-20 — cadrage — Reconnaissance des ingrédients en français hors du parseur upstream
**Contexte** : le parseur `cookbook/helper/ingredient_parser.py` reconnaît mal les unités, articles et pluriels français.
**Choix** : ne pas modifier le parseur. Le fork ajoute deux choses :
- des alias d'unités, via les automatisations `UNIT_ALIAS` existantes, semées par `kitchen/` ;
- un prétraitement dans `kitchen/`, appelé avant le parseur.

Le jeu d'exemples en pytest fait foi.
**Alternative écartée** : patcher le parseur upstream (conflits de merge à chaque release). Si un cas ne peut être traité
qu'en amont, proposer un patch upstream plutôt que de diverger.
**Réversible ?** Oui.

## 2026-10-20 — kit — Bases du fork
**Contexte** : fork personnel destiné à rester synchronisable avec Tandoor.
**Choix** : base `master` (releases) ; aucune migration dans `cookbook/` ; extensions backend dans l'app `kitchen/` ;
dépendances Python via uv ; contrôles UI headless hors de `vue3/` (`scripts/fork/ui`).
**Alternative écartée** : suivre `develop` (instable, tests parfois non lançables).
**Réversible ?** Oui.
