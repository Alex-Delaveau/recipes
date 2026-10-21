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


def test_duplicates_are_grouped_around_one_food_to_keep(setup_space, u1_s1):
    with scopes_disabled():
        for name in ['Oignon', 'oignons', 'Oignon jaune']:
            Food.objects.create(name=name, space=setup_space)
    results = u1_s1.get(reverse('kitchen:duplicates')).json()['results']
    assert {p['keep']['name'] for p in results} == {'Oignon'}
    assert sorted(p['drop']['name'] for p in results) == ['Oignon jaune', 'oignons']


def test_aisle_counts_count_every_food(setup_space, u1_s1):
    with scopes_disabled():
        for name in ['Courgette', 'Poireau', 'Navet']:
            Food.objects.create(name=name, space=setup_space)
    aisles = {a['name']: a['foods'] for a in u1_s1.get(reverse('kitchen:aisles')).json()['aisles']}
    assert aisles['Fruits et légumes'] == 3


def test_invalid_category_is_a_400(setup_space, u1_s1):
    with scopes_disabled():
        food = Food.objects.create(name='Navet', space=setup_space)
    response = u1_s1.post(reverse('kitchen:food-aisle', args=[food.id]), {'category': 'abc'}, content_type='application/json')
    assert response.status_code == 400


def test_other_space_food_cannot_be_changed(setup_space, u1_s2):
    with scopes_disabled():
        food = Food.objects.create(name='Navet', space=setup_space)
    assert u1_s2.post(reverse('kitchen:food-aisle', args=[food.id]), {'category': None}, content_type='application/json').status_code == 404
    assert u1_s2.post(reverse('kitchen:food-family', args=[food.id]), {'is_family': True}, content_type='application/json').status_code == 404


# ---------------------------------------------------------------- names left over by imports

CLEAN_NAMES = [
    ('à café coriandre en poudre', 'coriandre en poudre'),
    ("à café d'huile d'olive", "huile d'olive"),
    ('à soupe beurre de cacahuète nature', 'beurre de cacahuète nature'),
    ("à soupe d'huile", 'huile'),
    ('à soupe de maïzena', 'maïzena'),
    ("d'eau + 30 ml", 'eau'),
    ('200 g de farine', 'farine'),
    ('c. à soupe rase de sucre', 'sucre'),
    ('2 c. à s. de miel', 'miel'),
    ('de la crème', 'crème'),
]
KEEP_NAMES = ['nouveaux', 'Abricot', 'aiguillettes de poulet', 'Pomme de terre', 'Crème fraîche', "Huile d'olive", 'Ail',
              'Pâte de curry', 'Sauce à la crème', '4 épices', '5 baies', '3 fromages', '7 Up', '2 en 1', '100% cacao',
              'Du Barry', 'Des de jambon']


@pytest.mark.parametrize('name,clean', CLEAN_NAMES)
def test_clean_food_name(name, clean):
    from kitchen.french import clean_food_name
    assert clean_food_name(name) == clean


@pytest.mark.parametrize('name', KEEP_NAMES)
def test_clean_food_name_keeps_real_names(name):
    from kitchen.french import clean_food_name
    assert clean_food_name(name) == name


def test_names_to_fix_proposes_merge_or_rename(setup_space, u1_s1):
    with scopes_disabled():
        huile = Food.objects.create(name='Huile', space=setup_space)
        a = Food.objects.create(name="à soupe d'huile", space=setup_space)
        b = Food.objects.create(name='à café coriandre en poudre', space=setup_space)
        c = Food.objects.create(name='à soupe coriandre en poudre', space=setup_space)
        Food.objects.create(name='nouveaux', space=setup_space)
    data = u1_s1.get(reverse('kitchen:foods-names')).json()
    by_id = {r['id']: r for r in data['results']}
    assert data['count'] == 3 and set(by_id) == {a.id, b.id, c.id}
    assert by_id[a.id]['target'] == {'id': huile.id, 'name': 'Huile', 'renamed': False}
    # two foods cleaning to the same new name: one is renamed, the other merges into it
    renamed = [r for r in (by_id[b.id], by_id[c.id]) if r['target'] is None]
    merged = [r for r in (by_id[b.id], by_id[c.id]) if r['target'] is not None]
    assert len(renamed) == 1 and renamed[0]['clean'] == 'coriandre en poudre'
    assert merged[0]['target'] == {'id': renamed[0]['id'], 'name': 'coriandre en poudre', 'renamed': True}
    # renames come first
    assert data['results'][0]['target'] is None
    assert u1_s1.get(reverse('kitchen:foods')).json()['names_to_fix'] == 3


def test_to_sort_tells_usage(setup_space, u1_s1):
    with scopes_disabled():
        Food.objects.create(name='nouveaux', space=setup_space)
    item = u1_s1.get(reverse('kitchen:foods-to-sort')).json()['results'][0]
    assert item['name'] == 'nouveaux' and item['recipes'] == 0 and item['shopping'] == 0


def test_kept_name_is_not_proposed_again(setup_space, u1_s1):
    with scopes_disabled():
        food = Food.objects.create(name='de la crème', space=setup_space)
    assert u1_s1.get(reverse('kitchen:foods-names')).json()['count'] == 1
    assert u1_s1.post(reverse('kitchen:food-keep-name', args=[food.id])).status_code == 200
    assert u1_s1.get(reverse('kitchen:foods-names')).json()['count'] == 0
    with scopes_disabled():  # renamed later: checked again
        food.name = 'de la crème liquide'
        food.save()
    assert u1_s1.get(reverse('kitchen:foods-names')).json()['count'] == 1


def test_delete_only_unused_foods_that_are_not_families(setup_space, u1_s1, recipe_1_s1):
    with scopes_disabled():
        family = Food.add_root(name='Zzoignon', space=setup_space)
        child = family.add_child(name='Zzoignon rouge', space=setup_space)
        ingredient = Ingredient.objects.filter(step__recipe=recipe_1_s1).first()
        ingredient.food = child
        ingredient.save()
        free = Food.objects.create(name='nouveaux', space=setup_space)
        lines = Ingredient.objects.count()
    # a family: its children (and their recipe lines) would go with it
    response = u1_s1.post(reverse('kitchen:food-delete', args=[family.id]))
    assert response.status_code == 409 and response.json()['reason'] == 'family'
    response = u1_s1.post(reverse('kitchen:food-delete', args=[child.id]))
    assert response.status_code == 409 and response.json()['reason'] == 'used'
    assert u1_s1.post(reverse('kitchen:food-delete', args=[free.id])).status_code == 204
    with scopes_disabled():
        assert Food.objects.filter(id__in=[family.id, child.id]).count() == 2
        assert not Food.objects.filter(id=free.id).exists()
        assert Ingredient.objects.count() == lines
