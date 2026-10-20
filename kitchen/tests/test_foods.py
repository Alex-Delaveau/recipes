import pytest
from django.contrib import auth
from django.urls import reverse
from django_scopes import scopes_disabled

from cookbook.models import Automation, Food, Ingredient, Recipe, ShoppingListEntry, Step, Supermarket, SupermarketCategory
from kitchen import services
from kitchen.aisles import GENERIC_AISLES, GENERIC_SUPERMARKET_NAME
from kitchen.models import KitchenFood, KitchenSpace
from kitchen.names import similarity


@pytest.fixture
def setup_space(space_1):
    with scopes_disabled():
        SupermarketCategory.objects.create(name='Crèmerie', space=space_1)
        SupermarketCategory.objects.create(name='Divers', space=space_1)
        services.ensure_setup(space_1)
    return space_1


def category(space, name):
    with scopes_disabled():
        return SupermarketCategory.objects.get(space=space, name=name)


# ---------------------------------------------------------------- similarity rule on French examples

DUPLICATES = [
    ('oignons', 'Oignon'),            # plural
    ('Oignon jaune', 'oignon'),       # extra word
    ('1 oignon émincé', 'Oignon'),    # quantity + preparation
    ('Échalote', 'echalotes'),        # accents + plural
    ('poireaux', 'Poireau'),          # -eaux plural
    ('Œufs', 'oeuf'),                 # ligature
    ('pois chiches', 'Pois chiche'),  # invariable word + plural
    ('Tomates cerises', 'tomate cerise'),
    ('carrotte', 'Carotte'),          # typo
    ('Persil plat', 'persil'),
    ('Farine T55', 'farine'),
    ('Crème fraîche épaisse', 'Crème fraîche'),
]

DIFFERENT = [
    ('Pomme de terre', 'Pomme'),      # compound food
    ('Lait de coco', 'Lait'),
    ("Huile d'olive", 'Huile'),
    ('Ail', 'Riz'),
    ('Citron', 'Citronnelle'),
    ('Poivre', 'Poivron'),
    ('Sel', 'Sucre'),
]


@pytest.mark.parametrize('a,b', DUPLICATES)
def test_similarity_finds_french_duplicates(a, b):
    score, reason = similarity(a, b)
    assert reason is not None, (a, b, score)


@pytest.mark.parametrize('a,b', DIFFERENT)
def test_similarity_keeps_different_foods_apart(a, b):
    score, reason = similarity(a, b)
    assert reason is None, (a, b, score, reason)


def test_duplicates_endpoint_detects_french_examples(setup_space, u1_s1):
    names = ['Oignon', 'oignons', 'Oignon jaune', 'Pomme de terre', 'Pomme', 'Échalote', 'echalotes', 'Lait de coco', 'Lait']
    with scopes_disabled():
        foods = {n: Food.objects.create(name=n, space=setup_space) for n in names}
        recipe = Recipe.objects.create(name='Soupe', created_by=auth.get_user(u1_s1), space=setup_space)
        step = Step.objects.create(instruction='', space=setup_space)
        step.ingredients.add(Ingredient.objects.create(food=foods['Oignon'], amount=1, space=setup_space))
        recipe.steps.add(step)
    response = u1_s1.get(reverse('kitchen:duplicates'))
    assert response.status_code == 200
    pairs = {frozenset((p['keep']['name'], p['drop']['name'])) for p in response.json()['results']}
    assert frozenset(('Oignon', 'oignons')) in pairs
    assert frozenset(('Oignon', 'Oignon jaune')) in pairs
    assert frozenset(('Échalote', 'echalotes')) in pairs
    assert frozenset(('Pomme de terre', 'Pomme')) not in pairs
    assert frozenset(('Lait de coco', 'Lait')) not in pairs
    oignon = next(p for p in response.json()['results'] if {p['keep']['name'], p['drop']['name']} == {'Oignon', 'oignons'})
    assert oignon['keep']['name'] == 'Oignon' and oignon['keep']['recipes'] == 1  # the used food is kept


def test_dismissed_pair_is_not_proposed_again(setup_space, u1_s1):
    with scopes_disabled():
        a = Food.objects.create(name='Oignon', space=setup_space)
        b = Food.objects.create(name='oignons', space=setup_space)
    assert u1_s1.post(reverse('kitchen:duplicates-dismiss'), {'a': a.id, 'b': b.id}, content_type='application/json').status_code == 204
    assert u1_s1.get(reverse('kitchen:duplicates')).json()['results'] == []


# ---------------------------------------------------------------- generic aisle order

