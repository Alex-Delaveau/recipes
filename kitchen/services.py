"""Aisle organisation of the fork: generic aisle order, aisle suggestion for new foods, families, duplicates."""
from django.db import transaction
from django.db.models import Count, Q
from django_scopes import scopes_disabled

from cookbook.models import Food, Ingredient, ShoppingListEntry, Supermarket, SupermarketCategory, SupermarketCategoryRelation
from kitchen.aisles import GENERIC_AISLES, GENERIC_SUPERMARKET_NAME, match_generic_key, suggest_aisle_key
from kitchen.models import KitchenFood, KitchenSpace, NotDuplicate
from kitchen.names import closest, normalize, similarity


# ---------------------------------------------------------------- generic aisle order

@transaction.atomic
def ensure_setup(space):
    """
    Idempotent: makes sure the space has the generic aisles (existing categories with a matching name are reused,
    e.g. "Crèmerie" stands for "Frais") and the "Ordre générique" supermarket that orders them. Categories that match
    no generic aisle are kept, after the generic ones. Returns the KitchenSpace.
    """
    with scopes_disabled():
        kitchen, _ = KitchenSpace.objects.get_or_create(space=space)
        supermarket = kitchen.generic_supermarket
        if supermarket is not None and supermarket.space_id == space.id:
            return kitchen

        categories = list(SupermarketCategory.objects.filter(space=space).order_by('name'))
        by_key = {}
        for category in categories:
            key = match_generic_key(category.name)
            if key and key not in by_key:
                by_key[key] = category
        ordered = []
        for key, display, _others in GENERIC_AISLES:
            category = by_key.get(key) or SupermarketCategory.objects.create(name=display, space=space)
            ordered.append(category)
        ordered += [c for c in categories if c not in ordered]

        supermarket = Supermarket.objects.filter(space=space, name=GENERIC_SUPERMARKET_NAME).first()
        if supermarket is None:
            supermarket = Supermarket.objects.create(space=space, name=GENERIC_SUPERMARKET_NAME,
                                                     description='Ordre de rayons générique du fork (réglable).')
        existing = set(SupermarketCategoryRelation.objects.filter(supermarket=supermarket).values_list('category_id', flat=True))
        next_order = SupermarketCategoryRelation.objects.filter(supermarket=supermarket).count()
        for category in ordered:
            if category.id not in existing:
                SupermarketCategoryRelation.objects.create(supermarket=supermarket, category=category, order=next_order)
                next_order += 1
        kitchen.generic_supermarket = supermarket
        kitchen.save()
        return kitchen


def ordered_aisles(space):
    """Categories of the space in the generic order (categories created later come last, alphabetically)."""
    kitchen = ensure_setup(space)
    relations = SupermarketCategoryRelation.objects.filter(supermarket=kitchen.generic_supermarket).select_related('category').order_by('order', 'id')
    ordered = [r.category for r in relations]
    known = {c.id for c in ordered}
    ordered += list(SupermarketCategory.objects.filter(space=space).exclude(id__in=known).order_by('name'))
    return ordered


@transaction.atomic
def set_aisle_order(space, category_ids):
    kitchen = ensure_setup(space)
    supermarket = kitchen.generic_supermarket
    categories = {c.id: c for c in SupermarketCategory.objects.filter(space=space, id__in=category_ids)}
    for order, category_id in enumerate(category_ids):
        category = categories.get(category_id)
        if category is None:
            continue
        SupermarketCategoryRelation.objects.update_or_create(supermarket=supermarket, category=category,
                                                             defaults={'order': order})
    return ordered_aisles(space)


# ---------------------------------------------------------------- aisle suggestion

def generic_category(space, key):
    """Category standing for a generic aisle key in this space (only once the space is set up)."""
    for category in SupermarketCategory.objects.filter(space=space):
        if match_generic_key(category.name) == key:
            return category
    return None


def suggest_aisle(food):
    """
    Aisle suggestion for a food, in the order of SPEC.md: the family's aisle, then the fork's French dictionary,
    then the aisle of an existing food with a close name. Returns (category or None, source).
    """
    parent = food.get_parent() if food.depth and food.depth > 1 else None
    if parent is not None and parent.supermarket_category_id:
        return parent.supermarket_category, KitchenFood.SOURCE_PARENT

    space = food.space
    if KitchenSpace.objects.filter(space=space, generic_supermarket__isnull=False).exists():
        key = suggest_aisle_key(food.name)
        if key:
            category = generic_category(space, key)
            if category is not None:
                return category, KitchenFood.SOURCE_DICTIONARY

    candidates = Food.objects.filter(space=space, supermarket_category__isnull=False).exclude(id=food.id).values_list('id', 'name', 'supermarket_category_id')
    categories = {fid: cid for fid, _name, cid in candidates}
    match = closest(food.name, [(fid, name) for fid, name, _cid in candidates])
    if match:
        return SupermarketCategory.objects.filter(id=categories[match[0]]).first(), KitchenFood.SOURCE_SIMILAR
    return None, KitchenFood.SOURCE_NONE


