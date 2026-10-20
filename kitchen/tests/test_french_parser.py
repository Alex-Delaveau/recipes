"""French ingredient lines (M4): measured on real lines, through the parser, the parser API, the URL import."""
import json
from types import SimpleNamespace

import pytest
from django.contrib import auth
from django.urls import reverse
from django.utils import translation
from django_scopes import scope, scopes_disabled

from cookbook.helper.ingredient_parser import IngredientParser
from cookbook.models import Automation, Food

# real lines from French recipe sites: (line, amount, unit, food, note)
LINES = [
    ("2 c. à soupe d'huile d'olive", 2, 'c. à soupe', "huile d'olive", ''),
    ('1 cs de sucre', 1, 'c. à soupe', 'sucre', ''),
    ('1 CS de miel', 1, 'c. à soupe', 'miel', ''),
    ('1 càs de sauce soja', 1, 'c. à soupe', 'sauce soja', ''),
    ('1 càc de sel', 1, 'c. à café', 'sel', ''),
    ('1 cc de cannelle', 1, 'c. à café', 'cannelle', ''),
    ('2 cuillères à café de cumin', 2, 'c. à café', 'cumin', ''),
    ('1 c. à c. de curcuma', 1, 'c. à café', 'curcuma', ''),
    ('3 oignons émincés', 3, None, 'oignons', 'émincés'),
    ('½ citron', 0.5, None, 'citron', ''),
    ('1/2 citron vert', 0.5, None, 'citron vert', ''),
    ('1,5 kg de pommes de terre', 1.5, 'kg', 'pommes de terre', ''),
    ('200 g de farine T55', 200, 'g', 'farine', 'T55'),
    ('200g de farine', 200, 'g', 'farine', ''),
    ("2 gousses d'ail", 2, 'gousse', 'ail', ''),
    ('2-3 tomates bien mûres', 2, None, 'tomates', '2-3, bien mûres'),
    ('2 à 3 carottes', 2, None, 'carottes', '2-3'),
    ('1 pincée de sel', 1, 'pincée', 'sel', ''),
    ('Une pincée de poivre', 1, 'pincée', 'poivre', ''),
    ('1 sachet de levure chimique', 1, 'sachet', 'levure chimique', ''),
    ('3 brins de thym', 3, 'brin', 'thym', ''),
    ('1 botte de radis', 1, 'botte', 'radis', ''),
    ('4 tranches de jambon', 4, 'tranche', 'jambon', ''),
    ('1 verre de vin blanc', 1, 'verre', 'vin blanc', ''),
    ('1 noisette de beurre', 1, 'noisette', 'beurre', ''),
    ("1 filet d'huile d'olive", 1, 'filet', "huile d'olive", ''),
    ('2 filets de poulet', 2, None, 'filets de poulet', ''),
    ('1 boîte de tomates pelées', 1, 'boîte', 'tomates', 'pelées'),
    ('20 cl de crème liquide', 20, 'cl', 'crème liquide', ''),
    ('1 l de lait', 1, 'l', 'lait', ''),
    ('100 g de beurre mou', 100, 'g', 'beurre', 'mou'),
    ('1 oignon jaune, haché finement', 1, None, 'oignon jaune', 'haché finement'),
    ('2 courgettes coupées en dés', 2, None, 'courgettes', 'coupées en dés'),
    ('250 ml de lait de coco', 250, 'ml', 'lait de coco', ''),
    ('6 feuilles de basilic frais', 6, 'feuille', 'basilic', 'frais'),
    ('1 1/2 tasse de riz', 1.5, 'tasse', 'riz', ''),
    ('Farine 200 g', 200, 'g', 'Farine', ''),
    ('3 œufs', 3, None, 'œufs', ''),
    ('1 cube de bouillon de légumes', 1, 'cube', 'bouillon de légumes', ''),
    ('50 g de parmesan râpé', 50, 'g', 'parmesan', 'râpé'),
]


@pytest.mark.parametrize('line,amount,unit,food,note', LINES)
def test_french_lines(line, amount, unit, food, note):
    parser = IngredientParser(None, ignore_automations=True)
    with translation.override('fr'):
        assert parser.parse(line) == (amount, unit, food, note)


def test_at_least_30_real_lines():
    assert len(LINES) >= 30


def test_other_languages_keep_the_upstream_parser():
    parser = IngredientParser(None, ignore_automations=True)
    with translation.override('en'):
        assert parser.parse('2 large eggs') == (2, 'large', 'eggs', '')


@pytest.fixture
def user_request(space_1, u1_s1):
    return SimpleNamespace(space=space_1, user=auth.get_user(u1_s1))


def test_plural_finds_the_existing_food(space_1, user_request):
    with scopes_disabled():
        Food.objects.create(name='Oignon', space=space_1)
        Food.objects.create(name='Tomate', space=space_1, plural_name='Tomates')
    with scope(space=space_1), translation.override('fr'):
        parser = IngredientParser(user_request, cache_mode=False)
        assert parser.parse('3 oignons émincés')[2] == 'Oignon'
        assert parser.parse('2 tomates bien mûres')[2] == 'Tomate'
        ingredient = parser.parse_as_ingredient('2 oignons rouges')  # extra word: a different food, created
        assert ingredient.food.name == 'oignons rouges'


