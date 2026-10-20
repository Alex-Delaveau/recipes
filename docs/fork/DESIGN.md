# Direction de design

État : **validé lors de l'entretien de cadrage du 2026-10-20**. Ce fichier fait référence pour toutes les sessions et
pour le subagent `ui-auditor`.

## Intention
Une application de cuisine calme et lisible, pensée pour être utilisée d'une main, avec un téléphone posé sur le plan
de travail. Le contenu (photos, ingrédients, étapes) prime sur l'interface. Moderne sans être à la mode : peu d'ombres,
surfaces nettes, hiérarchie portée par la typographie et l'espacement.

## Ambiance
- **Thème par défaut : celui du système** (`prefers-color-scheme`). On peut le forcer en clair ou en sombre dans les réglages.
- Thème clair : chaleureux et neutre, fond crème, primaire terre cuite, secondaire vert sauge.
- Thème sombre « nuit étoilée », inspiré de l'astrophotographie :
  - fonds bleu-noir profonds, accents froids, texte doux (jamais de blanc pur) ;
  - un léger champ d'étoiles statique habille les écrans vides et la connexion, jamais les écrans de cuisine, de courses
    ou de saisie.
- **Mouvement : fondus entre les vues uniquement** (≤ 200 ms). Ni parallaxe, ni étoile filante, ni animation de
  récompense. Avec `prefers-reduced-motion`, le fondu est coupé.

## Tokens (valeurs de départ, ajustables en M1 si un contraste échoue)
| Token | Clair | Sombre |
|---|---|---|
| surface | #FAF8F5 | #0B1020 |
| surface-variant | #F1EDE6 | #141A2E |
| on-surface | #1F1D1A | #E6E8F0 |
| primary | #C2552D | #8FB3FF |
| secondary | #3E6B5A | #B9A6FF |
| error | #B3261E | #FF8A80 |

- Typographie :
  - **police du système** (`system-ui, -apple-system, Roboto, "Segoe UI", sans-serif`), sans police téléchargée ;
  - échelle 12/14/16/20/24/32 px, corps de texte à 16 px sur mobile ;
  - en mode cuisine, l'étape est à 24 px et les quantités à 20 px.
- Espacements : grille de 4 px (4, 8, 12, 16, 24, 32). Marges latérales de 16 px sur mobile.
- Rayons : 12 px pour les cartes, 999 px pour les puces, 16 px pour les feuilles du bas.
- Élévation : 0 ou 1, avec des contours fins plutôt que des ombres.
- Icônes : Material Design Icons (déjà dans Vuetify), un seul style (outlined).

## Navigation
- **Mobile : barre du bas à 4 entrées, chacune avec un libellé sous l'icône.**
  1. **Recettes** : accueil, recherche et filtres.
  2. **Courses** : la liste du foyer.
  3. **Ajouter** : ouvre une feuille du bas « Depuis un site (URL) » / « Saisir une recette ».
  4. **Plus** : plan de repas, aliments, doublons, livres, garde-manger, réglages.
- La barre du bas ne masque jamais le contenu : la page réserve sa hauteur.
- En-tête compact : titre de la page et une action contextuelle au plus.
- Desktop : tiroir latéral avec les mêmes entrées, plan de repas et aliments en accès direct.

## Règles mobile
- Aucun défilement horizontal à 360 px. Zones tactiles ≥ 44 × 44 px, espacées de 8 px.
- Actions principales dans la moitié basse de l'écran : barre du bas, bouton flottant, feuilles du bas.
- Listes en cartes ou en lignes, **jamais de tableau à colonnes** sur mobile.
- Formulaires :
  - un champ par ligne ;
  - clavier adapté (`inputmode`) ;
  - pas de sélecteurs minuscules ;
  - les longs formulaires sont découpés en écrans successifs (assistant), pas en onglets.
- États vides, de chargement (squelettes) et d'erreur prévus pour chaque liste.
- Contraste du texte ≥ 4.5:1 dans les deux thèmes.

## Mode cuisine
- Une étape par écran, en plein écran. On avance et on recule par balayage ou avec deux grands boutons en bas.
- Les quantités suivent les portions choisies. L'écran reste allumé (Wake Lock) tant que le mode est ouvert.
- Ni décor, ni étoiles, ni éléments secondaires.

## Grille de relecture (utilisée par `ui-auditor`)
1. Une action principale évidente par écran.
2. Alignements et espacements sur la grille de 4 px.
3. Échelle typographique respectée, pas plus de 3 tailles par écran.
4. Couleurs issues des tokens uniquement.
5. Lisible à bout de bras (cuisine) : quantités et étapes en grand.
6. Rien de tronqué ou de chevauché à 360 px.
7. Thème sombre aussi soigné que le clair.
