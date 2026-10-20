from datetime import timedelta

import pytest
from django.contrib import auth
from django.urls import reverse
from django.utils import timezone
from django_scopes import scopes_disabled

from cookbook.models import CookLog, Food, Ingredient, Recipe, Step, ViewLog

URL = reverse('kitchen:recipes')


def make_recipe(space, user, name, foods, working=10, waiting=0):
    recipe = Recipe.objects.create(name=name, created_by=user, space=space, working_time=working, waiting_time=waiting)
    step = Step.objects.create(instruction='', space=space)
    for food in foods:
        step.ingredients.add(Ingredient.objects.create(food=food, amount=1, space=space))
    recipe.steps.add(step)
    return recipe


@pytest.fixture
def kitchen_data(space_1, u1_s1):
    user = auth.get_user(u1_s1)
    with scopes_disabled():
        legumes = Food.add_root(name='Légumes', space=space_1)
        courgette = legumes.add_child(name='Courgette', space=space_1)
        riz = Food.add_root(name='Riz', space=space_1)
        oeuf = Food.add_root(name='Œuf', space=space_1)
        recipes = {
            'both': make_recipe(space_1, user, 'Riz aux courgettes', [courgette, riz], 10, 20),
            'riz': make_recipe(space_1, user, 'Riz cantonais', [riz, oeuf], 30, 30),
            'none': make_recipe(space_1, user, 'Omelette', [oeuf], 5, 0),
        }
    return {'user': user, 'legumes': legumes, 'courgette': courgette, 'riz': riz, 'recipes': recipes}


def names(response):
    assert response.status_code == 200, response.content
    return [r['name'] for r in response.json()['results']]


def test_anonymous_is_refused(client):
    assert client.get(URL).status_code == 403


def test_other_space_is_not_visible(kitchen_data, u1_s2):
    assert names(u1_s2.get(URL)) == []


def test_private_recipe_of_another_user_stays_hidden(kitchen_data, u1_s1, u2_s1, space_1):
    other = auth.get_user(u2_s1)
    with scopes_disabled():
        make_recipe(space_1, other, 'Secret de famille', [], 5, 0).__class__.objects.filter(name='Secret de famille').update(private=True)
    assert 'Secret de famille' not in names(u1_s1.get(URL))
    assert 'Secret de famille' in names(u2_s1.get(URL))


def test_foods_on_hand_rank_recipes_using_most_of_them(kitchen_data, u1_s1):
    d = kitchen_data
    response = u1_s1.get(URL, {'have': [d['courgette'].id, d['riz'].id]})
    assert names(response) == ['Riz aux courgettes', 'Riz cantonais']
    first = response.json()['results'][0]
    assert first['matched_foods'] == 2 and first['total_foods'] == 2


def test_food_family_matches_its_children(kitchen_data, u1_s1):
    assert names(u1_s1.get(URL, {'have': [kitchen_data['legumes'].id]})) == ['Riz aux courgettes']


def test_max_total_time(kitchen_data, u1_s1):
    assert sorted(names(u1_s1.get(URL, {'max_time': 30}))) == ['Omelette', 'Riz aux courgettes']
    assert names(u1_s1.get(URL, {'max_time': 15})) == ['Omelette']


def test_upstream_text_search_still_applies(kitchen_data, u1_s1):
    assert sorted(names(u1_s1.get(URL, {'query': 'riz'}))) == ['Riz aux courgettes', 'Riz cantonais']


def test_recent_lists_only_viewed_recipes_latest_first(kitchen_data, u1_s1, space_1):
    d = kitchen_data
    with scopes_disabled():
        for days, key in ((3, 'riz'), (1, 'none')):
            log = ViewLog.objects.create(recipe=d['recipes'][key], created_by=d['user'], space=space_1)
            ViewLog.objects.filter(pk=log.pk).update(created_at=timezone.now() - timedelta(days=days))
    assert names(u1_s1.get(URL, {'sort': 'recent'})) == ['Omelette', 'Riz cantonais']


def test_forgotten_puts_never_cooked_then_oldest_first(kitchen_data, u1_s1, space_1):
    d = kitchen_data
    with scopes_disabled():
        CookLog.objects.create(recipe=d['recipes']['riz'], created_by=d['user'], space=space_1,
                               created_at=timezone.now() - timedelta(days=60))
        CookLog.objects.create(recipe=d['recipes']['none'], created_by=d['user'], space=space_1,
                               created_at=timezone.now() - timedelta(days=2))
    response = u1_s1.get(URL, {'sort': 'forgotten'})
    assert names(response) == ['Riz aux courgettes', 'Riz cantonais', 'Omelette']
    assert response.json()['results'][0]['last_cooked'] is None
    assert response.json()['results'][1]['last_cooked'] is not None


def test_random_returns_everything(kitchen_data, u1_s1):
    assert len(names(u1_s1.get(URL, {'sort': 'random'}))) == 3
