"""
Average French supermarket prices of common foods, offered as "estimated" prices (M7), and usual weights of a piece.

Orders of magnitude for a mid-range supermarket in mainland France in 2025-2026, rounded: they are a starting point,
not a quote. Source and date are recorded in docs/fork/DECISIONS.md. Each line reads:

    name ; price in euros ; per (kg, l or piece) ; weight of a piece in grams (optional)

Names go through kitchen.names.normalize (case, accents, plurals and descriptors ignored), like the aisle dictionary.
"""
from decimal import Decimal

from kitchen.names import normalize

_TABLE = """
# vegetables
oignon ; 2.20 ; kg ; 150
oignon rouge ; 3.00 ; kg ; 150
echalote ; 6.00 ; kg ; 30
ail ; 9.00 ; kg ; 50
carotte ; 1.60 ; kg ; 100
pomme de terre ; 1.80 ; kg ; 150
patate douce ; 3.50 ; kg ; 300
courgette ; 2.80 ; kg ; 250
aubergine ; 3.50 ; kg ; 300
poivron ; 4.50 ; kg ; 180
tomate ; 3.50 ; kg ; 120
tomate cerise ; 7.00 ; kg ; 15
concombre ; 1.00 ; piece ; 400
salade ; 1.20 ; piece ; 300
laitue ; 1.20 ; piece ; 300
mache ; 12.00 ; kg
roquette ; 14.00 ; kg
brocoli ; 3.50 ; kg ; 400
chou fleur ; 2.50 ; piece ; 800
chou ; 2.00 ; kg ; 1000
poireau ; 2.80 ; kg ; 200
celeri ; 3.00 ; kg ; 500
champignon ; 6.00 ; kg ; 20
epinard ; 5.00 ; kg
haricot vert ; 6.00 ; kg
petit pois ; 4.00 ; kg
avocat ; 1.20 ; piece ; 200
betterave ; 3.00 ; kg ; 150
radis ; 1.50 ; piece ; 250
navet ; 2.50 ; kg ; 150
potiron ; 2.50 ; kg ; 2000
courge ; 2.50 ; kg ; 1500
butternut ; 2.50 ; kg ; 1200
fenouil ; 4.00 ; kg ; 250
endive ; 3.50 ; kg ; 120
mais ; 4.00 ; kg
gingembre ; 10.00 ; kg ; 50
persil ; 1.20 ; piece ; 50
coriandre ; 1.20 ; piece ; 50
basilic ; 1.80 ; piece ; 30
ciboulette ; 1.50 ; piece ; 20
menthe ; 1.50 ; piece ; 30
thym ; 1.50 ; piece ; 20
romarin ; 1.50 ; piece ; 20
# fruits
pomme ; 2.80 ; kg ; 180
poire ; 3.20 ; kg ; 180
banane ; 2.00 ; kg ; 120
orange ; 2.50 ; kg ; 200
citron ; 3.50 ; kg ; 120
citron vert ; 6.00 ; kg ; 70
clementine ; 3.50 ; kg ; 70
fraise ; 10.00 ; kg ; 15
framboise ; 20.00 ; kg
myrtille ; 18.00 ; kg
raisin ; 4.50 ; kg
kiwi ; 4.00 ; kg ; 80
ananas ; 2.50 ; piece ; 1500
mangue ; 1.80 ; piece ; 400
melon ; 2.50 ; piece ; 1000
peche ; 4.00 ; kg ; 150
abricot ; 5.00 ; kg ; 50
cerise ; 9.00 ; kg
prune ; 4.00 ; kg ; 40
pamplemousse ; 3.00 ; kg ; 350
# dairy, eggs
lait ; 1.10 ; l
beurre ; 11.00 ; kg
beurre de cacahuete ; 10.00 ; kg
creme fraiche ; 6.50 ; l
creme liquide ; 5.00 ; l
creme ; 6.00 ; l
yaourt ; 0.35 ; piece ; 125
yaourt grec ; 5.00 ; kg
fromage blanc ; 3.50 ; kg
oeuf ; 0.35 ; piece ; 60
emmental ; 10.00 ; kg
gruyere ; 15.00 ; kg
comte ; 18.00 ; kg
parmesan ; 25.00 ; kg
mozzarella ; 10.00 ; kg ; 125
feta ; 13.00 ; kg
chevre ; 15.00 ; kg
camembert ; 2.20 ; piece ; 250
roquefort ; 20.00 ; kg
mascarpone ; 9.00 ; kg
ricotta ; 10.00 ; kg
raclette ; 14.00 ; kg
reblochon ; 16.00 ; kg ; 450
cheddar ; 14.00 ; kg
fromage rape ; 10.00 ; kg
lait de coco ; 4.50 ; l
lait d amande ; 2.50 ; l
lait d avoine ; 2.20 ; l
# meat, fish
blanc de poulet ; 13.00 ; kg ; 150
poulet ; 7.00 ; kg ; 1500
cuisse de poulet ; 7.00 ; kg ; 250
dinde ; 13.00 ; kg
boeuf ; 18.00 ; kg
steak hache ; 13.00 ; kg ; 100
viande hachee ; 12.00 ; kg
porc ; 9.00 ; kg
cote de porc ; 9.00 ; kg ; 200
filet mignon ; 15.00 ; kg ; 500
lardon ; 11.00 ; kg
jambon ; 15.00 ; kg ; 40
bacon ; 18.00 ; kg ; 15
chorizo ; 16.00 ; kg
saucisse ; 10.00 ; kg ; 100
merguez ; 12.00 ; kg ; 60
agneau ; 20.00 ; kg
veau ; 22.00 ; kg
canard ; 20.00 ; kg
magret ; 25.00 ; kg ; 350
saumon ; 25.00 ; kg ; 125
saumon fume ; 35.00 ; kg
cabillaud ; 22.00 ; kg ; 125
colin ; 17.00 ; kg ; 125
thon ; 20.00 ; kg
thon en boite ; 14.00 ; kg ; 140
sardine en boite ; 10.00 ; kg ; 115
crevette ; 18.00 ; kg
moule ; 6.00 ; kg
surimi ; 9.00 ; kg ; 17
tofu ; 8.00 ; kg
# grocery
pate ; 2.00 ; kg
spaghetti ; 2.00 ; kg
tagliatelle ; 3.00 ; kg
lasagne ; 3.00 ; kg
riz ; 2.50 ; kg
riz basmati ; 4.00 ; kg
semoule ; 2.50 ; kg
couscous ; 2.50 ; kg
quinoa ; 8.00 ; kg
boulgour ; 4.00 ; kg
lentille ; 3.50 ; kg
pois chiche ; 3.00 ; kg
haricot rouge ; 3.00 ; kg
haricot blanc ; 3.00 ; kg
farine ; 1.20 ; kg
sucre ; 1.30 ; kg
sucre roux ; 2.50 ; kg
sucre glace ; 3.00 ; kg
sucre vanille ; 0.15 ; piece ; 8
sel ; 1.00 ; kg
poivre ; 30.00 ; kg
huile ; 3.50 ; l
huile d olive ; 12.00 ; l
huile de tournesol ; 3.00 ; l
vinaigre ; 2.00 ; l
vinaigre balsamique ; 8.00 ; l
moutarde ; 5.00 ; kg
mayonnaise ; 6.00 ; kg
ketchup ; 4.00 ; kg
sauce soja ; 8.00 ; l
concentre de tomate ; 6.00 ; kg
coulis de tomate ; 2.50 ; kg
sauce tomate ; 3.50 ; kg
# a stock cube makes 500 ml: "2 cubes" and "1 l de bouillon" cost the same
bouillon ; 0.30 ; l ; 500
fond de veau ; 25.00 ; kg
fond de volaille ; 25.00 ; kg
chocolat noir ; 12.00 ; kg
chocolat ; 12.00 ; kg
cacao ; 12.00 ; kg
levure chimique ; 0.20 ; piece ; 11
levure ; 0.40 ; piece ; 8
extrait de vanille ; 100.00 ; l
miel ; 12.00 ; kg
confiture ; 6.00 ; kg
pate a tartiner ; 7.00 ; kg
flocon d avoine ; 2.50 ; kg
pain ; 4.00 ; kg ; 250
baguette ; 1.10 ; piece ; 250
pain de mie ; 3.50 ; kg ; 25
pain burger ; 0.40 ; piece ; 75
tortilla ; 0.30 ; piece ; 40
pate feuilletee ; 1.50 ; piece ; 230
pate brisee ; 1.30 ; piece ; 230
pate a pizza ; 1.80 ; piece ; 260
noix ; 20.00 ; kg
amande ; 18.00 ; kg
noisette ; 18.00 ; kg
pignon ; 50.00 ; kg
cacahuete ; 8.00 ; kg
graine de sesame ; 10.00 ; kg
olive ; 12.00 ; kg
cornichon ; 8.00 ; kg
capre ; 20.00 ; kg
cumin ; 40.00 ; kg
curry ; 35.00 ; kg
paprika ; 35.00 ; kg
cannelle ; 40.00 ; kg
curcuma ; 35.00 ; kg
ras el hanout ; 40.00 ; kg
herbe de provence ; 40.00 ; kg
origan ; 50.00 ; kg
muscade ; 60.00 ; kg
piment d espelette ; 150.00 ; kg
noix de coco rape ; 10.00 ; kg
maizena ; 6.00 ; kg
chapelure ; 4.00 ; kg
creme de marron ; 9.00 ; kg
# drinks
eau ; 0.30 ; l
eau gazeuse ; 0.60 ; l
jus d orange ; 2.00 ; l
jus de pomme ; 1.80 ; l
jus de citron ; 8.00 ; l
vin blanc ; 6.00 ; l
vin rouge ; 6.00 ; l
biere ; 3.00 ; l
cafe ; 15.00 ; kg
the ; 30.00 ; kg
# frozen
petits pois surgeles ; 3.00 ; kg
epinard surgele ; 3.00 ; kg
legume surgele ; 3.00 ; kg
frite ; 2.50 ; kg
pizza surgelee ; 3.50 ; piece ; 400
"""

PERS = ('kg', 'l', 'piece')


def _build():
    table = {}
    for line in _TABLE.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split(';')]
        name, price, per = parts[0], Decimal(parts[1]), parts[2]
        assert per in PERS, line
        weight = Decimal(parts[3]) if len(parts) > 3 and parts[3] else None
        key = normalize(name)
        if key:
            table.setdefault(key, {'name': name, 'price': price, 'per': per, 'piece_weight': weight})
    return table


PRICES = _build()


def lookup(food_name):
    """Dictionary entry for a food name, or None: the whole name, then shorter runs of consecutive words, left to right
    ("gros oignon rouge" -> "oignon rouge", "tomates cerises bio" -> "tomate cerise")."""
    parts = normalize(food_name).split()
    for size in range(len(parts), 0, -1):
        for start in range(0, len(parts) - size + 1):
            entry = PRICES.get(' '.join(parts[start:start + size]))
            if entry:
                return entry
    return None
