from decimal import Decimal

import pytest
from django.contrib import auth
from django.urls import reverse
from django_scopes import scopes_disabled

from cookbook.models import (Food, Ingredient, Property, PropertyType, Recipe, ShoppingListEntry, Step, Unit,
                             UnitConversion)
from kitchen import prices
from kitchen.models import KitchenFood


@pytest.fixture
def units(space_1):
    with scopes_disabled():
        return {name: Unit.objects.create(name=name, space=space_1) for name in ('g', 'cl', 'c. à soupe', 'pièce', 'tranche', 'boîte')}


def food(space, name, price=None, per='kg', source=KitchenFood.PRICE_ESTIMATED, **state):
    with scopes_disabled():
        f = Food.objects.create(name=name, space=space)
        if state:
            KitchenFood.objects.update_or_create(food=f, defaults={'space': space, **state})
        if price is not None:
            prices.set_food_price(f, price, per, source)
            f.refresh_from_db()
        return f


def stored_price(f):
    with scopes_disabled():
        return prices.PriceBook(f.space, [Food.objects.get(id=f.id)]).display(Food.objects.get(id=f.id))


def recipe_with(space, user, servings, lines):
    with scopes_disabled():
        recipe = Recipe.objects.create(name='Test', servings=servings, created_by=user, space=space)
        step = Step.objects.create(instruction='', space=space)
        recipe.steps.add(step)
        for f, amount, unit in lines:
            step.ingredients.add(Ingredient.objects.create(food=f, amount=amount, unit=unit, space=space))
        return recipe


def entry(space, user, f, amount, unit=None, checked=False):
    with scopes_disabled():
        return ShoppingListEntry.objects.create(food=f, amount=amount, unit=unit, checked=checked, created_by=user, space=space)


# ---------------------------------------------------------------- quantities

def test_quantities_come_back_to_grams_millilitres_or_pieces(space_1, u1_s1, units):
    with scopes_disabled():
        assert prices.to_base(200, units['g']) == (200, 'g')
        assert prices.to_base(20, units['cl']) == (200, 'ml')
        assert prices.to_base(2, units['c. à soupe']) == (30, 'ml')
        assert prices.to_base(3, units['pièce']) == (3, 'piece')
        assert prices.to_base(3, None) == (3, 'piece')
        kilo = Unit.objects.create(name='Kilo (sac)', base_unit='kg', space=space_1)
        assert prices.to_base(2, kilo) == (2000, 'g')
        assert prices.to_base(1, units['tranche'], space=space_1) is None
        # the space's own conversions, here for one food only
        jambon = Food.objects.create(name='Jambon', space=space_1)
        UnitConversion.objects.create(base_amount=1, base_unit=units['tranche'], converted_amount=40, converted_unit=units['g'],
                                      food=jambon, space=space_1, created_by=auth.get_user(u1_s1))
        assert prices.to_base(2, units['tranche'], jambon, space_1) == (80, 'g')


def test_conversions_between_kinds():
    assert prices.convert(Decimal(3), 'piece', 'g', Decimal(150)) == 450
    assert prices.convert(Decimal(300), 'g', 'piece', Decimal(150)) == 2
    assert prices.convert(Decimal(200), 'ml', 'g') == 200  # density 1
    assert prices.convert(Decimal(3), 'piece', 'g') is None


# ---------------------------------------------------------------- the price of a food

def test_price_is_stored_in_the_upstream_price_property(space_1, units):
    oignon = food(space_1, 'Oignon', 2.20, 'kg', KitchenFood.PRICE_CONFIRMED)
    with scopes_disabled():
        pt = PropertyType.objects.get(space=space_1, category=PropertyType.PRICE)
        prop = Property.objects.get(foodproperty__food=oignon, property_type=pt)
        # the food reference is the existing "g" unit: 1000 g
        assert oignon.properties_food_unit == units['g'] and oignon.properties_food_amount == 1000
        assert prop.property_amount == Decimal('2.2')
    assert stored_price(oignon) == {'price': 2.2, 'per': 'kg', 'source': 'confirmed'}


