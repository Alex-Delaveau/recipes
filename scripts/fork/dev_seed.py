"""Seed a small, realistic dataset for local/cloud development and UI screenshots.

Usage (from repo root):
    DJANGO_SETTINGS_MODULE=recipes.settings uv run python scripts/fork/dev_seed.py

Idempotent: running it twice does not duplicate data.
Creates user `demo` / password `demo` (superuser) with an active, fully set-up space.
"""
import os
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "recipes.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django_scopes import scopes_disabled  # noqa: E402

from cookbook.helper.permission_helper import create_space_for_user  # noqa: E402
from cookbook.models import Food, Ingredient, Keyword, Recipe, Step, SupermarketCategory, Unit, UserSpace  # noqa: E402

USERNAME = "demo"
PASSWORD = "demo"
SPACE_NAME = "Cuisine démo"

CATEGORIES = ["Fruits & légumes", "Crèmerie", "Épicerie salée", "Boucherie", "Surgelés"]

# name -> (category, parent)
FOODS = {
    "Légumes": ("Fruits & légumes", None),
    "Courgette": ("Fruits & légumes", "Légumes"),
    "Poivron": ("Fruits & légumes", "Légumes"),
    "Oignon": ("Fruits & légumes", "Légumes"),
    "Ail": ("Fruits & légumes", "Légumes"),
    "Citron": ("Fruits & légumes", None),
    "Œuf": ("Crèmerie", None),
    "Crème fraîche": ("Crèmerie", None),
    "Parmesan": ("Crèmerie", None),
    "Pâtes": ("Épicerie salée", None),
    "Riz basmati": ("Épicerie salée", None),
    "Pois chiches": ("Épicerie salée", None),
    "Lait de coco": ("Épicerie salée", None),
    "Huile d'olive": ("Épicerie salée", None),
    "Curry en poudre": ("Épicerie salée", None),
    "Blanc de poulet": ("Boucherie", None),
    "Lardons": ("Boucherie", None),
}

UNITS = ["g", "ml", "c. à soupe", "c. à café", "pièce"]

RECIPES = [
    {
        "name": "Pâtes carbonara",
        "description": "La version rapide du soir, sans crème.",
        "servings": 2, "working_time": 10, "waiting_time": 10,
        "keywords": ["Rapide", "Pâtes"],
        "steps": [
            ("Cuire les pâtes", "Cuire les pâtes dans une grande casserole d'eau salée.", [("Pâtes", 200, "g")]),
            ("Préparer la sauce", "Faire revenir les lardons. Mélanger œufs et parmesan, puis hors du feu enrober les pâtes.",
             [("Lardons", 150, "g"), ("Œuf", 2, "pièce"), ("Parmesan", 40, "g")]),
        ],
    },
    {
        "name": "Curry de pois chiches",
        "description": "Végétarien, une seule poêle.",
        "servings": 3, "working_time": 15, "waiting_time": 20,
        "keywords": ["Végétarien", "Poêle"],
        "steps": [
            ("Base", "Faire suer l'oignon et l'ail dans l'huile, ajouter le curry.",
             [("Oignon", 1, "pièce"), ("Ail", 2, "pièce"), ("Huile d'olive", 1, "c. à soupe"), ("Curry en poudre", 2, "c. à café")]),
            ("Mijoter", "Ajouter pois chiches et lait de coco, laisser mijoter 15 min.",
             [("Pois chiches", 400, "g"), ("Lait de coco", 400, "ml")]),
            ("Servir", "Servir avec le riz et un trait de citron.", [("Riz basmati", 150, "g"), ("Citron", 1, "pièce")]),
        ],
    },
    {
        "name": "Poulet citron à l'air fryer",
        "description": "Sans four : air fryer 200 °C.",
        "servings": 2, "working_time": 10, "waiting_time": 18,
        "keywords": ["Air fryer", "Rapide"],
        "steps": [
            ("Mariner", "Mélanger poulet, huile, ail et zeste de citron.",
             [("Blanc de poulet", 300, "g"), ("Huile d'olive", 1, "c. à soupe"), ("Ail", 1, "pièce"), ("Citron", 1, "pièce")]),
            ("Cuire", "Air fryer 200 °C pendant 16 à 18 min, en retournant à mi-cuisson.", []),
        ],
    },
    {
        "name": "Poêlée de courgettes et poivrons",
        "description": "Accompagnement de saison.",
        "servings": 2, "working_time": 10, "waiting_time": 12,
        "keywords": ["Végétarien", "Poêle"],
        "steps": [
            ("Cuire", "Faire sauter courgette, poivron et oignon à feu vif dans l'huile.",
             [("Courgette", 2, "pièce"), ("Poivron", 1, "pièce"), ("Oignon", 1, "pièce"), ("Huile d'olive", 2, "c. à soupe")]),
        ],
    },
]


def main():
    User = get_user_model()
    with scopes_disabled():
        user, created = User.objects.get_or_create(username=USERNAME, defaults={"email": "demo@example.com"})
        user.is_superuser = True
        user.is_staff = True
        user.set_password(PASSWORD)
        user.save()

        user_space = UserSpace.objects.filter(user=user, space__name=SPACE_NAME).first()
        if user_space is None:
            user_space = create_space_for_user(user, name=SPACE_NAME)
        UserSpace.objects.filter(user=user).exclude(pk=user_space.pk).update(active=False)
        user_space.active = True
        user_space.save()
        space = user_space.space
        space.space_setup_completed = True
        space.save()

        cats = {name: SupermarketCategory.objects.get_or_create(name=name, space=space)[0] for name in CATEGORIES}
        units = {name: Unit.objects.get_or_create(name=name, space=space)[0] for name in UNITS}

        foods = {}
        for name, (cat, parent) in FOODS.items():  # parents are declared before children
            food = Food.objects.filter(name=name, space=space).first()
            if food is None:
                kwargs = {"name": name, "space": space, "supermarket_category": cats[cat]}
                food = foods[parent].add_child(**kwargs) if parent else Food.add_root(**kwargs)
            foods[name] = food

        for data in RECIPES:
            if Recipe.objects.filter(name=data["name"], space=space).exists():
                continue
            recipe = Recipe.objects.create(
                name=data["name"], description=data["description"], servings=data["servings"],
                working_time=data["working_time"], waiting_time=data["waiting_time"],
                created_by=user, space=space, internal=True,
            )
            for kw in data["keywords"]:
                keyword = Keyword.objects.filter(name=kw, space=space).first() or Keyword.add_root(name=kw, space=space)
                recipe.keywords.add(keyword)
            for order, (step_name, text, ingredients) in enumerate(data["steps"]):
                step = Step.objects.create(name=step_name, instruction=text, order=order, space=space)
                for i_order, (food_name, amount, unit_name) in enumerate(ingredients):
                    ing = Ingredient.objects.create(food=foods[food_name], unit=units[unit_name], amount=Decimal(amount),
                                                    order=i_order, space=space)
                    step.ingredients.add(ing)
                recipe.steps.add(step)

        print(f"seed ok: user={USERNAME}/{PASSWORD} space='{space.name}' "
              f"foods={Food.objects.filter(space=space).count()} recipes={Recipe.objects.filter(space=space).count()}")


if __name__ == "__main__":
    main()
