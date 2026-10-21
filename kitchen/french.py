"""
French ingredient lines for the upstream IngredientParser, without editing cookbook/helper/ingredient_parser.py.

`install()` (called from KitchenConfig.ready) wraps IngredientParser.parse: when the active language is French, lines
are read with French rules, then the upstream automations (UNIT_ALIAS, FOOD_ALIAS...) run as usual. Every caller of
the parser benefits: URL import, multi-line paste in the editor, shopping list free text, the fork's recipe wizard.

French rules:
- units in one or several words, abbreviated or not: "c. à soupe", "càs", "cs", "CS", "cuillère à café", "cc",
  "pincée", "gousse", "sachet", "brin", "botte", "tranche", "verre", "noisette", "filet" (of a liquid)...
- "de / d' / des / du" between the quantity (or unit) and the food are dropped;
- precisions go to the note: "émincés", "T55", "bien mûres", "coupé en dés"...;
- plurals find the existing food: "oignons" -> "Oignon";
- amounts: ½, 1/2, "1,5", "1 1/2", "2-3" / "2 à 3" (first number, range in the note), number words ("une", "deux").
"""
import re
import unicodedata

from django.utils import translation

from kitchen.names import DESCRIPTORS, normalize, strip_accents

# canonical unit name -> spellings (accent-free, lower case, without dots); the canonical name is what gets stored
UNITS = {
    'c. à soupe': ['c a soupe', 'c a s', 'cas', 'cs', 'cuillere a soupe', 'cuilleres a soupe', 'cuillere soupe', 'c soupe', 'cuil a soupe',
                   'cuill a soupe', 'tbsp', 'cs bombee', 'grosse cuillere', 'c s', 'cuilleree a soupe', 'cuillerees a soupe'],
    'c. à café': ['c a cafe', 'c a c', 'cac', 'cc', 'cuillere a cafe', 'cuilleres a cafe', 'cuillere cafe', 'c cafe', 'cuil a cafe', 'cuill a cafe',
                  'tsp', 'petite cuillere', 'cuillere a the', 'c a the', 'c c', 'cuilleree a cafe', 'cuillerees a cafe'],
    'g': ['g', 'gr', 'gramme', 'grammes'],
    'kg': ['kg', 'kilo', 'kilos', 'kilogramme', 'kilogrammes'],
    'mg': ['mg'],
    'ml': ['ml', 'millilitre', 'millilitres'],
    'cl': ['cl', 'centilitre', 'centilitres'],
    'dl': ['dl', 'decilitre', 'decilitres'],
    'l': ['l', 'litre', 'litres'],
    'pincée': ['pincee', 'pincees', 'pince'],
    'gousse': ['gousse', 'gousses'],
    'sachet': ['sachet', 'sachets'],
    'brin': ['brin', 'brins'],
    'botte': ['botte', 'bottes'],
    'bouquet': ['bouquet', 'bouquets'],
    'tranche': ['tranche', 'tranches'],
    'verre': ['verre', 'verres'],
    'tasse': ['tasse', 'tasses'],
    'bol': ['bol', 'bols'],
    'noisette': ['noisette', 'noisettes'],
    'filet': ['filet', 'filets', 'trait', 'traits'],
    'boîte': ['boite', 'boites', 'conserve', 'conserves'],
    'pot': ['pot', 'pots'],
    'cube': ['cube', 'cubes'],
    'feuille': ['feuille', 'feuilles'],
    'poignée': ['poignee', 'poignees'],
    'morceau': ['morceau', 'morceaux'],
    'branche': ['branche', 'branches'],
    'tige': ['tige', 'tiges'],
    'zeste': ['zeste', 'zestes'],
    'paquet': ['paquet', 'paquets'],
    'barquette': ['barquette', 'barquettes'],
    'louche': ['louche', 'louches'],
    'goutte': ['goutte', 'gouttes'],
    'boule': ['boule', 'boules'],
    'rouleau': ['rouleau', 'rouleaux'],
    'cm': ['cm'],
}
# "filet" (and "trait") is a unit only for liquids: "un filet d'huile", but "2 filets de poulet" is a food
LIQUIDS = ('huile', 'vinaigre', 'citron', 'jus', 'lait', 'creme', 'sauce', 'miel', 'sirop', 'eau', 'vin', 'tabasco', 'cognac', 'rhum')

