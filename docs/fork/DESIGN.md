# Direction de design

État : **proposition à valider pendant l'entretien de cadrage**. Une fois validée, ce fichier fait référence pour
toutes les sessions et pour le subagent `ui-auditor`.

## Intention
Une application de cuisine calme et lisible, pensée pour une main sur un téléphone posé sur le plan de travail.
Le contenu (photos, ingrédients, étapes) prime sur l'interface. Moderne sans être à la mode : peu d'ombres,
surfaces nettes, hiérarchie portée par la typographie et l'espacement.

## Ambiance proposée
- Thème clair par défaut, chaleureux et neutre.
- Thème sombre « nuit étoilée » inspiré de l'astrophotographie : fonds bleu-noir profonds, accents froids,
  texte doux (pas de blanc pur). Un léger champ d'étoiles peut habiller les écrans vides et la connexion,
  jamais les écrans de cuisine ou de saisie.
- Mouvement : fondus entre les vues, légère parallaxe sur la photo d'en-tête d'une recette, une étoile filante
  discrète comme récompense ponctuelle (ex. liste de courses terminée). Tout mouvement est coupé avec `prefers-reduced-motion`.

## Tokens (valeurs de départ, à ajuster en M1)
| Token | Clair | Sombre |
|---|---|---|
| surface | #FAF8F5 | #0B1020 |
| surface-variant | #F1EDE6 | #141A2E |
| on-surface | #1F1D1A | #E6E8F0 |
| primary | #C2552D | #8FB3FF |
| secondary | #3E6B5A | #B9A6FF |
| error | #B3261E | #FF8A80 |

- Typographie : une seule famille sans empattement lisible (ex. Inter ou la police système), échelle 12/14/16/20/24/32, corps 16 px sur mobile.
- Espacements : grille de 4 px (4, 8, 12, 16, 24, 32). Marges latérales 16 px sur mobile.
- Rayons : 12 px cartes, 999 px puces, 16 px feuilles du bas. Élévation : 0 ou 1, contours fins plutôt qu'ombres.
- Icônes : Material Design Icons (déjà dans Vuetify), un seul style (outlined).

## Règles mobile
- Aucun défilement horizontal à 360 px. Zones tactiles ≥ 44 × 44 px, espacées de 8 px.
- Actions principales dans la moitié basse de l'écran (barre du bas, bouton flottant, feuilles du bas).
- Formulaires : un champ par ligne, clavier adapté (`inputmode`), pas de sélecteurs minuscules.
- États vides, de chargement (squelettes) et d'erreur prévus pour chaque liste.
- Contraste texte ≥ 4.5:1.

## Grille de relecture (utilisée par `ui-auditor`)
1. Une action principale évidente par écran.
2. Alignements et espacements sur la grille de 4 px.
3. Échelle typographique respectée, pas plus de 3 tailles par écran.
4. Couleurs issues des tokens uniquement.
5. Lisible à bout de bras (cuisine) : quantités et étapes en grand.
6. Rien de tronqué ou de chevauché à 360 px.
7. Thème sombre aussi soigné que le clair.
