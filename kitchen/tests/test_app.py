from django.apps import apps


def test_kitchen_app_is_installed():
    config = apps.get_app_config('kitchen')
    assert config.name == 'kitchen'