def test_price_keeps_the_nutrition_reference(space_1, units):
    with scopes_disabled():
        beurre = Food.objects.create(name='Beurre', space=space_1, properties_food_amount=100, properties_food_unit=units['g'])
        kcal = PropertyType.objects.create(name='Calories', space=space_1, category=PropertyType.NUTRITION)
        beurre.properties.add(Property.objects.create(property_type=kcal, property_amount=740, space=space_1))
        prices.set_food_price(beurre, Decimal(11), 'kg')
        beurre.refresh_from_db()
        assert beurre.properties_food_amount == 100 and beurre.properties_food_unit == units['g']
        assert Property.objects.get(foodproperty__food=beurre, property_type__category=PropertyType.PRICE).property_amount == Decimal('1.1')
        # a price per piece cannot be stored in "per 100 g" without the weight of a piece
        with pytest.raises(prices.PriceError):
            prices.set_food_price(beurre, Decimal(2), 'piece')
    assert stored_price(beurre)['price'] == 11


def test_dictionary_prices_are_estimated_and_never_overwrite(space_1, u1_s1, units):
    with scopes_disabled():
        oignons = Food.objects.create(name='Oignons rouges', space=space_1)
        citron = food(space_1, 'Citron', 0.60, 'piece', KitchenFood.PRICE_CONFIRMED)
        inconnu = Food.objects.create(name='Zzz inconnu', space=space_1)
        user = auth.get_user(u1_s1)
        for f in (oignons, citron, inconnu):
            entry(space_1, user, f, 1)
        assert set(prices.missing_queryset(space_1)) == {oignons, inconnu}
        assert prices.apply_all_suggestions(space_1) == 1
        assert list(prices.missing_queryset(space_1)) == [inconnu]
        assert KitchenFood.objects.get(food=oignons).piece_weight == 150
    assert stored_price(oignons) == {'price': 3.0, 'per': 'kg', 'source': 'estimated'}
    assert stored_price(citron) == {'price': 0.6, 'per': 'piece', 'source': 'confirmed'}


# ---------------------------------------------------------------- estimates

def test_recipe_estimate_with_pieces_missing_prices_and_conversions(space_1, u1_s1, units):
    user = auth.get_user(u1_s1)
    oignon = food(space_1, 'Oignon', 2, 'kg', piece_weight=150)
    creme = food(space_1, 'Crème', 5, 'l')
    oeuf = food(space_1, 'Oeuf', Decimal('0.30'), 'piece')
    sel = food(space_1, 'Sel', 1)
    with scopes_disabled():
        Food.objects.filter(id=sel.id).update(ignore_shopping=True)
    safran = food(space_1, 'Safran')
    jambon = food(space_1, 'Jambon', 15)
    recipe = recipe_with(space_1, user, 4, [
        (oignon, 2, units['pièce']),     # 300 g -> 0.60
        (creme, 20, units['cl']),        # 0.2 l -> 1.00
        (oeuf, 3, None),                 # 0.90
        (sel, 1, units['c. à soupe']),   # never bought for a recipe
        (safran, 1, units['g']),         # no price
        (jambon, 2, units['tranche']),   # no conversion
    ])
    with scopes_disabled():
        result = prices.estimate_recipe(recipe)
    assert result['total'] == 2.5 and result['per_serving'] == 0.62
    assert {(m['name'], m['reason']) for m in result['missing']} == {('Safran', 'no_price'), ('Jambon', 'no_conversion')}

    response = u1_s1.post(reverse('kitchen:prices-recipes'), {'recipes': [{'id': recipe.id, 'servings': 8}, {'id': recipe.id}]},
                          content_type='application/json').json()
    assert [r['total'] for r in response['recipes']] == [5.0, 2.5]
    assert response['total'] == 7.5 and len(response['missing']) == 2