_UNIT_OF = {spelling: canonical for canonical, spellings in UNITS.items() for spelling in spellings}

NUMBER_WORDS = {'un': 1, 'une': 1, 'deux': 2, 'trois': 3, 'quatre': 4, 'cinq': 5, 'six': 6, 'sept': 7, 'huit': 8, 'neuf': 9, 'dix': 10,
                'onze': 11, 'douze': 12, 'quinze': 15, 'vingt': 20, 'demi': 0.5, 'demie': 0.5, 'quelques': None}

_VULGAR = '¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞'
_NUMBER = rf'(?:\d+\s+\d+/\d+|\d+\s+[{_VULGAR}]|\d+/\d+|\d+(?:[.,]\d+)?[{_VULGAR}]?|[{_VULGAR}])'
_AMOUNT = re.compile(rf'^(?P<amount>{_NUMBER})(?:\s*(?:-|à|a|ou)\s*(?P<to>{_NUMBER}))?(?=[\s\w(]|$)\s*', re.IGNORECASE)
_ARTICLE = re.compile(r"^(?:de la |de l['’]|des |du |de |d['’])", re.IGNORECASE)

# words that start a precision: everything from there goes to the note
NOTE_STARTERS = DESCRIPTORS | {
    'bien', 'tres', 'pour', 'coupe', 'coupes', 'coupee', 'coupees', 'taille', 'tailles', 'taillee', 'taillees', 'detaille', 'detailles',
    'decoupe', 'decoupes', 'ecrase', 'ecrases', 'ecrasee', 'ecrasees', 'fondu', 'fondus', 'fondue', 'fondues', 'mou', 'mous', 'pommade',
    'tiede', 'froid', 'froide', 'ramolli', 'ramollie', 'battu', 'battus', 'battue', 'battues', 'concasse', 'concasses', 'concassee',
    'concassees', 'egoutte', 'egouttes', 'egouttee', 'egouttees', 'rince', 'rinces', 'lave', 'laves', 'epluche', 'epluches', 'eplucheees',
    'epluchee', 'epluchees', 'cisele', 'ciseles', 'ciselee', 'ciselees', 'presse', 'presses', 'pressee', 'pressees', 'degerme', 'degermee',
    'degermees', 'environ', 'selon', 'sans', 'type', 'facultatif', 'optionnel', 'ou',
} - {'en', 'des', 'de'}
# prepositions start a precision only before a preparation word: "coupé en dés", "beurre en pommade", but
# "pâte à tarte", "lait en poudre", "poulet au curry" are food names
PREPOSITIONS = {'a', 'au', 'aux', 'en'}
PREPARATIONS = {'des', 'de', 'cube', 'cubes', 'rondelle', 'rondelles', 'lamelle', 'lamelles', 'morceau', 'morceaux', 'tranche',
                'tranches', 'pommade', 'julienne', 'brunoise', 'quartier', 'quartiers', 'fines', 'fins', 'fine', 'fin', 'petits', 'gros',
                'temperature', 'deux', 'quatre', 'huit', 'moitie', 'lanieres', 'batonnets', 'des'}
_FLOUR_TYPE = re.compile(r'^t\d{2,3}$', re.IGNORECASE)


def is_french():
    return (translation.get_language() or '').lower().startswith('fr')


