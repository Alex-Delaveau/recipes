"""
Price estimate of recipes and shopping lists (M7).

The price of a food is its upstream "Price" property: `property_amount` euros for `properties_food_amount` of
`properties_food_unit` (a property type of category PRICE, created by `price_type`). The fork adds where the price
comes from (estimated from the dictionary or confirmed), an optional package bought whole and the weight of a piece.

Every quantity is brought back to grams, millilitres or pieces:
- upstream base units and the usual French unit names ("g", "cl", "c. à soupe") without any setup;
- otherwise the space's own unit conversions (upstream `UnitConversionHelper`);
- pieces <-> grams through the weight of a piece, grams <-> millilitres at a density of 1 (an estimate, not a recipe).
An amount that cannot be brought back is counted as "not convertible", a food without a price as "no price": both are
reported, never hidden.
"""
import math
from collections import OrderedDict
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django_scopes import scopes_disabled

from cookbook.helper.unit_conversion_helper import CONVERSION_TABLE, UnitConversionHelper
from cookbook.models import Food, FoodProperty, Ingredient, Property, PropertyType, ShoppingListEntry, Unit
from kitchen import price_dictionary
from kitchen.models import KitchenFood
from kitchen.names import strip_accents

G, ML, PIECE = KitchenFood.KIND_WEIGHT, KitchenFood.KIND_VOLUME, KitchenFood.KIND_PIECE
PRICE_TYPE_NAMES = ('Prix', 'Prix (estimation)', 'Prix des courses')

# price units offered to the user: (quantity, kind) they stand for
PERS = {'kg': (Decimal(1000), G), 'l': (Decimal(1000), ML), 'piece': (Decimal(1), PIECE)}
PER_OF_KIND = {G: 'kg', ML: 'l', PIECE: 'piece'}

# smoothing of the adjustments after shopping: a price stands for at most this many observations
MAX_WEIGHT = 4
# one receipt never moves estimated prices beyond these factors (promotion, forgotten item, typing error)
MIN_FACTOR, MAX_FACTOR = Decimal('0.33'), Decimal(3)


def _unit_key(name):
    text = strip_accents((name or '').lower()).replace('.', ' ').replace("'", ' ')
    words = [w[:-1] if len(w) > 3 and w.endswith('s') else w for w in text.split()]
    return ' '.join(w for w in words if w not in ('de', 'd', 'a'))


def _units(*pairs):
    table = {}
    for names, amount, kind in pairs:
        for n in names.split('|'):
            table[_unit_key(n)] = (Decimal(str(amount)), kind)
    return table


# usual unit names, so that a fresh space needs no setup
UNIT_NAMES = _units(
    ('g|gr|gramme|grammes', 1, G), ('kg|kilo|kilos|kilogramme|kilogrammes', 1000, G), ('mg|milligramme', '0.001', G),
    ('ml|millilitre', 1, ML), ('cl|centilitre', 10, ML), ('dl|decilitre', 100, ML), ('l|litre|litres', 1000, ML),
    ('c. à soupe|cuillère à soupe|cuillères à soupe|cs|cas|càs|c à s|tbsp|tablespoon', 15, ML),
    ('c. à café|cuillère à café|cuillères à café|cc|cac|càc|c à c|tsp|teaspoon', 5, ML),
    ('pincée|pincées|pinch', '0.5', G), ('gousse|gousses', 5, G), ('verre|verres', 200, ML), ('tasse|cup', 240, ML),
    ('pièce|pièces|piece|pieces|unité|unités|u|pc|pcs|pce', 1, PIECE),
)
_BASE = {**{k: (Decimal(1000) / Decimal(str(v)), G) for k, v in CONVERSION_TABLE['weight'].items()},
         **{k: (Decimal(1000) / Decimal(str(v)), ML) for k, v in CONVERSION_TABLE['volume'].items()}}