def test_shopping_estimate_counts_whole_packages(space_1, u1_s1, units):
    user = auth.get_user(u1_s1)
    pates = food(space_1, 'Pâtes', 2, 'kg', package_amount=500, package_kind='g', package_price=Decimal('1.20'))
    riz = food(space_1, 'Riz', 3, 'kg', package_amount=1000, package_kind='g')
    lait = food(space_1, 'Lait', Decimal('1.10'), 'l')
    e1 = entry(space_1, user, pates, 400, units['g'])
    e2 = entry(space_1, user, pates, 300, units['g'])
    e3 = entry(space_1, user, riz, 200, units['g'])
    e4 = entry(space_1, user, lait, 50, units['cl'], checked=True)
    e5 = entry(space_1, user, food(space_1, 'Safran'), 1, units['g'])
    response = u1_s1.post(reverse('kitchen:prices-shopping'), {'entries': [e.id for e in (e1, e2, e3, e4, e5)]},
                          content_type='application/json').json()
    items = {i['food']['name']: i for i in response['items']}
    assert items['Pâtes']['packages'] == 2 and items['Pâtes']['cost'] == 2.4 and items['Pâtes']['source'] == 'confirmed'
    assert items['Riz']['packages'] == 1 and items['Riz']['cost'] == 3.0  # one bag of 1 kg at 3 €/kg
    assert items['Lait']['cost'] == 0.55 and items['Lait']['checked']
    assert response['total'] == 5.95 and response['checked_total'] == 0.55
    assert response['missing'] == [{'id': items['Safran']['food']['id'], 'name': 'Safran', 'reason': 'no_price'}]


# ---------------------------------------------------------------- after shopping

def test_adjustment_moves_only_estimated_prices_and_is_smoothed(space_1, u1_s1, units):
    user = auth.get_user(u1_s1)
    pomme = food(space_1, 'Pomme', 2, 'kg')                                    # estimated
    poire = food(space_1, 'Poire', 4, 'kg')                                    # estimated
    saumon = food(space_1, 'Saumon', 20, 'kg', KitchenFood.PRICE_CONFIRMED)   # confirmed
    entries = [entry(space_1, user, pomme, 1000, units['g'], True), entry(space_1, user, poire, 500, units['g'], True),
               entry(space_1, user, saumon, 250, units['g'], True)]
    ids = [e.id for e in entries]
    # estimated: 2 + 2 + 5 (confirmed) = 9; paid 11 -> the estimated part (4) must become 6: +50 %
    preview = u1_s1.post(reverse('kitchen:prices-adjust'), {'entries': ids, 'paid': '11'}, content_type='application/json').json()
    assert preview['estimated'] == 9 and preview['confirmed_part'] == 5 and preview['percent'] == 50 and preview['adjusted'] == 0
    assert stored_price(pomme)['price'] == 2

    applied = u1_s1.post(reverse('kitchen:prices-adjust'), {'entries': ids, 'paid': '11', 'apply': True}, content_type='application/json').json()
    assert applied['adjusted'] == 2
    # weighted average: the estimate counts for one observation, the receipt for one -> half of +50 %
    assert stored_price(pomme)['price'] == 2.5 and stored_price(poire)['price'] == 5
    assert stored_price(saumon) == {'price': 20, 'per': 'kg', 'source': 'confirmed'}
    with scopes_disabled():
        assert KitchenFood.objects.get(food=pomme).price_weight == 2
    # second receipt at the same +50 %: now 1 / 3 of the move
    u1_s1.post(reverse('kitchen:prices-adjust'), {'entries': ids, 'paid': '12.5', 'apply': True}, content_type='application/json')
    assert stored_price(pomme)['price'] == pytest.approx(2.5 * (1 + 0.5 / 3), abs=0.001)


def test_adjustment_factor_is_bounded(space_1, u1_s1, units):
    user = auth.get_user(u1_s1)
    pomme = food(space_1, 'Pomme', 2, 'kg')
    e = entry(space_1, user, pomme, 1000, units['g'], True)
    result = u1_s1.post(reverse('kitchen:prices-adjust'), {'entries': [e.id], 'paid': '200'}, content_type='application/json').json()
    assert result['factor'] == 3 and result['percent'] == 200


