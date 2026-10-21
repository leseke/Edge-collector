"""Identification produit : cle stable a partir d'un titre d'annonce.

Regles deterministes et volontairement prudentes. Une identification
incertaine est signalee (identity_confidence) plutot que devinee.
"""
import re
import unicodedata

_LEGO_SET = re.compile(r"(?<!\d)(\d{4,6})(?:-\d)?(?!\d)")
_YEARS = set(str(y) for y in range(1950, 2041))

# Mots excluant un produit neuf/scelle complet (lots, pieces, notices...).
EXCLUDE_TOKENS = (
    "notice", "instructions only", "minifig only", "minifigure only",
    "boite vide", "empty box", "lot de pieces", "pieces detachees",
    "sticker", "autocollant", "replica", "compatible", "moc ", "custom",
    "proxy", "fake", "repro",
)
USED_TOKENS = ("occasion", "used", "d'occasion", "loose", "incomplet",
               "incomplete", "deballe", "opened", "ouvert")
SEALED_TOKENS = ("neuf", "new", "sealed", "scelle", "misb", "nisb", "bnib")


def fold(text):
    t = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t.lower()).strip()


def slug(text, max_words=8):
    words = re.findall(r"[a-z0-9]+", fold(text))
    stop = {"le", "la", "les", "de", "du", "des", "the", "and", "et", "a",
            "new", "neuf", "sealed", "scelle", "lot", "set"}
    words = [w for w in words if w not in stop][:max_words]
    return "-".join(words)


def lego_set_numbers(text):
    t = fold(text)
    if "lego" not in t:
        return []
    nums = [m.group(1) for m in _LEGO_SET.finditer(t)]
    return [n for n in nums if n not in _YEARS]


def condition_of(text, declared=None):
    """NEW / USED / UNKNOWN. Une mention d'usage l'emporte."""
    t = fold(text) + " " + fold(declared or "")
    if any(tok in t for tok in USED_TOKENS):
        return "USED"
    if any(tok in t for tok in SEALED_TOKENS) or fold(declared) in ("brand new", "new", "neuf"):
        return "NEW"
    return "UNKNOWN"


def identify(name, hint_key=None):
    """Retourne (product_key, identity_confidence, notes).

    HIGH  : un seul numero de set LEGO dans le titre (ou cle fournie).
    LOW   : plusieurs numeros (lot ?) ou cle derivee du libelle.
    """
    if hint_key:
        return str(hint_key).lower(), "HIGH", ["cle fournie par la source"]
    t = fold(name)
    if any(tok in t for tok in EXCLUDE_TOKENS):
        return None, "REJECTED", ["libelle hors produit complet"]
    nums = sorted(set(lego_set_numbers(name)))
    if len(nums) == 1:
        return f"lego:{nums[0]}", "HIGH", []
    if len(nums) > 1:
        return "lego:" + "+".join(nums), "LOW", ["plusieurs references : lot probable"]
    s = slug(name)
    if not s:
        return None, "REJECTED", ["libelle vide"]
    return f"name:{s}", "LOW", ["identification par libelle seulement"]
