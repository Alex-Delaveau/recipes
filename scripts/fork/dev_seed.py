"""Seed a small, realistic dataset for local/cloud development and UI screenshots.

Usage (from repo root):
    DJANGO_SETTINGS_MODULE=recipes.settings uv run python scripts/fork/dev_seed.py

Idempotent: running it twice does not duplicate data.
Creates user `demo` / password `demo` (superuser) with an active, fully set-up space.
"""
import io
import math
import os
import random
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "recipes.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from django.utils import timezone  # noqa: E402
from django_scopes import scopes_disabled  # noqa: E402

from cookbook.helper.permission_helper import create_space_for_user  # noqa: E402
from cookbook.models import (CookLog, Food, Household, Ingredient, Keyword, Recipe, ShoppingListEntry, Step,  # noqa: E402
                             SupermarketCategory, Unit, UserSpace, ViewLog)

USERNAME = "demo"
PASSWORD = "demo"
SPACE_NAME = "Cuisine démo"
HOUSEHOLD_NAME = "Foyer démo"

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

# names left by imports: duplicates and foods with no confirmed aisle, for the food organisation screens
MESSY_FOODS = ["oignons", "Oignon jaune", "Échalote", "échalotes", "Tomates cerises", "Gingembre frais", "Sauce soja"]

# warm palettes for the generated placeholder photos (no external image service)
PHOTO_COLORS = {
    "Pâtes carbonara": ((236, 205, 140), (196, 140, 70)),
    "Curry de pois chiches": ((230, 160, 60), (170, 90, 30)),
    "Poulet citron à l'air fryer": ((240, 220, 120), (190, 120, 60)),
    "Poêlée de courgettes et poivrons": ((140, 180, 90), (200, 70, 50)),
}

# (food, amount, unit, checked) shopping entries of the household list
SHOPPING = [("Courgette", 3, "pièce", False), ("Citron", 2, "pièce", False), ("Riz basmati", 500, "g", False),
            ("Crème fraîche", 20, "ml", False), ("Parmesan", 100, "g", True), ("Pâtes", 500, "g", False)]


def placeholder_photo(name):
    """A deterministic 'plate seen from above' JPEG, so recipe cards have a photo in screenshots."""
    from PIL import Image, ImageDraw, ImageFilter
    rnd = random.Random(name)
    base, accent = PHOTO_COLORS.get(name, ((220, 200, 170), (170, 110, 70)))
    w, h = 1200, 800
    img = Image.new("RGB", (w, h), (92, 70, 55))
    draw = ImageDraw.Draw(img)
    for y in range(0, h, 40):  # wooden table
        shade = 80 + rnd.randint(0, 25)
        draw.rectangle([0, y, w, y + 38], fill=(shade + 20, shade, shade - 20))
    cx, cy, r = w // 2 + rnd.randint(-60, 60), h // 2, 330
    draw.ellipse([cx - r - 30, cy - r - 30, cx + r + 30, cy + r + 30], fill=(245, 242, 236))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=base)
    for _ in range(60):
        a, d = rnd.uniform(0, 6.28), rnd.uniform(0, r - 50)
        x, y = cx + d * math.cos(a), cy + d * math.sin(a)
        s = rnd.randint(12, 34)
        color = accent if rnd.random() < 0.6 else tuple(min(255, c + 40) for c in base)
        draw.ellipse([x - s, y - s * 0.7, x + s, y + s * 0.7], fill=color)
    img = img.filter(ImageFilter.GaussianBlur(2))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=82)
    return buf.getvalue()

RECIPES = [
    {
        "name": "Pâtes carbonara",
        "description": "La version rapide du soir, sans crème.",
        "servings": 2, "working_time": 10, "waiting_time": 10,
        "keywords": ["Rapide", "Pâtes"],
        "steps": [
            ("Cuire les pâtes", "Cuire {{ scale(200) }} g de pâtes dans une grande casserole d'eau salée.", [("Pâtes", 200, "g")]),
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
            ("Mijoter", "Ajouter {{ scale(400) }} g de pois chiches et {{ scale(400) }} ml de lait de coco, laisser mijoter 15 min.",
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
        space = user_space.space
        # a household is needed for shopping/meal plan sharing; without it the app opens on the household wizard
        household = Household.objects.get_or_create(name=HOUSEHOLD_NAME, space=space)[0]
        user_space.active = True
        user_space.household = household
        user_space.save()
        space.space_setup_completed = True
        space.household_setup_completed = True
        space.save()

        cats = {name: SupermarketCategory.objects.get_or_create(name=name, space=space)[0] for name in CATEGORIES}
        units = {name: Unit.objects.get_or_create(name=name, space=space)[0] for name in UNITS}
        Unit.objects.filter(space=space, name="pièce", plural_name__isnull=True).update(plural_name="pièces")

        from kitchen.services import ensure_setup
        ensure_setup(space)  # generic aisle order of the fork (reuses the categories above)

        foods = {}
        for name, (cat, parent) in FOODS.items():  # parents are declared before children
            food = Food.objects.filter(name=name, space=space).first()
            if food is None:
                kwargs = {"name": name, "space": space, "supermarket_category": cats[cat]}
                food = foods[parent].add_child(**kwargs) if parent else Food.add_root(**kwargs)
            foods[name] = food

        for data in RECIPES:
            existing = Recipe.objects.filter(name=data["name"], space=space).first()
            if existing is not None:
                for order, (_, text, _) in enumerate(data["steps"]):  # keep older dev databases in sync with the texts
                    existing.steps.filter(order=order).exclude(instruction=text).update(instruction=text)
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

        for name in MESSY_FOODS:
            if not Food.objects.filter(name=name, space=space).exists():
                Food.objects.create(name=name, space=space)  # the fork suggests an aisle, left to confirm

        now = timezone.now()
        for i, recipe in enumerate(Recipe.objects.filter(space=space).order_by("id")):
            if not recipe.image:
                recipe.image.save(f"seed_{recipe.id}.jpg", ContentFile(placeholder_photo(recipe.name)), save=True)
            # history for the "recent" and "not cooked for a long time" shortcuts: fixed, relative dates
            if not ViewLog.objects.filter(recipe=recipe, created_by=user).exists() and i < 2:
                log = ViewLog.objects.create(recipe=recipe, created_by=user, space=space)
                ViewLog.objects.filter(pk=log.pk).update(created_at=now - timedelta(days=i + 1))
            if not CookLog.objects.filter(recipe=recipe, created_by=user).exists() and i % 2 == 0:
                CookLog.objects.create(recipe=recipe, created_by=user, space=space, servings=recipe.servings,
                                       created_at=now - timedelta(days=5 + 30 * i))

        if not ShoppingListEntry.objects.filter(space=space).exists():
            for food_name, amount, unit_name, checked in SHOPPING:
                ShoppingListEntry.objects.create(food=foods[food_name], unit=units[unit_name], amount=Decimal(amount),
                                                 checked=checked, completed_at=now if checked else None,
                                                 created_by=user, space=space)

        print(f"seed ok: user={USERNAME}/{PASSWORD} space='{space.name}' "
              f"foods={Food.objects.filter(space=space).count()} recipes={Recipe.objects.filter(space=space).count()}")


if __name__ == "__main__":
    main()