def test_automations_still_apply_on_the_cleaned_text(space_1, user_request):
    with scopes_disabled():
        Automation.objects.create(type=Automation.FOOD_ALIAS, param_1='ail', param_2='Ail rose', space=space_1, created_by=user_request.user)
    with scope(space=space_1), translation.override('fr'):
        parser = IngredientParser(user_request, cache_mode=False)
        assert parser.parse("2 gousses d'ail")[2] == 'Ail rose'


def test_parser_api_in_french(space_1, u1_s1):
    with scopes_disabled():
        Food.objects.create(name='Courgette', space=space_1)
    with translation.override('fr'):  # LocaleMiddleware (Accept-Language) is off in the test settings
        response = u1_s1.post('/api/ingredient-parser/post/', {'ingredients': ['2 courgettes coupées en dés', '1 c. à soupe de sucre']},
                              content_type='application/json')
    assert response.status_code == 200, response.content
    first, second = response.json()['ingredients']
    assert first['food']['name'] == 'Courgette' and first['note'] == 'coupées en dés' and first['unit'] is None
    assert second['unit']['name'] == 'c. à soupe' and second['food']['name'] == 'sucre'


def test_url_import_in_french(space_1, u1_s1):
    html = '<script type="application/ld+json">' + json.dumps({
        '@context': 'https://schema.org', '@type': 'Recipe', 'name': 'Soupe',
        'recipeIngredient': ['3 poireaux émincés', "2 c. à soupe d'huile d'olive"],
        'recipeInstructions': [{'@type': 'HowToStep', 'text': 'Cuire.'}],
    }) + '</script>'
    with translation.override('fr'):
        response = u1_s1.post(reverse('api_recipe_from_source'), {'data': html}, content_type='application/json')
    assert response.status_code == 200, response.content
    ingredients = response.json()['recipe']['steps'][0]['ingredients']
    assert ingredients[0]['food']['name'] == 'poireaux' and ingredients[0]['note'] == 'émincés' and ingredients[0]['unit'] is None
    assert ingredients[1]['unit']['name'] == 'c. à soupe' and ingredients[1]['food']['name'] == "huile d'olive"


def test_shopping_free_text_in_french(space_1, u1_s1):
    with scopes_disabled():
        Food.objects.create(name='Citron', space=space_1)
    with translation.override('fr'):
        response = u1_s1.post('/api/ingredient-parser/post/', {'ingredient': '2 citrons'}, content_type='application/json')
    assert response.json()['ingredient']['food']['name'] == 'Citron'


def test_wizard_parse_creates_nothing(space_1, u1_s1):
    with scopes_disabled():
        Food.objects.create(name='Oignon', space=space_1)
        before = Food.objects.filter(space=space_1).count()
    with translation.override('fr'):
        response = u1_s1.post(reverse('kitchen:parse'), {'lines': ['3 oignons émincés', '200 g de farine T55', '']},
                              content_type='application/json')
    assert response.status_code == 200, response.content
    first, second, empty = response.json()['results']
    assert first['food'] == 'Oignon' and first['food_id'] is not None and first['note'] == 'émincés'
    assert second['food'] == 'farine' and second['food_id'] is None and second['unit'] == 'g'
    assert empty['food'] is None
    with scopes_disabled():
        assert Food.objects.filter(space=space_1).count() == before


@pytest.mark.parametrize('line,amount,unit,food,note', [
    ('1 ½ c. à soupe de sucre', 1.5, 'c. à soupe', 'sucre', ''),
    ("2 ½ cuillères à soupe d'huile", 2.5, 'c. à soupe', 'huile', ''),
    ('1 pâte à tarte', 1, None, 'pâte à tarte', ''),
    ('2 c. à soupe de lait en poudre', 2, 'c. à soupe', 'lait en poudre', ''),
    ('1 poulet au curry', 1, None, 'poulet au curry', ''),
    ('50 g de beurre en pommade', 50, 'g', 'beurre', 'en pommade'),
    ('Noisettes concassées', 0, None, 'Noisettes', 'concassées'),
])
def test_review_cases(line, amount, unit, food, note):
    parser = IngredientParser(None, ignore_automations=True)
    with translation.override('fr'):
        assert parser.parse(line) == (amount, unit, food, note)


def test_long_line_note_is_truncated():
    parser = IngredientParser(None, ignore_automations=True)
    with translation.override('fr'):
        amount, unit, food, note = parser.parse('1 ' + 'tomate ' * 70)
    assert len(food) <= 128 and len(note) <= 256


def test_parse_view_rejects_non_object(u1_s1):
    assert u1_s1.post(reverse('kitchen:parse'), ['x'], content_type='application/json').status_code == 400