def test_one_item_correction_confirms_its_price(space_1, u1_s1, units):
    user = auth.get_user(u1_s1)
    saumon = food(space_1, 'Saumon', 25, 'kg')
    pates = food(space_1, 'Pâtes', 2, 'kg', package_amount=500, package_kind='g', package_price=Decimal('1.20'))
    e = entry(space_1, user, saumon, 300, units['g'], True)
    response = u1_s1.post(reverse('kitchen:prices-correct'), {'food': saumon.id, 'entries': [e.id], 'paid': '6.90'}, content_type='application/json')
    assert response.status_code == 200
    assert response.json()['price'] == {'price': 23.0, 'per': 'kg', 'source': 'confirmed'}
    p = entry(space_1, user, pates, 700, units['g'], True)
    u1_s1.post(reverse('kitchen:prices-correct'), {'food': pates.id, 'entries': [p.id], 'paid': '3'}, content_type='application/json')
    with scopes_disabled():
        assert KitchenFood.objects.get(food=pates).package_price == Decimal('1.5')


# ---------------------------------------------------------------- food sheet API

def test_food_price_endpoint(space_1, u1_s1, units):
    oeuf = food(space_1, 'Oeufs')
    url = reverse('kitchen:food-price', args=[oeuf.id])
    data = u1_s1.get(url).json()
    assert data['price'] is None and data['suggestion'] == {'price': 0.35, 'per': 'piece', 'piece_weight': 60.0}
    data = u1_s1.put(url, {'price': '0,40', 'per': 'piece', 'package_amount': 6, 'package_kind': 'piece', 'package_price': '2.20',
                           'piece_weight': 60}, content_type='application/json').json()
    assert data['price'] == {'price': 0.4, 'per': 'piece', 'source': 'confirmed'}
    assert data['package'] == {'amount': 6.0, 'kind': 'piece', 'price': 2.2} and data['piece_weight'] == 60
    assert u1_s1.put(url, {'price': 'abc'}, content_type='application/json').status_code == 400
    data = u1_s1.put(url, {'price': None}, content_type='application/json').json()
    assert data['price'] is None
    data = u1_s1.put(url, {'suggest': True}, content_type='application/json').json()
    assert data['price'] == {'price': 0.35, 'per': 'piece', 'source': 'estimated'}

    foods = u1_s1.get(reverse('kitchen:foods')).json()
    assert next(f for f in foods['foods'] if f['id'] == oeuf.id)['price']['price'] == 0.35


def test_missing_queue_endpoint(space_1, u1_s1, units):
    user = auth.get_user(u1_s1)
    oignon = food(space_1, 'Oignon')
    entry(space_1, user, oignon, 1)
    food(space_1, 'Pas utilisé')
    data = u1_s1.get(reverse('kitchen:prices-missing')).json()
    assert data['count'] == 1 and data['suggested'] == 1 and data['results'][0]['name'] == 'Oignon'
    assert u1_s1.get(reverse('kitchen:foods')).json()['no_price'] == 1
    assert u1_s1.post(reverse('kitchen:prices-missing')).json() == {'applied': 1, 'count': 0}


def test_other_space_entries_are_ignored(space_1, space_2, u1_s1, u1_s2, units):
    with scopes_disabled():
        other = Food.objects.create(name='Pomme', space=space_2)
        e = ShoppingListEntry.objects.create(food=other, amount=1, created_by=auth.get_user(u1_s2), space=space_2)
    data = u1_s1.post(reverse('kitchen:prices-shopping'), {'entries': [e.id]}, content_type='application/json').json()
    assert data['items'] == [] and data['total'] == 0


# ---------------------------------------------------------------- safety (review)