def _direct(unit):
    """(grams / millilitres / pieces per 1 of this unit, kind) without any conversion table, or None."""
    if unit is None:
        return Decimal(1), PIECE
    if unit.base_unit and unit.base_unit in _BASE:
        return _BASE[unit.base_unit]
    return UNIT_NAMES.get(_unit_key(unit.name))


def to_base(amount, unit, food=None, space=None):
    """(quantity, kind) of an amount in grams, millilitres or pieces, or None when it cannot be brought back."""
    amount = Decimal(amount or 0)
    direct = _direct(unit)
    if direct:
        return amount * direct[0], direct[1]
    if space is None:
        return None
    # the space's own conversions ("1 tranche = 30 g", "1 boîte = 400 g" for this food)
    for c in UnitConversionHelper(space).get_conversions(Ingredient(amount=amount, unit=unit, food=food, space=space))[1:]:
        found = _direct(c.unit)
        if found and found[1] != PIECE:
            return Decimal(c.amount) * found[0], found[1]
    return None


def convert(quantity, kind, target, piece_weight=None):
    """Quantity from one kind to another (density 1 between grams and millilitres), or None."""
    if kind == target:
        return quantity
    mass = {G, ML}
    if kind in mass and target in mass:
        return quantity
    if kind == PIECE and target in mass:
        return quantity * piece_weight if piece_weight else None
    if kind in mass and target == PIECE:
        return quantity / piece_weight if piece_weight else None
    return None


# ---------------------------------------------------------------- the price of a food

def price_type(space):
    """The space's price property type: the first one of category PRICE, created ("Prix", €) when there is none."""
    with scopes_disabled():
        pt = PropertyType.objects.filter(space=space, category=PropertyType.PRICE).order_by('order', 'id').first()
        if pt is not None:
            return pt
        # the name is unique in a space: a "Prix" of another category (made by hand) keeps its name, ours takes another
        taken = set(PropertyType.objects.filter(space=space, name__in=PRICE_TYPE_NAMES).values_list('name', flat=True))
        name = next((n for n in PRICE_TYPE_NAMES if n not in taken), None)
        if name is None:
            raise PriceError('price_type')
        try:
            with transaction.atomic():
                return PropertyType.objects.create(space=space, name=name, unit='€', category=PropertyType.PRICE,
                                                   description='Prix moyen, estimé ou confirmé (fork).')
        except IntegrityError:
            # created by a concurrent request
            pt = PropertyType.objects.filter(space=space, category=PropertyType.PRICE).order_by('order', 'id').first()
            if pt is None:
                raise
            return pt


class PriceBook:
    """Prices, fork states and conversions of a set of foods, loaded once for a recipe or a shopping list."""

    def __init__(self, space, foods):
        self.space = space
        self.type = price_type(space)
        foods = [f for f in foods if f is not None]
        self.foods = {f.id: f for f in foods}
        self.states = {s.food_id: s for s in KitchenFood.objects.filter(food_id__in=self.foods)}
        self.amounts = {}
        for fp in FoodProperty.objects.filter(food_id__in=self.foods, property__property_type=self.type).select_related('property'):
            if fp.property.property_amount is not None:
                self.amounts[fp.food_id] = Decimal(fp.property.property_amount)
        self._prices = {}

    def state(self, food):
        return self.states.get(food.id)

    def piece_weight(self, food):
        state = self.state(food)
        if state and state.piece_weight:
            return Decimal(state.piece_weight)
        entry = price_dictionary.lookup(food.name)
        return entry['piece_weight'] if entry else None

    def source(self, food):
        """Where the price comes from. A price set outside the fork, or changed there since the fork wrote it (upstream
        property editor), is the user's: confirmed."""
        state = self.state(food)
        if not state or state.price_source != KitchenFood.PRICE_ESTIMATED:
            return KitchenFood.PRICE_CONFIRMED
        amount = self.amounts.get(food.id)
        if state.price_value is None or amount is None or abs(Decimal(state.price_value) - amount) > Decimal('0.00005'):
            return KitchenFood.PRICE_CONFIRMED
        return KitchenFood.PRICE_ESTIMATED

    def price(self, food):
        """(euros per gram / millilitre / piece, kind) of a food, or None (no price, or a reference that cannot be read)."""
        if food.id not in self._prices:
            self._prices[food.id] = self._price(food)
        return self._prices[food.id]

    def _price(self, food):
        amount = self.amounts.get(food.id)
        if amount is None or not food.properties_food_unit_id or not food.properties_food_amount:
            return None
        ref = to_base(food.properties_food_amount, food.properties_food_unit, food, self.space)
        if not ref or ref[0] <= 0:
            return None
        return amount / ref[0], ref[1]

    def cost(self, food, quantity, kind):
        """Cost of a quantity of a food (proportional), or (None, reason)."""
        price = self.price(food)
        if price is None:
            return None, 'no_price'
        q = convert(quantity, kind, price[1], self.piece_weight(food))
        if q is None:
            return None, 'no_conversion'
        return q * price[0], None

    def display(self, food):
        """Price as the user reads it: {price, per, source}, or None."""
        price = self.price(food)
        if price is None:
            return None
        per = PER_OF_KIND[price[1]]
        return {'price': _round(price[0] * PERS[per][0], 4), 'per': per, 'source': self.source(food)}