def _key(text):
    """accent-free, lower case, dots and apostrophes as spaces: matching key for unit spellings"""
    text = strip_accents(text.lower())
    text = re.sub(r"[.’']", ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def parse_number(text, parser):
    text = text.strip().replace(',', '.')
    if ' ' in text and text[-1] in _VULGAR:  # "1 ½"
        whole, frac = text.split(None, 1)
        return float(whole) + unicodedata.numeric(frac.strip())
    if ' ' in text and '/' in text:  # "1 1/2"
        whole, frac = text.split(None, 1)
        return float(whole) + parse_number(frac, parser)
    if len(text) == 1 and text in _VULGAR:
        return unicodedata.numeric(text)
    if text and text[-1] in _VULGAR:  # "1½"
        return float(text[:-1]) + unicodedata.numeric(text[-1])
    if '/' in text:
        num, den = text.split('/', 1)
        return float(num) / float(den) if float(den) else 0
    return float(text)


def match_unit(rest):
    """(canonical unit, remaining text) when `rest` starts with a known unit (longest spelling wins), else (None, rest)."""
    best = None
    for i in range(1, min(len(rest), 32) + 1):
        if i < len(rest) and rest[i].isalnum() and rest[i - 1].isalnum():
            continue  # never cut inside a word: "l" is not the start of "lait"
        canonical = _UNIT_OF.get(_key(rest[:i]))
        if canonical:
            best = (canonical, rest[i:].lstrip(" .’'"))
    if best is None:
        return None, rest
    canonical, remaining = best
    if canonical == 'filet' and not _key(_ARTICLE.sub('', remaining)).startswith(LIQUIDS):
        return None, rest
    return canonical, remaining.strip()


def split_note(food_text):
    """'tomates bien mûres' -> ('tomates', 'bien mûres'); 'farine T55' -> ('farine', 'T55'); commas and parentheses too."""
    note_parts = []
    m = re.search(r'\(([^)]*)\)', food_text)
    if m:
        note_parts.append(m.group(1).strip())
        food_text = (food_text[:m.start()] + food_text[m.end():]).strip()
    if ',' in food_text:
        food_text, extra = food_text.split(',', 1)
        note_parts.insert(0, extra.strip())
    words = food_text.split()
    cut = len(words)
    for i, w in enumerate(words):
        k = _key(w)
        if i == 0:
            continue
        if k in PREPOSITIONS:
            following = _key(words[i + 1]) if i + 1 < len(words) else ''
            if following in PREPARATIONS or following in NOTE_STARTERS:
                cut = i
                break
            continue
        if k in NOTE_STARTERS or _FLOUR_TYPE.match(k):
            cut = i
            break
    food = ' '.join(words[:cut]).strip(' ,;:-')
    precision = ' '.join(words[cut:]).strip(' ,;:-')
    note = ', '.join(p for p in [precision] + note_parts if p)
    return food, note


class ExistingFoods:
    """normalized name -> existing food name of the space, to bring plurals and variants back to the existing food"""

    def __init__(self, space):
        self.space = space
        self._map = None

    def find(self, name):
        if self.space is None:
            return None
        if self._map is None:
            from cookbook.models import Food
            self._map = {}
            for food_name, plural in Food.objects.filter(space=self.space).values_list('name', 'plural_name'):
                for n in (food_name, plural):
                    if n:
                        self._map.setdefault(normalize(n), food_name)
        return self._map.get(normalize(name))


def parse_french(parser, text):
    """
    French reading of one ingredient line. Returns (amount, unit, food, note) like IngredientParser.parse, before the
    upstream unit/food automations (applied by the caller).
    """
    line = re.sub(r'\s+', ' ', text.strip())
    line = re.sub(r'^[,.\-_=+#*|\\/•]+\s*', '', line)
    amount, note_parts, unit = 0, [], None

    # "Farine 200 g": quantity written after the food
    trailing = re.match(rf'^(?P<food>\D+?)\s+(?P<qty>{_NUMBER}\s*\S*)$', line)
    if trailing and not _AMOUNT.match(line) and match_unit(re.sub(rf'^{_NUMBER}\s*', '', trailing.group('qty')))[0]:
        line = f"{trailing.group('qty')} {trailing.group('food')}"

    m = _AMOUNT.match(line)
    if m:
        amount = parse_number(m.group('amount'), parser)
        if m.group('to'):
            note_parts.append(f"{m.group('amount')}-{m.group('to')}")
        rest = line[m.end():]
        # "200g" glued: the unit follows without a space
        glued = re.match(r'^([a-zA-Zàâçéèêëîïôûùüÿœ.]+)(?=\s|$)', rest) if rest and not line[m.end() - 1].isspace() else None
        if glued is not None and match_unit(glued.group(1))[0]:
            unit, _ = match_unit(glued.group(1))
            rest = rest[glued.end():].strip()
    else:
        first, _, after = line.partition(' ')
        word = _key(first)
        if word in NUMBER_WORDS and after:
            amount = NUMBER_WORDS[word] or 0
            rest = after
            if word in ('une', 'un') and _key(after).startswith('demi'):  # "une demi botte"
                amount = 0.5
                rest = after.split(' ', 1)[1] if ' ' in after else after
        else:
            rest = line

    if unit is None and rest is not line:
        # a unit only follows a quantity: "Noisettes concassées" is a food, not 2 "noisette" units
        unit, rest = match_unit(rest)
    rest = _ARTICLE.sub('', rest.strip()).strip()
    extra = _EXTRA_AMOUNT.search(rest)
    if extra:
        note_parts.append(extra.group(0).strip())
        rest = rest[:extra.start()].strip()
    food, note = split_note(rest)
    if note:
        note_parts.append(note)
    if not food:
        raise ValueError('no food in line')

    existing = parser._kitchen_foods.find(food) if hasattr(parser, '_kitchen_foods') else None
    if existing:
        food = existing
    return float(amount), unit, food, ', '.join(note_parts)[:256]


# "+ 30 ml", "+ 1 c. à soupe" after the food: a second quantity, never part of the name
_EXTRA_AMOUNT = re.compile(rf'\s*\+\s*{_NUMBER}.*$')
# what an old import left in front of a food name: the end of "c. à soupe", "cuillère à café"...
# a quantity followed by a space (never "100% cacao")
_LEADING_AMOUNT = re.compile(rf'^{_NUMBER}(?=\s)\s*')
_UNIT_LEFTOVER = re.compile(r'^(?:(?:c\.?|cuill[eè]re?s?|cuiller[ée]es?)\s*)?(?:à|a)\s+(?:soupe|caf[ée]|th[ée])\b\.?\s*'
                            r'(?:(?:ras|rases?|bomb[ée]e?s?|pleines?)\b\s*)?', re.IGNORECASE)


def clean_food_name(name):
    """
    Food name without what an import left around it: "à café coriandre en poudre" -> "coriandre en poudre",
    "à soupe d'huile" -> "huile", "d'eau + 30 ml" -> "eau", "200 g de farine" -> "farine". Returns the name unchanged
    when there is nothing to remove. Careful with real names: "4 épices", "7 Up", "100% cacao", "Du Barry" stay, and
    descriptions such as "en poudre" stay too (they make a different food).
    """
    text = re.sub(r'\s+', ' ', str(name)).strip()
    # a lower case leading article is a leftover ("de la crème"); a capital one is part of a name ("Du Barry")
    removed = bool(re.match(r"^(?:de la |de l['’]|des |du |de |d['’])", text))
    for _ in range(3):  # "2 c. à soupe de ..." needs several passes
        before = text
        text = _EXTRA_AMOUNT.sub('', text).strip()
        text = _UNIT_LEFTOVER.sub('', text).strip()
        m = _LEADING_AMOUNT.match(text)
        if m:
            unit, rest = match_unit(text[m.end():])
            if unit:  # "200 g de farine"; a bare number stays ("4 épices")
                text = rest
            elif _ARTICLE.match(text[m.end():]):  # "2 de ..."
                text = text[m.end():]
        elif _key(text).startswith(('c a ', 'cuillere', 'cuilleree')):
            unit, rest = match_unit(text)
            if unit:
                text = rest
        removed = removed or text != before
        if removed:
            text = _ARTICLE.sub('', text).strip(' ,;:-')
        if text == before:
            break
    return text or str(name).strip()


def install():
    """Wrap IngredientParser.parse (idempotent)."""
    from cookbook.helper.ingredient_parser import IngredientParser
    if getattr(IngredientParser.parse, '_kitchen_french', False):
        return
    upstream_parse = IngredientParser.parse

    def parse(self, ingredient):
        if not is_french():
            return upstream_parse(self, ingredient)
        if len(ingredient.strip()) == 0 or len(ingredient) > 512:
            return upstream_parse(self, ingredient)  # upstream raises the right error
        if not hasattr(self, '_kitchen_foods'):
            self._kitchen_foods = ExistingFoods(getattr(self.request, 'space', None) if self.request is not None else None)
        if not self.ignore_rules:
            ingredient = self.automation.apply_transpose_automation(ingredient)
        try:
            amount, unit, food, note = parse_french(self, ingredient)
        except (ValueError, ZeroDivisionError):
            return upstream_parse(self, ingredient)
        if not self.ignore_rules:
            if unit is not None:
                unit = self.automation.apply_unit_automation(unit)
            food = self.automation.apply_food_automation(food)
        if len(food) > 128:
            food, note = food[:128], f'{food} {note}'.strip()
        return amount, unit, food.strip(), note.strip()[:256]

    parse._kitchen_french = True
    IngredientParser.parse = parse