def on_food_created(food):
    """
    Called for every new food, whatever creates it (import, typing, shopping list): the suggested aisle is applied
    right away so the shopping list is sorted, and the food joins the "to sort" queue until the user confirms it.
    A food created with an aisle (chosen by the user, open data) counts as confirmed.
    """
    with scopes_disabled():
        if KitchenFood.objects.filter(food=food).exists():
            return
        if food.supermarket_category_id:
            KitchenFood.objects.create(food=food, space=food.space, aisle_source=KitchenFood.SOURCE_USER, aisle_confirmed=True)
            return
        category, source = suggest_aisle(food)
        KitchenFood.objects.create(food=food, space=food.space, aisle_source=source, aisle_confirmed=False)
        if category is not None:
            # queryset update: no save signal, upstream inheritance and search fields stay untouched
            Food.objects.filter(id=food.id).update(supermarket_category=category)
            food.supermarket_category = category


def kitchen_food(food):
    obj, _ = KitchenFood.objects.get_or_create(food=food, defaults={
        'space': food.space, 'aisle_confirmed': food.supermarket_category_id is not None,
        'aisle_source': KitchenFood.SOURCE_USER if food.supermarket_category_id else KitchenFood.SOURCE_NONE,
        'is_family': food.depth == 1 and food.numchild > 0,
    })
    return obj


@transaction.atomic
def set_food_aisle(food, category):
    """The user picks (or confirms) an aisle. A family passes it on to its members that follow it."""
    previous = food.supermarket_category_id
    Food.objects.filter(id=food.id).update(supermarket_category=category)
    food.supermarket_category = category
    state = kitchen_food(food)
    state.aisle_confirmed = True
    state.aisle_source = KitchenFood.SOURCE_USER
    state.save()
    if food.numchild:
        # members (any depth) follow the family (inheritance by default), except those whose own aisle the user chose
        followers = list(food.get_descendants().filter(
            Q(supermarket_category_id=previous) | Q(supermarket_category__isnull=True) | Q(kitchen__aisle_confirmed=False)
            | Q(kitchen__aisle_source=KitchenFood.SOURCE_PARENT)).values_list('id', flat=True))
        Food.objects.filter(id__in=followers).update(supermarket_category=category)
        for follower in Food.objects.filter(id__in=followers):
            KitchenFood.objects.update_or_create(food=follower, defaults={'space': food.space, 'aisle_confirmed': True,
                                                                           'aisle_source': KitchenFood.SOURCE_PARENT})
    return food


def to_sort_queryset(space):
    """Foods whose aisle the user has not confirmed yet (new foods, or older foods without an aisle)."""
    return Food.objects.filter(space=space, ignore_shopping=False).filter(
        Q(kitchen__isnull=True, supermarket_category__isnull=True) | Q(kitchen__aisle_confirmed=False)
    ).order_by('name')


# ---------------------------------------------------------------- families (2-level tree)

def is_family(food):
    if food.depth != 1:
        return False
    if food.numchild > 0:
        return True
    return KitchenFood.objects.filter(food=food, is_family=True).exists()


def _node_location():
    # same rule as the upstream move endpoint (TreeMixin.move)
    return 'sorted' if Food.node_order_by else 'last'


@transaction.atomic
def move_to_family(food, family):
    """
    Moves a food into a family (or to the top level when family is None). It takes the family's aisle, as members
    inherit the family's aisle by default.
    """
    if family is not None:
        if family.id == food.id or family.space_id != food.space_id:
            raise ValueError('invalid family')
        if family.depth != 1:
            family = family.get_root()
        with scopes_disabled():
            food.move(family, f'{_node_location()}-child')
        state = kitchen_food(family)
        if not state.is_family:
            state.is_family = True
            state.save()
        food.refresh_from_db()
        if family.supermarket_category_id:
            Food.objects.filter(id=food.id).update(supermarket_category=family.supermarket_category_id)
            KitchenFood.objects.update_or_create(food=food, defaults={'space': food.space, 'aisle_confirmed': True,
                                                                       'aisle_source': KitchenFood.SOURCE_PARENT})
    else:
        if food.depth > 1:
            with scopes_disabled():
                food.move(Food.get_first_root_node(), f'{_node_location()}-sibling')
    food.refresh_from_db()
    return food


# ---------------------------------------------------------------- duplicates

def usage_counts(food_ids):
    """recipes and shopping entries using each food: {id: (recipes, shopping entries)}"""
    recipes = dict(Ingredient.objects.filter(food_id__in=food_ids).values('food_id')
                   .annotate(n=Count('step__recipe', distinct=True)).values_list('food_id', 'n'))
    shopping = dict(ShoppingListEntry.objects.filter(food_id__in=food_ids).values('food_id')
                    .annotate(n=Count('id')).values_list('food_id', 'n'))
    return {i: (recipes.get(i, 0), shopping.get(i, 0)) for i in food_ids}