def _round(value, places=2):
    return float(round(Decimal(value), places))


# ---------------------------------------------------------------- estimates

def _missing(items):
    """Foods without a price or with an amount that cannot be converted, once each."""
    seen = OrderedDict()
    for food, reason in items:
        seen.setdefault(food.id, {'id': food.id, 'name': food.name, 'reason': reason})
    return list(seen.values())


def estimate_recipe(recipe, book=None):
    """Cost of a recipe for its own servings: {total, per_serving, servings, missing}."""
    ingredients = list(Ingredient.objects.filter(step__recipe=recipe, is_header=False, food__isnull=False)
                       .select_related('food', 'food__properties_food_unit', 'unit'))
    book = book or PriceBook(recipe.space, [i.food for i in ingredients])
    total, missing = Decimal(0), []
    for i in ingredients:
        # salt, water, pantry staples: not bought for the recipe; an ingredient without amount costs nothing
        if i.food.ignore_shopping or i.no_amount or not i.amount:
            continue
        base = to_base(i.amount, i.unit, i.food, recipe.space)
        if base is None:
            missing.append((i.food, 'no_conversion'))
            continue
        cost, reason = book.cost(i.food, *base)
        if cost is None:
            missing.append((i.food, reason))
        else:
            total += cost
    servings = recipe.servings or 1
    return {'id': recipe.id, 'total': _round(total), 'servings': servings, 'per_serving': _round(total / servings),
            'missing': _missing(missing)}


def estimate_recipes(space, requests):
    """[(recipe, servings or None)] -> {total, recipes: [...], missing}, each recipe scaled to the servings asked."""
    foods = Food.objects.filter(ingredient__step__recipe__in=[r for r, _s in requests]).select_related('properties_food_unit').distinct()
    book = PriceBook(space, list(foods))
    results, total, missing = [], Decimal(0), OrderedDict()
    for recipe, servings in requests:
        r = estimate_recipe(recipe, book)
        if servings:
            factor = Decimal(str(servings)) / Decimal(str(r['servings']))
            r['total'] = _round(Decimal(str(r['total'])) * factor)
            r['servings'] = servings
        total += Decimal(str(r['total']))
        for m in r['missing']:
            missing.setdefault(m['id'], m)
        results.append(r)
    return {'total': _round(total), 'recipes': results, 'missing': list(missing.values())}


