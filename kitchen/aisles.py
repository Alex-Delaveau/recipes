"""
Generic French aisle order and a dictionary of common foods, used to suggest an aisle for new foods.

The order follows a typical walk through a French supermarket (SPEC.md): fruits and vegetables first,
household items last. Keys are stable identifiers, names are what the user sees (and can rename).
"""
from kitchen.names import normalize

# (key, displayed name, other names an existing category may already have)
GENERIC_AISLES = [
    ('fruits_legumes', 'Fruits et légumes', ['fruits & legumes', 'fruits legumes', 'primeur', 'legumes', 'fruits']),
    ('boulangerie', 'Boulangerie', ['pain', 'boulangerie patisserie']),
    ('frais', 'Frais', ['cremerie', 'produits laitiers', 'cremerie fromage', 'fromage', 'frais libre service', 'rayon frais']),
    ('boucherie', 'Boucherie et poisson', ['boucherie', 'poissonnerie', 'viande', 'boucherie poisson', 'viande poisson', 'charcuterie']),
    ('epicerie_salee', 'Épicerie salée', ['epicerie', 'conserves', 'pates riz', 'condiments']),
    ('epicerie_sucree', 'Épicerie sucrée', ['petit dejeuner', 'sucre', 'patisserie']),
    ('boissons', 'Boissons', ['boisson', 'cave', 'vins']),
    ('surgeles', 'Surgelés', ['surgele', 'congele']),
    ('hygiene_maison', 'Hygiène et maison', ['hygiene', 'entretien', 'maison', 'droguerie', 'hygiene beaute']),
]

GENERIC_SUPERMARKET_NAME = 'Ordre générique'

_FOODS = {
    'fruits_legumes': """
        abricot ail ananas artichaut asperge aubergine avocat banane basilic betterave blette brocoli carotte
        celeri cerise champignon chou chou fleur ciboulette citron citron vert clementine coriandre cornichon courge
        courgette concombre echalote endive epinard estragon fenouil figue fraise framboise gingembre grenade groseille
        haricot vert kiwi laitue mache mandarine mangue melon menthe mirabelle myrtille navet nectarine oignon orange
        pamplemousse panais pasteque patate douce peche persil petit pois poire poireau poivron pomme pomme de terre
        potiron prune radis raisin roquette romarin salade shiitake thym tomate tomate cerise topinambour cresson
        citronnelle aneth sauge laurier piment salade verte potimarron butternut feve
    """,
    'boulangerie': """
        pain baguette pain de mie brioche croissant pain complet pain burger pain pita tortilla wrap biscotte
    """,
    'frais': """
        beurre creme creme fraiche creme liquide lait yaourt fromage blanc fromage parmesan mozzarella comte emmental
        gruyere feta chevre ricotta mascarpone camembert roquefort reblochon raclette oeuf pate feuilletee pate brisee
        pate sablee pate a pizza lardon jambon chorizo saucisse knacki tofu houmous gnocchi skyr faisselle burrata
        pecorino cheddar
    """,
    'boucherie': """
        poulet blanc de poulet cuisse de poulet dinde boeuf steak hache viande hachee porc filet mignon agneau veau
        canard magret saumon cabillaud thon crevette moule colin merlu truite sardine maquereau dorade bar lieu
        saucisse de toulouse roti cote de porc escalope
    """,
    'epicerie_salee': """
        pate riz riz basmati semoule couscous quinoa boulgour lentille pois chiche haricot rouge haricot blanc farine
        huile huile d olive huile de tournesol vinaigre vinaigre balsamique moutarde mayonnaise ketchup sel poivre
        curry cumin paprika curcuma cannelle muscade herbe de provence bouillon cube concentre de tomate coulis de tomate
        sauce soja lait de coco tomate pelee olive capre thon en boite sardine en boite mais nouille vermicelle
        chapelure fecule maizena levure sauce tomate pesto noix de coco rape cacahuete amande noisette noix pignon
        graine de sesame sesame tahini harissa ras el hanout gingembre en poudre piment d espelette bouillon
    """,
    'epicerie_sucree': """
        sucre sucre glace sucre roux cassonade miel confiture chocolat chocolat noir chocolat au lait cacao
        cereale muesli flocon d avoine biscuit levure chimique sucre vanille extrait de vanille vanille sirop
        compote pate a tartiner raisin sec abricot sec datte pruneau creme de marron caramel
    """,
    'boissons': """
        eau eau gazeuse jus d orange jus de pomme jus vin vin blanc vin rouge biere cidre cafe the tisane soda
        limonade sirop de menthe lait vegetal lait d amande lait d avoine
    """,
    'surgeles': """
        glace sorbet petits pois surgeles epinard surgele frite poelee surgelee legume surgele pizza surgelee
    """,
    'hygiene_maison': """
        papier toilette essuie tout sopalin lessive liquide vaisselle eponge sac poubelle savon shampoing gel douche
        dentifrice brosse a dent mouchoir coton film alimentaire papier aluminium papier cuisson
    """,
}