def test_setup_creates_generic_order_reusing_matching_categories(setup_space):
    with scopes_disabled():
        kitchen = KitchenSpace.objects.get(space=setup_space)
        assert kitchen.generic_supermarket.name == GENERIC_SUPERMARKET_NAME
        names = [c.name for c in services.ordered_aisles(setup_space)]
    assert names[0] == 'Fruits et légumes' and names[8] == 'Hygiène et maison'
    assert names[2] == 'Crèmerie'  # stands for "Frais", no second category created
    assert 'Frais' not in names and names[-1] == 'Divers'
    assert len(names) == len(GENERIC_AISLES) + 1
    services.ensure_setup(setup_space)  # idempotent
    with scopes_disabled():
        assert Supermarket.objects.filter(space=setup_space, name=GENERIC_SUPERMARKET_NAME).count() == 1


def test_aisle_order_can_be_changed(setup_space, u1_s1):
    aisles = u1_s1.get(reverse('kitchen:aisles')).json()['aisles']
    ids = [a['id'] for a in aisles]
    new = [ids[-1]] + ids[:-1]
    response = u1_s1.put(reverse('kitchen:aisles'), {'order': new}, content_type='application/json')
    assert [a['id'] for a in response.json()['aisles']] == new


def test_guest_cannot_reorder_aisles(setup_space, g1_s1):
    assert g1_s1.put(reverse('kitchen:aisles'), {'order': []}, content_type='application/json').status_code == 403


# ---------------------------------------------------------------- aisle suggestion

def test_new_food_gets_family_aisle_first(setup_space):
    with scopes_disabled():
        legumes = Food.add_root(name='Légumes', space=setup_space, supermarket_category=category(setup_space, 'Divers'))
        food = legumes.add_child(name='Panais', space=setup_space)
        food.refresh_from_db()
        assert food.supermarket_category.name == 'Divers'
        assert KitchenFood.objects.get(food=food).aisle_source == KitchenFood.SOURCE_PARENT


def test_new_food_gets_dictionary_aisle(setup_space):
    with scopes_disabled():
        food = Food.objects.create(name='Courgettes', space=setup_space)  # plural, through the upstream manager
        food.refresh_from_db()
        assert food.supermarket_category.name == 'Fruits et légumes'
        state = KitchenFood.objects.get(food=food)
        assert state.aisle_source == KitchenFood.SOURCE_DICTIONARY and not state.aisle_confirmed


def test_new_food_gets_similar_food_aisle(setup_space):
    with scopes_disabled():
        Food.objects.create(name='Gochujang', space=setup_space, supermarket_category=category(setup_space, 'Divers'))
        food = Food.objects.create(name='Gochujang doux', space=setup_space)
        food.refresh_from_db()
        assert food.supermarket_category.name == 'Divers'
        assert KitchenFood.objects.get(food=food).aisle_source == KitchenFood.SOURCE_SIMILAR


def test_food_created_with_an_aisle_is_confirmed(setup_space):
    with scopes_disabled():
        food = Food.objects.create(name='Chose', space=setup_space, supermarket_category=category(setup_space, 'Divers'))
        assert KitchenFood.objects.get(food=food).aisle_confirmed


def test_space_without_setup_is_untouched(space_2):
    with scopes_disabled():
        food = Food.objects.create(name='Courgette', space=space_2)
        food.refresh_from_db()
        assert food.supermarket_category is None
        assert not KitchenFood.objects.filter(food=food).exists()


def test_shopping_list_food_gets_an_aisle(setup_space, u1_s1):
    response = u1_s1.post(reverse('api:shoppinglistentry-list'), {'food': {'name': 'Citrons verts'}, 'amount': 2, 'unit': None},
                          content_type='application/json')
    assert response.status_code == 201, response.content
    with scopes_disabled():
        food = ShoppingListEntry.objects.get(id=response.json()['id']).food
        assert food.supermarket_category.name == 'Fruits et légumes'


# ---------------------------------------------------------------- queue, aisle, families

def test_to_sort_queue_and_one_tap_confirmation(setup_space, u1_s1):
    with scopes_disabled():
        food = Food.objects.create(name='Courgette', space=setup_space)
        Food.objects.create(name='Beurre', space=setup_space, supermarket_category=category(setup_space, 'Crèmerie'))
    queue = u1_s1.get(reverse('kitchen:foods-to-sort')).json()
    assert queue['count'] == 1
    assert queue['results'][0]['name'] == 'Courgette' and queue['results'][0]['suggested']['name'] == 'Fruits et légumes'
    divers = category(setup_space, 'Divers')
    response = u1_s1.post(reverse('kitchen:food-aisle', args=[food.id]), {'category': divers.id}, content_type='application/json')
    assert response.status_code == 200 and response.json()['to_sort'] == 0
    with scopes_disabled():
        food.refresh_from_db()
        assert food.supermarket_category_id == divers.id