def _group_cost(book, food, entries):
    """Cost of what a set of shopping entries of one food asks for: whole packages when the food has one."""
    space = book.space
    quantities = []
    for e in entries:
        if not e.amount or Decimal(e.amount) <= 0:
            continue
        base = to_base(e.amount, e.unit, food, space)
        if base is None:
            return {'cost': None, 'reason': 'no_conversion'}
        quantities.append(base)
    if not quantities:
        # "some salt": what it cost is unknown, and it was paid for
        return {'cost': None, 'reason': 'no_conversion'}
    state = book.state(food)
    weight = book.piece_weight(food)
    price = book.price(food)
    if state and state.package_amount and state.package_kind and (state.package_price or price):
        needed = [convert(q, k, state.package_kind, weight) for q, k in quantities]
        if all(n is not None for n in needed):
            packages = max(1, math.ceil(sum(needed) / Decimal(state.package_amount) - Decimal('0.0001')))
            if state.package_price:
                return {'cost': packages * Decimal(state.package_price), 'reason': None, 'packages': packages, 'package_price': True}
            cost, reason = book.cost(food, packages * Decimal(state.package_amount), state.package_kind)
            if cost is not None:
                return {'cost': cost, 'reason': None, 'packages': packages}
    if price is None:
        return {'cost': None, 'reason': 'no_price'}
    total = Decimal(0)
    for q, k in quantities:
        cost, reason = book.cost(food, q, k)
        if cost is None:
            return {'cost': None, 'reason': reason}
        total += cost
    return {'cost': total, 'reason': None}


def estimate_entries(space, entries):
    """
    Cost of shopping entries, one item per food (and per checked state): {total, checked_total, items, missing}.
    Each item says where its price comes from: "estimated" prices are the ones an adjustment may move.
    """
    entries = [e for e in entries if e.food_id]
    book = PriceBook(space, list({e.food_id: e.food for e in entries}.values()))
    groups = OrderedDict()
    for e in entries:
        groups.setdefault((e.food_id, bool(e.checked)), []).append(e)
    items, total, checked_total, missing = [], Decimal(0), Decimal(0), []
    for (food_id, checked), group in groups.items():
        food = book.foods[food_id]
        result = _group_cost(book, food, group)
        item = {'food': {'id': food.id, 'name': food.name}, 'checked': checked, 'entries': [e.id for e in group],
                'cost': _round(result['cost']) if result['cost'] is not None else None, 'reason': result['reason'],
                'packages': result.get('packages'),
                'source': KitchenFood.PRICE_CONFIRMED if result.get('package_price') else book.source(food)}
        item['_cost'] = result['cost']
        items.append(item)
        if result['cost'] is None:
            missing.append((food, result['reason']))
        else:
            total += result['cost']
            if checked:
                checked_total += result['cost']
    return {'total': _round(total), 'checked_total': _round(checked_total), 'items': items, 'missing': _missing(missing), 'book': book}


def public(estimate):
    """Estimate without the internal fields, ready for the API."""
    data = {k: v for k, v in estimate.items() if k != 'book'}
    if 'items' in data:
        data['items'] = [{k: v for k, v in i.items() if k != '_cost'} for i in data['items']]
    return data


# ---------------------------------------------------------------- setting prices

def _reference_unit(space, per):
    """Unit (and amount) to use as the food reference for a price per kg / l / piece: an existing unit of the space
    when there is one ("g" -> 1000 g), a new one otherwise."""
    quantity, kind = PERS[per]
    fallback = None
    for unit in Unit.objects.filter(space=space).order_by('id'):
        direct = _direct(unit)
        if not direct or direct[1] != kind:
            continue
        if direct[0] == quantity:
            return unit, Decimal(1)
        if fallback is None and kind != PIECE and direct[0] in (1, 10):
            fallback = (unit, quantity / direct[0])
    if fallback:
        return fallback
    name, base = {'kg': ('kg', 'kg'), 'l': ('l', 'l'), 'piece': ('pièce', None)}[per]
    unit, _ = Unit.objects.get_or_create(space=space, name=name, defaults={'base_unit': base})
    return unit, Decimal(1)


class PriceError(ValueError):
    pass


def _state(food):
    from kitchen.services import kitchen_food
    return kitchen_food(food)