def test_unreadable_reference_with_nutrition_is_never_rewritten(space_1, units):
    with scopes_disabled():
        portion = Unit.objects.create(name='portion', space=space_1)
        beurre = Food.objects.create(name='Beurre', space=space_1, properties_food_amount=100, properties_food_unit=portion)
        kcal = PropertyType.objects.create(name='Calories', space=space_1, category=PropertyType.NUTRITION)
        beurre.properties.add(Property.objects.create(property_type=kcal, property_amount=740, space=space_1))
        with pytest.raises(prices.PriceError):
            prices.set_food_price(beurre, Decimal(11), 'kg')
        assert prices.apply_suggestion(beurre) == 'reference'
        beurre.refresh_from_db()
        assert beurre.properties_food_unit == portion and beurre.properties_food_amount == 100
        assert not Property.objects.filter(foodproperty__food=beurre, property_type__category=PropertyType.PRICE).exists()


def test_price_type_named_prix_of_another_category(space_1):
    with scopes_disabled():
        PropertyType.objects.create(name='Prix', space=space_1, category=PropertyType.OTHER)
        pt = prices.price_type(space_1)
        assert pt.category == PropertyType.PRICE and pt.name != 'Prix'
        assert prices.price_type(space_1) == pt


def test_price_changed_in_upstream_screens_counts_as_confirmed(space_1, units):
    pomme = food(space_1, 'Pomme', 2, 'kg')
    assert stored_price(pomme)['source'] == 'estimated'
    with scopes_disabled():
        Property.objects.filter(foodproperty__food=pomme, property_type__category=PropertyType.PRICE).update(property_amount=Decimal('2.4'))
    assert stored_price(pomme) == {'price': 2.4, 'per': 'kg', 'source': 'confirmed'}


def test_no_adjustment_while_cart_items_have_no_price(space_1, u1_s1, units):
    user = auth.get_user(u1_s1)
    pomme = food(space_1, 'Pomme', 2, 'kg')
    entries = [entry(space_1, user, pomme, 1000, units['g'], True), entry(space_1, user, food(space_1, 'Safran'), 1, units['g'], True),
               entry(space_1, user, food(space_1, 'Sel', 1), 0, None, True)]
    result = u1_s1.post(reverse('kitchen:prices-adjust'), {'entries': [e.id for e in entries], 'paid': '9', 'apply': True},
                        content_type='application/json').json()
    assert result['blocked'] and result['adjusted'] == 0 and {m['name'] for m in result['missing']} == {'Safran', 'Sel'}
    assert stored_price(pomme)['price'] == 2


def test_numbers_are_validated(space_1, u1_s1, units):
    pomme = food(space_1, 'Pomme', 2, 'kg')
    url = reverse('kitchen:food-price', args=[pomme.id])
    for bad in ('nan', 'Infinity', '1e12', '-1'):
        assert u1_s1.put(url, {'price': bad, 'per': 'kg'}, content_type='application/json').status_code == 400
    # a refused price keeps nothing of the same request
    with scopes_disabled():
        portion = Unit.objects.create(name='portion', space=space_1)
        Food.objects.filter(id=pomme.id).update(properties_food_unit=portion)
        kcal = PropertyType.objects.create(name='Calories', space=space_1, category=PropertyType.NUTRITION)
        pomme.properties.add(Property.objects.create(property_type=kcal, property_amount=52, space=space_1))
    response = u1_s1.put(url, {'price': 3, 'per': 'kg', 'piece_weight': 180}, content_type='application/json')
    assert response.status_code == 400 and response.json()['reason'] == 'reference'
    with scopes_disabled():
        assert KitchenFood.objects.get(food=pomme).piece_weight is None


def test_private_recipes_of_others_are_not_estimated(space_1, u1_s1, u2_s1, units):
    with scopes_disabled():
        private = Recipe.objects.create(name='Secret', servings=2, private=True, created_by=auth.get_user(u2_s1), space=space_1)
    data = u1_s1.post(reverse('kitchen:prices-recipes'), {'recipes': [{'id': private.id}]}, content_type='application/json').json()
    assert data['recipes'] == []
