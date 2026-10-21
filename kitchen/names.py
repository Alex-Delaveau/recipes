"""
French food name normalisation and similarity, shared by the duplicate finder, the aisle suggestion and the
"closest existing food" proposal of the import review.

The rules are deliberately simple and explainable (a reason is returned with every match):
- case, accents, punctuation and quantities are ignored ("1 Oignon émincé" ~ "oignon") ;
- plural forms are reduced to the singular ("oignons", "poireaux", "choux") ;
- preparation words and small words are dropped ("émincé", "frais", "de") ;
- a name whose words are all contained in the other one matches ("oignon" ~ "oignon jaune") ;
- otherwise a close spelling matches (typos).
"""
import re
import unicodedata
from difflib import SequenceMatcher

# words that describe a preparation or a state, not a different food
DESCRIPTORS = {
    'emince', 'eminces', 'emincee', 'emincees', 'hache', 'haches', 'hachee', 'hachees', 'coupe', 'coupes', 'coupee',
    'coupees', 'rape', 'rapes', 'rapee', 'rapees', 'frais', 'sec', 'secs', 'seche', 'seches',
    'pele', 'peles', 'pelee', 'pelees', 'cuit', 'cuits', 'cuite', 'cuites', 'cru', 'crus', 'crue', 'crues', 'bio',
    'entier', 'entiers', 'entiere', 'entieres', 'moyen', 'moyens', 'moyenne', 'moyennes', 'gros', 'grosse', 'grosses',
    'petit', 'petits', 'petite', 'petites', 'beau', 'beaux', 'belle', 'belles', 'mur', 'murs', 'mure', 'mures', 'bien',
    'finement', 'grossierement', 'en', 'des', 'cubes', 'cube', 'des', 'rondelles', 'lamelles', 'morceaux', 'tranches',
    'environ', 'facultatif', 'optionnel',
}

# grammatical words ignored when comparing ("pommes de terre" keeps its meaning through the remaining words)
STOPWORDS = {'de', 'd', 'du', 'des', 'la', 'le', 'les', 'l', 'a', 'au', 'aux', 'et', 'ou', 'un', 'une'}

# plural endings that are not a simple trailing s/x
IRREGULAR_PLURALS = {'oeufs': 'oeuf', 'yeux': 'oeil', 'boeufs': 'boeuf'}
INVARIABLE = {'pois', 'riz', 'mais', 'anchois', 'radis', 'noix', 'ananas', 'cassis', 'jus', 'gras', 'frais', 'gros',
              'bras', 'tapioca', 'couscous', 'pamplemousse', 'chips'}


def strip_accents(text):
    text = text.replace('œ', 'oe').replace('Œ', 'oe').replace('æ', 'ae').replace('Æ', 'ae')
    return ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))


def singular(word):
    """French singular of a single, accent-free, lower case word (good enough for food names)."""
    if word in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[word]
    if word in INVARIABLE or len(word) <= 3:
        return word
    if word.endswith('eaux') or word.endswith('eux') or word.endswith('oux'):
        return word[:-1]  # poireaux -> poireau, cheveux, choux -> chou
    if word.endswith('aux') and len(word) > 4:
        return word[:-3] + 'al'  # (bocaux -> bocal)
    if word.endswith('s') and not word.endswith('ss'):
        return word[:-1]
    if word.endswith('x'):
        return word[:-1]
    return word


def words(name):
    """Significant words of a food name: accent-free, singular, without quantities, small words or descriptors."""
    text = strip_accents(str(name).lower())
    text = re.sub(r"[’'`]", ' ', text)
    text = re.sub(r'[^a-z0-9 ]+', ' ', text)
    result = []
    for w in text.split():
        if w.isdigit() or re.fullmatch(r'\d+[a-z]{0,2}', w):  # "1", "200g"
            continue
        if w in STOPWORDS or w in DESCRIPTORS:
            continue
        result.append(singular(w))
    return result


COMPOUND = re.compile(r"\b(de|du|des|d|a la|au|aux)\b")


def is_compound(name):
    """'pomme de terre', 'huile d'olive', 'poulet au curry': a preposition links the words"""
    text = re.sub(r"[’'`]", ' ', strip_accents(str(name).lower()))
    text = re.sub(r'^[\d\s.,/]+', '', text)  # a leading quantity is not part of the name
    return bool(COMPOUND.search(text))


def _tokens(name):
    """all the words of a name, small words included, accent-free and singular: 'Pommes de terre' -> pomme de terre"""
    text = re.sub(r"[’'`]", ' ', strip_accents(str(name).lower()))
    return [singular(w) for w in re.sub(r'[^a-z0-9 ]+', ' ', text).split()]


def extends_compound(shorter, longer):
    """
    'Pomme de terre' -> 'Pomme de terre à chair ferme': the whole compound name, then more words (a variety).
    Not 'Pomme' -> 'Pomme de terre': there the preposition belongs to the longer name.
    """
    short, long = _tokens(shorter), _tokens(longer)
    return is_compound(shorter) and len(long) > len(short) and long[:len(short)] == short


def normalize(name):
    """Comparison key of a food name: "Oignons émincés" -> "oignon"."""
    return ' '.join(words(name))


def similarity(a, b):
    """
    Returns (score, reason) for two food names, score in [0, 1]; reason is None when the names are not considered
    the same food. Reasons: 'same' (only case/accents/plural/descriptors differ), 'extra_words', 'spelling'.
    """
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return 0.0, None
    na, nb = ' '.join(wa), ' '.join(wb)
    if na == nb:
        return 1.0, 'same'
    sa, sb = set(wa), set(wb)
    small, big = (sa, sb) if len(sa) <= len(sb) else (sb, sa)
    # "oignon" ~ "oignon jaune": every word of the shorter name is in the longer one, at most 2 words more.
    # Not when the extra words make a compound with a preposition: "pomme de terre", "lait de coco", "huile d'olive" are
    # other foods than "pomme", "lait", "huile". A whole compound followed by more words is a variety, though:
    # "pomme de terre à chair ferme" ~ "pomme de terre".
    longer, shorter = (a, b) if len(wa) >= len(wb) else (b, a)
    compound_ok = not is_compound(longer) or extends_compound(shorter, longer)
    if small <= big and len(big) - len(small) <= 2 and len(' '.join(sorted(small))) >= 3 and compound_ok:
        return 0.9 - 0.05 * (len(big) - len(small)), 'extra_words'
    ratio = SequenceMatcher(None, na, nb).ratio()
    if ratio >= 0.88 and min(len(na), len(nb)) >= 5:
        return round(ratio * 0.85, 3), 'spelling'
    return round(ratio * 0.5, 3), None


def closest(name, candidates, threshold=0.7):
    """
    Best match for `name` among `candidates` (iterable of (key, candidate_name)); returns (key, score, reason) or None.
    """
    best = None
    for key, candidate in candidates:
        score, reason = similarity(name, candidate)
        if reason and score >= threshold and (best is None or score > best[1]):
            best = (key, score, reason)
    return best