@transaction.atomic
def set_food_price(food, price, per, source=KitchenFood.PRICE_CONFIRMED, weight=1):
    """
    Store a price per kg / l / piece in the food's upstream Price property, and where it comes from.
    The food reference (`properties_food_amount` of `properties_food_unit`) is shared with nutrition values: it is set
    when the food has none (or nothing else uses it), otherwise the price is converted into it.
    price None removes the price.
    """
    space = food.space
    pt = price_type(space)
    state = _state(food)
    existing = Property.objects.filter(foodproperty__food=food, property_type=pt).first()
    if price is None:
        if existing:
            existing.delete()
        state.price_source = ''
        state.price_weight = 1
        state.save()
        return
    if per not in PERS:
        raise PriceError('per')
    price = Decimal(str(price))
    if price < 0:
        raise PriceError('price')
    quantity, kind = PERS[per]
    ref = to_base(food.properties_food_amount, food.properties_food_unit, food, space) if food.properties_food_unit_id and food.properties_food_amount else None
    others = Property.objects.filter(foodproperty__food=food).exclude(property_type=pt).exists()
    ref_in_kind = convert(ref[0], ref[1], kind, PriceBook(space, [food]).piece_weight(food)) if ref else None
    if ref is None and others:
        # nutrition values for a reference that cannot be read ("100 portion", no unit): rewriting the reference
        # would silently change them
        raise PriceError('reference')
    if ref is None or (not others and ref[1] != kind):
        unit, amount = _reference_unit(space, per)
        Food.objects.filter(id=food.id).update(properties_food_unit=unit, properties_food_amount=amount)
        food.properties_food_unit, food.properties_food_amount = unit, amount
        value = price * amount * _direct(unit)[0] / quantity
    elif ref_in_kind is None:
        # nutrition values per 100 g and a price per piece without the weight of a piece: cannot be stored
        raise PriceError('reference')
    else:
        value = price / quantity * ref_in_kind
    value = value.quantize(Decimal('0.0001'))  # what the database keeps: the fork compares it later
    if existing:
        existing.property_amount = value
        existing.save()
    else:
        existing = Property.objects.create(space=space, property_type=pt, property_amount=value)
        food.properties.add(existing)
    state.price_source = source
    state.price_weight = weight
    state.price_value = existing.property_amount
    state.save()


def suggestion(food):
    """Price the dictionary proposes for a food: {price, per, piece_weight}, or None."""
    entry = price_dictionary.lookup(food.name)
    if not entry:
        return None
    return {'price': float(entry['price']), 'per': entry['per'],
            'piece_weight': float(entry['piece_weight']) if entry['piece_weight'] else None}


def apply_suggestion(food):
    """Store the dictionary price of a food as "estimated" (with the weight of a piece if the food has none).
    Returns None, or why it could not: "no_suggestion", "reference"."""
    entry = price_dictionary.lookup(food.name)
    if not entry:
        return 'no_suggestion'
    try:
        with transaction.atomic():
            state = _state(food)
            if entry['piece_weight'] and not state.piece_weight:
                state.piece_weight = entry['piece_weight']
                state.save()
            set_food_price(food, entry['price'], entry['per'], KitchenFood.PRICE_ESTIMATED)
    except PriceError as e:
        return str(e)
    return None


def missing_queryset(space):
    """Foods that are bought (used by a recipe or a shopping list, not "never on the list", not a family) and have no
    price, the most used first."""
    pt = price_type(space)
    priced = FoodProperty.objects.filter(property__property_type=pt, property__property_amount__isnull=False).values('food_id')
    return (Food.objects.filter(space=space, ignore_shopping=False, numchild=0)
            .exclude(id__in=priced).exclude(kitchen__is_family=True)
            .annotate(uses=Count('ingredient', distinct=True) + Count('shopping_entries', distinct=True))
            .filter(uses__gt=0).order_by('-uses', 'name'))


def apply_all_suggestions(space):
    """Dictionary prices for every food without a price that the dictionary knows: number of prices set."""
    return sum(1 for food in list(missing_queryset(space)) if price_dictionary.lookup(food.name) and apply_suggestion(food) is None)


# ---------------------------------------------------------------- after shopping