def test_family_aisle_passes_on_to_members(setup_space, u1_s1):
    with scopes_disabled():
        family = Food.add_root(name='Herbes', space=setup_space)
        member = family.add_child(name='Persil', space=setup_space)
        own = family.add_child(name='Gingembre', space=setup_space, supermarket_category=category(setup_space, 'Crèmerie'))
    divers = category(setup_space, 'Divers')
    u1_s1.post(reverse('kitchen:food-aisle', args=[family.id]), {'category': divers.id}, content_type='application/json')
    with scopes_disabled():
        member.refresh_from_db()
        own.refresh_from_db()
        assert member.supermarket_category_id == divers.id
        assert own.supermarket_category.name == 'Crèmerie'  # its own aisle is kept


def test_move_into_family_takes_its_aisle(setup_space, u1_s1):
    with scopes_disabled():
        family = Food.add_root(name='Légumes', space=setup_space, supermarket_category=category(setup_space, 'Divers'))
        food = Food.add_root(name='Navet', space=setup_space)
        other = Food.add_root(name='Truc', space=space_other(setup_space))
    response = u1_s1.post(reverse('kitchen:food-move', args=[food.id]), {'family': family.id}, content_type='application/json')
    assert response.status_code == 200, response.content
    with scopes_disabled():
        food.refresh_from_db()
        assert food.get_parent().id == family.id and food.supermarket_category.name == 'Divers'
    # back to the top level
    u1_s1.post(reverse('kitchen:food-move', args=[food.id]), {'family': None}, content_type='application/json')
    with scopes_disabled():
        food.refresh_from_db()
        assert food.depth == 1
    # a food of another space is not a valid family
    assert u1_s1.post(reverse('kitchen:food-move', args=[food.id]), {'family': other.id}, content_type='application/json').status_code == 404


def space_other(space):
    from cookbook.models import Space
    return Space.objects.exclude(id=space.id).first() or Space.objects.create(name='other', created_by=space.created_by)


def test_food_list_marks_families_and_members(setup_space, u1_s1):
    with scopes_disabled():
        family = Food.add_root(name='Légumes', space=setup_space)
        family.add_child(name='Céleri', space=setup_space)
        empty = Food.add_root(name='Fromages', space=setup_space)
    u1_s1.post(reverse('kitchen:food-family', args=[empty.id]), {'is_family': True}, content_type='application/json')
    foods = {f['name']: f for f in u1_s1.get(reverse('kitchen:foods')).json()['foods']}
    assert foods['Légumes']['is_family'] and foods['Fromages']['is_family']
    assert foods['Céleri']['family'] == family.id and not foods['Céleri']['is_family']


# ---------------------------------------------------------------- import review

def test_match_proposes_closest_existing_food(setup_space, u1_s1):
    with scopes_disabled():
        Food.objects.create(name='Oignon', space=setup_space)
        Food.objects.create(name='Tomate', space=setup_space, plural_name='Tomates')
        Automation.objects.create(type=Automation.FOOD_ALIAS, param_1='ognon', param_2='Oignon', space=setup_space,
                                  created_by=auth.get_user(u1_s1))
    response = u1_s1.post(reverse('kitchen:foods-match'), {'names': ['oignons émincés', 'Tomates', 'ognon', 'Pomme de terre']},
                          content_type='application/json')
    results = response.json()['results']
    assert results['oignons émincés']['closest']['name'] == 'Oignon'
    assert results['Tomates']['exists']  # plural name
    assert results['ognon']['exists']  # an alias already maps it
    assert results['Pomme de terre']['closest'] is None


def test_dictionary_finds_the_food_inside_a_longer_name():
    from kitchen.aisles import suggest_aisle_key
    assert suggest_aisle_key('Gros oignons rouges') == 'fruits_legumes'
    assert suggest_aisle_key('Tomates cerises bio') == 'fruits_legumes'
    assert suggest_aisle_key('Crème fraîche épaisse') == 'frais'
    assert suggest_aisle_key('Truc inconnu') is None


def test_upstream_merge_still_works_with_fork_food_state(setup_space, u1_s1):
    with scopes_disabled():
        keep = Food.objects.create(name='Poireau', space=setup_space)
        drop = Food.objects.create(name='poireaux', space=setup_space)
        assert KitchenFood.objects.filter(food__in=[keep, drop]).count() == 2
    response = u1_s1.put(reverse('api:food-merge', args=[drop.id, keep.id]), {}, content_type='application/json')
    assert response.status_code == 200, response.content
    with scopes_disabled():
        assert not Food.objects.filter(id=drop.id).exists()
        assert KitchenFood.objects.filter(food=keep).exists()
