import re

GERMAN_HINTS = {
    "und",
    "der",
    "die",
    "das",
    "mit",
    "fuer",
    "auf",
    "als",
    "bei",
    "wir",
    "sie",
    "ihr",
    "uns",
    "bewerbung",
    "stellenanzeige",
    "aufgaben",
    "kenntnisse",
    "erfahrung",
    "bereich",
    "team",
    "unternehmen",
}


def detect_language(text):
    if not text:
        return "en"
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    if not tokens:
        return "en"
    hits = sum(1 for t in tokens if t in GERMAN_HINTS)
    if hits >= 3:
        return "de"
    return "en"
