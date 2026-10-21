import io
from unittest import mock

import pytest
from django.contrib import auth
from django.core.files.base import ContentFile
from django.urls import reverse
from django_scopes import scopes_disabled
from PIL import Image

from cookbook.models import Recipe


def png(width, height, color=(200, 80, 40)):
    out = io.BytesIO()
    Image.new('RGB', (width, height), color).save(out, 'PNG')
    return out.getvalue()


@pytest.fixture
def recipe(space_1, u1_s1):
    with scopes_disabled():
        r = Recipe.objects.create(name='Curry', created_by=auth.get_user(u1_s1), space=space_1)
        r.image.save('photo.png', ContentFile(png(800, 600)), save=True)
    return r


def stored_size(recipe):
    with scopes_disabled():
        recipe.refresh_from_db()
        with recipe.image.open('rb') as f:
            return Image.open(io.BytesIO(f.read())).size


def test_crop_the_current_photo(recipe, u1_s1):
    response = u1_s1.put(reverse('kitchen:recipe-image', args=[recipe.id]), {'crop': {'x': 0.25, 'y': 0, 'w': 0.5, 'h': 0.5}},
                         content_type='application/json')
    assert response.status_code == 200, response.content
    assert stored_size(recipe) == (400, 300)
    assert response.json()['image'].endswith('.jpeg')


def test_crop_an_imported_photo_from_its_url(recipe, u1_s1):
    fake = mock.Mock(content=png(3200, 1800))
    with mock.patch('kitchen.images.safe_request', return_value=fake) as get:
        response = u1_s1.put(reverse('kitchen:recipe-image', args=[recipe.id]),
                             {'image_url': 'https://example.org/photo.jpg', 'crop': {'x': 0, 'y': 0, 'w': 1, 'h': 1}},
                             content_type='application/json')
    assert response.status_code == 200, response.content
    get.assert_called_once()
    assert stored_size(recipe) == (1600, 900)  # width capped, ratio kept


@pytest.mark.parametrize('crop', [{}, {'x': 0.5, 'y': 0, 'w': 0.8, 'h': 1}, {'x': 0, 'y': 0, 'w': 0, 'h': 1}, {'x': 'a', 'y': 0, 'w': 1, 'h': 1}])
def test_bad_crop_is_refused(recipe, u1_s1, crop):
    response = u1_s1.put(reverse('kitchen:recipe-image', args=[recipe.id]), {'crop': crop}, content_type='application/json')
    assert response.status_code == 400
    assert stored_size(recipe) == (800, 600)


def test_other_space_cannot_crop(recipe, u1_s2):
    response = u1_s2.put(reverse('kitchen:recipe-image', args=[recipe.id]), {'crop': {'x': 0, 'y': 0, 'w': 1, 'h': 1}},
                         content_type='application/json')
    assert response.status_code == 404