def _scale_price(food, ratio, weight):
    pt = price_type(food.space)
    prop = Property.objects.filter(foodproperty__food=food, property_type=pt).first()
    if prop is None or prop.property_amount is None:
        return
    prop.property_amount = (Decimal(prop.property_amount) * ratio).quantize(Decimal('0.0001'))
    prop.save()
    state = _state(food)
    state.price_weight = weight
    state.price_value = prop.property_amount
    state.save()


def adjust_after_shopping(space, entries, paid, apply=True):
    """
    The user paid `paid` for the checked `entries`. Prices set by hand (confirmed) are taken as right; the rest of the
    gap is spread over the estimated prices, proportionally: factor = (paid - confirmed part) / estimated part.
    Each estimated price then moves towards its new value by 1 / (observations + 1) (weighted average), so one unusual
    receipt does not undo everything. Returns the comparison shown before saving, and what was changed.
    Items without a price are in what was paid but not in the estimate: while there are some, nothing is adjusted
    (they would read as an error of the estimated prices); the user corrects them first, or skips.
    """
    paid = Decimal(str(paid))
    estimate = estimate_entries(space, entries)
    book = estimate['book']
    estimated = [i for i in estimate['items'] if i['_cost'] is not None and i['source'] == KitchenFood.PRICE_ESTIMATED]
    estimated_part = sum((i['_cost'] for i in estimated), Decimal(0))
    fixed_part = sum((i['_cost'] for i in estimate['items'] if i['_cost'] is not None), Decimal(0)) - estimated_part
    total = estimated_part + fixed_part
    result = {'paid': _round(paid), 'estimated': _round(total), 'estimated_part': _round(estimated_part),
              'confirmed_part': _round(fixed_part), 'factor': None, 'percent': None, 'adjusted': 0,
              'missing': estimate['missing'], 'blocked': bool(estimate['missing'])}
    if estimated_part <= 0:
        return result
    factor = min(MAX_FACTOR, max(MIN_FACTOR, (paid - fixed_part) / estimated_part))
    result['factor'] = _round(factor, 4)
    result['percent'] = int(round((factor - 1) * 100))
    result['blocked'] = bool(estimate['missing'])
    if not apply or result['blocked']:
        return result
    with transaction.atomic():
        done = set()
        for item in estimated:
            food = book.foods[item['food']['id']]
            if food.id in done:
                continue
            done.add(food.id)
            state = book.state(food)
            weight = state.price_weight if state and state.price_weight else 1
            ratio = 1 + (factor - 1) / (weight + 1)
            _scale_price(food, ratio, min(MAX_WEIGHT, weight + 1))
    result['adjusted'] = len(done)
    return result


def correct_item(space, food, entries, paid):
    """"The salmon was 6.90 €": the price of the food becomes what was paid for these entries, confirmed."""
    paid = Decimal(str(paid))
    book = PriceBook(space, [food])
    state = book.state(food)
    result = _group_cost(book, food, entries)
    if result.get('package_price'):
        state.package_price = paid / result['packages']
        state.save()
        return
    if result.get('packages'):
        quantity, kind = result['packages'] * Decimal(state.package_amount), state.package_kind
    else:
        bases = [to_base(e.amount, e.unit, food, space) for e in entries if e.amount and Decimal(e.amount) > 0]
        if not bases or any(b is None for b in bases):
            raise PriceError('no_conversion')
        price = book.price(food)
        kind = price[1] if price else bases[0][1]
        weight = book.piece_weight(food)
        converted = [convert(q, k, kind, weight) for q, k in bases]
        if any(c is None for c in converted):
            raise PriceError('no_conversion')
        quantity = sum(converted)
    if quantity <= 0:
        raise PriceError('no_conversion')
    per = PER_OF_KIND[kind]
    set_food_price(food, paid / quantity * PERS[per][0], per, KitchenFood.PRICE_CONFIRMED)


def entries_for(space, ids):
    return list(ShoppingListEntry.objects.filter(space=space, id__in=ids).select_related('food', 'food__properties_food_unit', 'unit'))
