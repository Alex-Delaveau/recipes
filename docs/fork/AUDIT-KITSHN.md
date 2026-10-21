# Audit de kitshn (2026-10-21)

[kitshn](https://github.com/kitshn-app/kitshn) est un client **natif** non officiel de Tandoor (Kotlin Multiplatform,
Compose, Material 3) pour Android, iOS et desktop. Il parle à l'API Tandoor sans rien changer côté serveur. Licence
GPL-3.0 : on reprend des **idées**, pas de code. Le fork est en Vue/Django, de toute façon rien ne se copie tel quel.

Version lue : `main` du 2026-09-17 (`3134818`). Sources : README, `web/docs/features/*.md`, code de `shared/` (écrans,
dépôts de données, chaînes de traduction).

## Ce que fait kitshn, et ce qu'en a déjà le fork

| Fonction kitshn | Ce qu'elle fait | Dans le fork aujourd'hui | Verdict |
|---|---|---|---|
| **Détection des minuteurs** (`TimerDetection.kt`) | Repère les durées dans le texte des étapes (« 10 min », « 1 h 30 », « 10-15 min », « 15 s à 45 min »). Un tap lance un minuteur ; une plage ouvre un choix de durée. | Rien. Le mode cuisine affiche seulement `step.time` dans une puce, non cliquable. | **Retenu** |
| **Écran « Terminé »** du mode cuisine (`RecipeDone.kt`) | À la fin : note en étoiles et commentaire facultatifs, enregistrés en `CookLog`. | Le bouton « Terminé » ramène à la recette **sans rien enregistrer**. Conséquence : le raccourci « pas faites depuis longtemps » et le tri « récentes » de l'accueil (fondés sur `lastcooked`) ne sont jamais nourris par le fork. SPEC P2.4 (« note et commentaire facultatifs ») n'est pas couvert. | **Retenu** |
| **Mode courses** (`ShoppingMode.kt`) | Plein écran, écran maintenu allumé, articles agrandis, cochés en bas. | Liste du fork déjà grande, groupée et cochés en bas. Écran **non** maintenu allumé. | **Retenu** (écran allumé) |
| **Synchro hors ligne des courses** (base Room, `ShoppingTransaction`, `DeltaSyncableRepo`) | Les coches faites sans réseau sont stockées et rejouées ; la liste s'affiche hors ligne. | `ShoppingStore` a une file de synchro, mais **en mémoire** : si l'app est fermée (ou rechargée) en magasin sans réseau, les coches sont perdues. La file du service worker ne couvre que `PATCH /api/shopping-list-entry/{id}`, alors que les coches passent par l'endpoint groupé. | **Retenu** (file persistante) |
| **Plan de repas mis en avant** (`HomeMealPlanPromotionSection.kt`) | L'accueil montre le repas prévu aujourd'hui (le soir : demain). | Bandeau de la semaine sur desktop seulement (décision M2). Rien sur téléphone. | **Retenu** (carte compacte) |
| **Partager vers l'app** (share intent) | Un lien partagé depuis le navigateur ouvre l'import. | Le manifeste upstream a déjà un `share_target` vers `/recipe/import`, mais `RecipeImportPage` envoie tout le champ `text` comme URL, et `text` écrase `url`. Un partage « Titre https://… » échoue. | **Retenu** (correctif) |
| Gabarits `{{ ingredients[0] }}`, `{{ scale() }}` | Quantités dans le texte des étapes. | Déjà rendus par le composant upstream `Instructions` (vue recette et mode cuisine). | Rien à faire |
| Accueil dynamique (sections selon l'heure et des mots-clés : petit-déj, déjeuner, Noël…) | Rangées de recettes tirées au sort selon l'heure. | Accueil P1 : recherche, filtres, « récentes / pas faites depuis longtemps / au hasard ». | Écarté : demande beaucoup de mots-clés et de recettes (moins de 30 aujourd'hui) ; listes de mots-clés allemandes/anglaises. À revoir quand la base aura grossi. |
| Outil de répartition des ingrédients par étape, « tri automatique des ingrédients » et « découper les étapes » à l'import | Rattache chaque ingrédient à une étape. | Le fork a choisi la **liste unique** (cadrage, M4). | Écarté : contraire à la décision. |
| Favoris (livre de recettes marqué `#KTSHNFAV`) | Bouton ❤️ dans la recette. | Livres hors périmètre (SPEC). | Écarté pour l'instant (voir « Idées en réserve »). |
| Import depuis TikTok/Instagram par IA, import IA | | | Écarté : SPEC exclut l'IA et les services externes. |
| Vidéos dans les étapes (fichier nommé « video ») | | | Écarté : astuce de nommage, usage marginal. |
| « Share wrapping » (`x.kitshn.app`), mTLS, multi-instance, rapports de plantage, Material You, couleur depuis une image | | | Écarté : propre à une app native ou contraire aux tokens de DESIGN.md. |
| Plan de repas complet sur téléphone, livres | | | Écarté : hors périmètre (SPEC). |
| Double tap pour cocher un article | Évite les coches accidentelles. | Annulation (bouton et snackbar) déjà présente. | Écarté : l'annulation suffit et le tap unique est une exigence de P4. |

## Détail des fonctions retenues

### 1. Minuteurs dans les étapes
- kitshn transforme chaque durée en lien `timer://secondes` (ou `timer-range://de/à`), puis délègue au minuteur du
  système (Android) ou à un raccourci (iOS). Une PWA n'a pas ce minuteur système : le fork doit **tenir lui-même les
  minuteurs** (heure de fin stockée, compte à rebours, son et vibration à la fin).
- Les définitions de kitshn n'existent qu'en anglais et en allemand. Il faut un jeu français : `min`, `minute(s)`,
  `mn`, `h`, `heure(s)`, `s`, `seconde(s)`, « et », « à », « 1 h 30 », « 1 heure et demie », « 20 à 25 minutes »,
  « 2-3 min ». Le texte est déjà rendu en HTML par `Instructions` : la détection se fait sur les nœuds texte du rendu,
  pas sur le Markdown.
- Limite d'une PWA : un onglet en arrière-plan ou un téléphone verrouillé peut être gelé par le navigateur. En mode
  cuisine, l'écran reste allumé (Wake Lock), donc l'alarme sonne. Ailleurs, on garantit seulement qu'au retour l'app
  affiche « terminé » (le temps est calculé depuis l'heure de fin, pas compté par un `setInterval`). Une notification
  système est tentée si l'utilisateur l'autorise, sans être promise.

### 2. Fin de cuisine → journal
- Upstream fournit tout : `POST /api/cook-log/` (`recipe`, `servings`, `rating`, `comment`). Aucun changement backend.
- L'écran « Bon appétit » remplace la sortie directe : étoiles et commentaire facultatifs, un bouton « Enregistrer »
  et un « Passer » qui enregistre quand même le passage en cuisine (sans note). C'est ce qui fait vivre « récentes » et
  « pas faites depuis longtemps ».

### 3. Courses en magasin
- Écran allumé sur la liste de courses (Wake Lock, comme le mode cuisine), réglable, relâché en quittant la page.
- File de coches **persistée** sur l'appareil (localStorage) et rejouée au retour du réseau ou au prochain lancement ;
  indicateur « N modifications en attente ». La file reste un tampon d'envoi : la vérité reste le serveur, ce qui est
  compatible avec la contrainte « rien ne repose sur un état local, sauf les brouillons ».
- La liste doit s'afficher hors ligne à partir du dernier état connu (le service worker met déjà `api/*` en cache, à
  vérifier pour l'endpoint des courses).

### 4. « Au menu » sur l'accueil
- Carte compacte en haut de l'accueil téléphone, **seulement s'il y a un repas prévu** : « Aujourd'hui » (ou « Demain »
  après 21 h). Un tap ouvre la recette. On planifie sur l'ordinateur et on cuisine depuis le téléphone : c'est le lien
  qui manque entre les deux. Elle complète la décision M2 (bandeau de la semaine sur desktop), sans la remettre en cause.

### 5. Partager un lien vers l'app
- Extraire la première URL `http(s)` de `url`, puis `text`, puis `title`, et lancer l'import sur elle seule. Correctif de
  quelques lignes dans `RecipeImportPage.vue` via un utilitaire du fork.

## Idées en réserve (pas dans le jalon)
- **Favoris** : un cœur dans la vue recette, stocké dans `kitchen/` (ou un mot-clé), avec un raccourci « favorites » sur
  l'accueil. À décider avec Alex : utile si la base dépasse quelques dizaines de recettes.
- **Accueil par moment de la journée** (petit-déj le matin, rapide tard le soir), une fois les mots-clés en place.
