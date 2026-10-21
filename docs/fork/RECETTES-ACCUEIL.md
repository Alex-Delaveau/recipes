# Accueil des recettes : comprendre la fatigue, choisir une direction

Réflexion demandée par Alex le 2026-10-21. Il trouve la liste des recettes « fatigante à lire, pas très lisible », avec
le sentiment de se perdre dans « plein de plats ». Il hésite aussi sur une grille à la Jow, dont il a « un peu le même
sentiment ». Ce document cherche la cause avant de proposer un écran. **Rien n'est encore refait** : la direction est à
valider (fin du document).

## 1. Ce qu'on voit aujourd'hui

Captures `docs/fork/screens/aliments/start-*.jpg`, sur un téléphone de 390 px.

- **Une recette par écran, ou presque.**
  - Chaque carte prend toute la largeur : photo en 16/9 (≈ 220 px), titre, ligne d'infos, soit environ 360 px.
  - On voit donc 1,5 à 2 recettes par écran. Avec ~30 recettes, il faut défiler ~15 écrans pour tout voir, et on
    oublie le début avant d'arriver à la fin.
- **Toutes les recettes ont le même poids.**
  - Aucune n'est mise en avant, aucune n'est regroupée. Ce n'est pas trié selon une question que l'on se pose : il
    n'y a que l'ordre par défaut de la recherche.
  - L'œil n'a aucun point d'appui.
- **Les photos manquantes font des cartes identiques.**
  - Les imports gardent la photo, mais une recette saisie à la main n'en a pas : la carte est alors un grand
    rectangle gris.
  - Deux cartes grises côte à côte ne se distinguent que par le titre, en bas.
- **L'écran sert deux tâches différentes avec la même liste.**
  - « Je sais ce que je veux » : il faut retrouver vite. La recherche le fait déjà bien.
  - « Je ne sais pas quoi manger » : il faut des propositions. La liste n'aide pas : elle déroule tout.

## 2. Pourquoi c'est fatigant

1. **Trop de choix équivalents.**
   - Plus les options sont nombreuses et indifférenciées, plus décider coûte (loi de Hick, « paradoxe du choix »).
   - 30 plats au même niveau, c'est 30 comparaisons implicites.
   - La grille Jow a le même défaut : plus dense, mais toujours plate. D'où le « même sentiment » d'Alex.
2. **Rien à quoi se raccrocher.**
   - Sans groupes, la mémoire de travail doit tout retenir. Avec des groupes (« rapides », « pas faites depuis
     longtemps », « soupes »), on compare 3 ou 4 familles, puis quelques plats dans une seule famille.
3. **Une densité mal placée.**
   - Trop peu sur téléphone : une carte par écran oblige à défiler longtemps.
   - Trop sur la grille Jow : beaucoup d'éléments par carte (badges, notes, boutons).
   - Le bon compromis est de voir 4 à 6 recettes d'un coup, avec seulement le nom, la photo et la durée.
4. **La liste répond à « montre tout » alors que la vraie question est « quoi ce soir / cette semaine ? ».**
   - Jow ne gagne pas par sa grille. Il gagne parce qu'il **décide d'abord** : il propose un menu de N recettes, et
     on remplace celles qui ne plaisent pas.
   - C'est exactement le tirage demandé, livré en même temps que ce document.

## 3. Pistes étudiées

| Piste | Ce que c'est | Pour | Contre |
|---|---|---|---|
| A. Grille dense | 2 colonnes sur téléphone, photo carrée, titre + durée | 4-6 recettes visibles, simple à faire | toujours une liste plate : on se perd moins vite, mais on se perd |
| B. Liste compacte | une ligne par recette : vignette 56 px, nom, durée (comme le tirage) | très lisible, 8-9 par écran, pas gênée par l'absence de photo | moins appétissante ; peu adaptée pour « donner envie » |
| C. Étagères | 3-5 rangées thématiques qui défilent de côté (« Rapides », « Pas faites depuis longtemps », « Avec ce que j'ai », un ou deux mots-clés) | groupes = points d'appui ; chaque rangée répond à une question | une recette peut être dans plusieurs rangées ; demande des mots-clés un peu rangés |
| D. Décider d'abord | l'accueil ouvre sur le tirage (menu de la semaine) ; parcourir vient après | supprime la fatigue de choisir ; colle au besoin réel | ne remplace pas la recherche quand on sait ce qu'on veut |

## 4. Recommandation

Combiner **D + C**, et utiliser **B** pour la liste complète :

1. **En haut : la décision.**
   - Une carte « Cette semaine » : la liste tirée au sort (vignettes en ligne, « Remplacer » / « Retirer »), ou un
     bouton « Tirer 5 recettes » si elle est vide.
   - La carte « Au menu » du jour reste au-dessus.
2. **Ensuite : 3 ou 4 étagères** de 6 à 10 recettes, en cartes moyennes (≈ 150 px de large, photo carrée, nom sur
   2 lignes, durée). Chacune a un lien « Tout voir ». Rangées proposées, chacune masquée si elle est vide :
   - « Rapides (≤ 30 min) » ;
   - « Pas faites depuis longtemps » ;
   - « Avec ce que j'ai » (si des aliments sont choisis dans les filtres) ;
   - les 1 ou 2 mots-clés les plus utilisés (« Plats », « Desserts »…).
3. **Enfin : « Toutes les recettes »** en liste compacte (piste B), triée par nom, avec une lettre en intertitre
   (A, B, C…). C'est l'annuaire, pas la vitrine.
4. **Recherche et filtres inchangés** en haut. Dès qu'on tape ou qu'on filtre, les étagères disparaissent au profit
   des seuls résultats, en liste compacte.
5. **Recettes sans photo** : vignette de couleur avec l'initiale ou l'icône du mot-clé principal, au lieu d'un grand
   rectangle gris.

Sur ordinateur, même structure : les étagères tiennent sans défiler de côté, et la liste complète passe en 2 ou 3
colonnes.

Ce qu'on attend en échange :
- moins de défilement : 5 à 10 recettes visibles au premier écran, contre 1,5 aujourd'hui ;
- un choix en deux temps : une question, puis quelques plats ;
- « je ne sais pas quoi manger » réglé par le tirage plutôt que par la liste.

## 5. Ce qui est déjà livré (même PR)

- **Tirer au sort** (`/recipes/draw`, chip « Tirer au sort » de l'accueil) :
  - on choisit le nombre (1 à 14), on tire, puis on retire ou on remplace une recette à la fois ;
  - « Une de plus » ajoute une recette, « Nouveau tirage » refait tout, et chaque action peut être annulée ;
  - le tirage suit les filtres de l'accueil (aliments sous la main, temps, mots-clés) ;
  - la liste reste sur l'appareil.
- **Chips de l'accueil corrigés** :
  - « Au hasard » est remplacé par « Tirer au sort ». Il ne pouvait plus se désélectionner : un nouveau clic
    relançait un tirage ;
  - « Récentes » et « Pas faites depuis longtemps » se désélectionnent d'un deuxième clic ;
  - un chip choisi n'a plus qu'une icône : la coche ajoutée par Vuetify à côté de l'icône du chip est supprimée.

## 6. À valider par Alex

- La direction **D + C + B** (décision d'abord, étagères, annuaire compact), ou une autre piste du tableau.
- Les étagères à proposer : la liste ci-dessus est-elle la bonne ? Faut-il des mots-clés imposés (Plats, Desserts,
  Soupes…) ?
- Le tirage doit-il pouvoir alimenter directement le menu de la semaine (un jour par recette) et la liste de courses ?
  C'est l'étape suivante logique, comme chez Jow.