def find_duplicates(space, limit=200):
    """
    Probable duplicates among the foods of a space: names that match by the similarity rule (plural, accents, extra
    words, spelling), minus the pairs marked "not a duplicate". Matches are grouped (oignons ~ Oignon ~ Oignon jaune)
    and every other food of a group is proposed for a merge into one food to keep: the most used, then the shortest
    name. So no proposal targets a food that is itself proposed for a merge.
    Returns a list of dicts sorted by score: {keep, drop, score, reason}.
    """
    foods = list(Food.objects.filter(space=space).values_list('id', 'name'))
    dismissed = set(NotDuplicate.objects.filter(space=space).values_list('food_a_id', 'food_b_id'))
    keys = {fid: normalize(name) for fid, name in foods}
    names = dict(foods)
    edges = []
    for i, (id_a, name_a) in enumerate(foods):
        for id_b, name_b in foods[i + 1:]:
            ka, kb = keys[id_a], keys[id_b]
            if not ka or not kb or (ka[0] != kb[0] and ka.split()[0] not in kb and kb.split()[0] not in ka):
                continue  # cheap pre-filter: names starting differently and sharing no first word
            score, reason = similarity(name_a, name_b)
            if reason and (min(id_a, id_b), max(id_a, id_b)) not in dismissed:
                edges.append((score, reason, id_a, id_b))

    # groups of matching foods (union-find)
    parent = {}

    def root(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for _score, _reason, a, b in edges:
        parent[root(a)] = root(b)
    groups = {}
    for fid in parent:
        groups.setdefault(root(fid), []).append(fid)

    counts = usage_counts(list(parent))
    best_edge = {}
    for score, reason, a, b in edges:
        for x in (a, b):
            if x not in best_edge or score > best_edge[x][0]:
                best_edge[x] = (score, reason)

    result = []
    for members in groups.values():
        keep = sorted(members, key=lambda x: (-sum(counts[x]), len(names[x]), names[x]))[0]
        for drop in members:
            if drop == keep or (min(keep, drop), max(keep, drop)) in dismissed:
                continue
            score, reason = similarity(names[drop], names[keep])
            if not reason:  # only linked through another member of the group: say so
                score, reason = best_edge[drop][0] * 0.9, 'group'
            result.append({
                'keep': {'id': keep, 'name': names[keep], 'recipes': counts[keep][0], 'shopping': counts[keep][1]},
                'drop': {'id': drop, 'name': names[drop], 'recipes': counts[drop][0], 'shopping': counts[drop][1]},
                'score': score, 'reason': reason,
            })
    result.sort(key=lambda p: -p['score'])
    return result[:limit]


def names_to_fix(space, limit=500):
    """
    Foods whose name kept a piece of an ingredient line ("à soupe d'huile", "d'eau + 30 ml"), with the fix:
    - `target`: an existing food with the clean name (plural, case and accents aside): merge into it;
    - otherwise rename to `clean`. Several foods cleaning to the same new name: the most used is renamed, the others
      are merged into it (their target is that food, `target.renamed` is true).
    """
    from kitchen.french import clean_food_name
    foods = list(Food.objects.filter(space=space).values_list('id', 'name', 'plural_name'))
    dirty = {}
    for fid, name, _plural in foods:
        clean = clean_food_name(name)
        if clean != name and normalize(clean):
            dirty[fid] = (name, clean)
    if not dirty:
        return []
    existing = {}
    for fid, name, plural in foods:
        if fid in dirty:
            continue
        for n in (name, plural):
            if n:
                existing.setdefault(normalize(n), (fid, name))
    counts = usage_counts(list(dirty))
    renamed = {}  # normalized clean name -> (id, clean name) of the food renamed to it
    result = []
    for fid in sorted(dirty, key=lambda x: (-sum(counts[x]), dirty[x][0])):
        name, clean = dirty[fid]
        key = normalize(clean)
        target = None
        if key in existing:
            target = {'id': existing[key][0], 'name': existing[key][1], 'renamed': False}
        elif key in renamed:
            target = {'id': renamed[key][0], 'name': renamed[key][1], 'renamed': True}
        else:
            renamed[key] = (fid, clean)
        result.append({'id': fid, 'name': name, 'clean': clean, 'target': target,
                       'recipes': counts[fid][0], 'shopping': counts[fid][1]})
    # renames first, so that the merges into a renamed food find it under its new name
    result.sort(key=lambda r: (r['target'] is not None, r['clean'].lower()))
    return result[:limit]


def dismiss_duplicate(space, id_a, id_b):
    a, b = min(id_a, id_b), max(id_a, id_b)
    NotDuplicate.objects.get_or_create(space=space, food_a_id=a, food_b_id=b)


def closest_food(space, name, exclude_id=None):
    """Existing food closest to a name (import review), or None: {id, name, score, reason}."""
    candidates = Food.objects.filter(space=space)
    if exclude_id:
        candidates = candidates.exclude(id=exclude_id)
    exact = candidates.filter(name__iexact=name.strip()).first()
    if exact:
        return {'id': exact.id, 'name': exact.name, 'score': 1.0, 'reason': 'exact'}
    match = closest(name, candidates.values_list('id', 'name'))
    if not match:
        return None
    food = candidates.get(id=match[0])
    return {'id': food.id, 'name': food.name, 'score': match[1], 'reason': match[2]}