# multi-word names are listed explicitly; single words are split on whitespace
_MULTI = [
    'chou fleur', 'citron vert', 'haricot vert', 'patate douce', 'petit pois', 'pomme de terre', 'tomate cerise',
    'salade verte', 'pain de mie', 'pain complet', 'pain burger', 'pain pita', 'creme fraiche', 'creme liquide',
    'fromage blanc', 'pate feuilletee', 'pate brisee', 'pate sablee', 'pate a pizza', 'blanc de poulet',
    'cuisse de poulet', 'steak hache', 'viande hachee', 'filet mignon', 'saucisse de toulouse', 'cote de porc',
    'riz basmati', 'pois chiche', 'haricot rouge', 'haricot blanc', 'huile d olive', 'huile de tournesol',
    'vinaigre balsamique', 'herbe de provence', 'bouillon cube', 'concentre de tomate', 'coulis de tomate',
    'sauce soja', 'lait de coco', 'tomate pelee', 'thon en boite', 'sardine en boite', 'sauce tomate',
    'noix de coco rape', 'graine de sesame', 'ras el hanout', 'gingembre en poudre', 'piment d espelette',
    'sucre glace', 'sucre roux', 'chocolat noir', 'chocolat au lait', 'flocon d avoine', 'levure chimique',
    'sucre vanille', 'extrait de vanille', 'pate a tartiner', 'raisin sec', 'abricot sec', 'creme de marron',
    'eau gazeuse', 'jus d orange', 'jus de pomme', 'vin blanc', 'vin rouge', 'sirop de menthe', 'lait vegetal',
    'lait d amande', 'lait d avoine', 'petits pois surgeles', 'epinard surgele', 'poelee surgelee', 'legume surgele',
    'pizza surgelee', 'papier toilette', 'essuie tout', 'liquide vaisselle', 'sac poubelle', 'gel douche',
    'brosse a dent', 'film alimentaire', 'papier aluminium', 'papier cuisson',
]


def _build():
    table = {}
    multi_by_aisle = {}
    for aisle, blob in _FOODS.items():
        text = ' ' + ' '.join(blob.split()) + ' '
        for m in sorted(_MULTI, key=len, reverse=True):
            if f' {m} ' in text:
                multi_by_aisle.setdefault(aisle, []).append(m)
                text = text.replace(f' {m} ', ' ')
        for name in multi_by_aisle.get(aisle, []) + text.split():
            key = normalize(name)
            if key:
                table.setdefault(key, aisle)  # first aisle wins for ambiguous names
    return table


FOOD_AISLES = _build()


def suggest_aisle_key(food_name):
    """Aisle key from the dictionary for a food name, or None. Tries the whole name, then without the last words
    ("tomate cerise bio" -> "tomate cerise" -> "tomate"), then the first word alone."""
    key = normalize(food_name)
    if not key:
        return None
    parts = key.split()
    for n in range(len(parts), 0, -1):
        candidate = ' '.join(parts[:n])
        if candidate in FOOD_AISLES:
            return FOOD_AISLES[candidate]
    return None


def match_generic_key(category_name):
    """Generic aisle key an existing category name corresponds to ("Crèmerie" -> "frais"), or None."""
    name = normalize(category_name)
    for key, display, others in GENERIC_AISLES:
        if name == normalize(display) or name in {normalize(o) for o in others}:
            return key
    return None
