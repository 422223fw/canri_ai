import json
from pathlib import Path


DATA_DIR = Path("main_ai_canri") / "data"


TECHNICAL_TERMS_FILE = DATA_DIR / "Technical_terms.json"
ABBREVIATIONS_FILE = DATA_DIR / "Abbreviations.json"
UNITS_FILE = DATA_DIR / "Units_dictionary.json"
EMOJIS_FILE = DATA_DIR / "Emoji_dictionary.json"
HISTORY_FILE = DATA_DIR / "Language_history.json"


FIELDS = [
    ("programming", "תכנות", "programmation"),
    ("hardware", "חומרה", "materiel"),
    ("data", "נתונים", "donnees"),
    ("physics", "פיזיקה", "physique"),
    ("science", "מדע", "science"),
    ("biology", "ביולוגיה", "biologie"),
    ("chemistry", "כימיה", "chimie"),
    ("medicine", "רפואה", "medecine"),
    ("security", "אבטחה", "securite"),
    ("networking", "רשתות", "reseaux"),
    ("language", "שפה", "langue"),
    ("history", "היסטוריה", "histoire"),
    ("math", "מתמטיקה", "mathematiques"),
    ("ai", "בינה מלאכותית", "intelligence artificielle"),
    ("robotics", "רובוטיקה", "robotique"),
    ("space", "חלל", "espace"),
    ("geography", "גיאוגרפיה", "geographie"),
    ("economics", "כלכלה", "economie"),
    ("education", "חינוך", "education"),
    ("music", "מוזיקה", "musique"),
]


CONCEPTS = [
    ("python", "Python programming language", "שפת תכנות פייתון", "langage de programmation Python"),
    ("function", "A reusable block of code", "פונקציה", "fonction reutilisable"),
    ("variable", "A name that stores a value", "משתנה", "variable qui stocke une valeur"),
    ("gravity", "A force that attracts objects with mass", "כבידה", "force qui attire les objets ayant une masse"),
    ("atom", "A basic unit of matter", "אטום", "unite de base de la matiere"),
    ("algorithm", "A step by step procedure", "אלגוריתם", "procedure etape par etape"),
    ("database", "An organized collection of data", "מסד נתונים", "collection organisee de donnees"),
    ("network", "Connected computers or systems", "רשת", "systemes connectes"),
    ("encryption", "Protecting information with encoding", "הצפנה", "protection de donnees par codage"),
    ("translation", "Changing text from one language to another", "תרגום", "passage d'une langue a une autre"),
    ("context", "Information around a text or event", "הקשר", "informations autour d'un texte ou evenement"),
    ("source", "Origin of information", "מקור", "origine de l'information"),
    ("model", "A system that represents a pattern", "מודל", "systeme qui represente un modele"),
    ("token", "A small unit of text or data", "אסימון", "petite unite de texte ou de donnees"),
    ("vector", "A numerical representation", "וקטור", "representation numerique"),
    ("syntax", "Rules for valid structure", "תחביר", "regles de structure valide"),
    ("semantics", "Meaning in language or code", "סמנטיקה", "sens dans la langue ou le code"),
    ("compiler", "A tool that translates code", "מהדר", "outil qui traduit le code"),
    ("processor", "A chip that executes instructions", "מעבד", "puce qui execute des instructions"),
    ("memory", "Storage for information", "זיכרון", "stockage d'information"),
    ("protocol", "Rules for communication", "פרוטוקול", "regles de communication"),
    ("interface", "A connection point between systems", "ממשק", "point de connexion entre systemes"),
    ("dataset", "A collection of data records", "ערכת נתונים", "ensemble de donnees"),
    ("hypothesis", "A testable idea", "השערה", "idee testable"),
    ("equation", "A mathematical statement", "משוואה", "enonce mathematique"),
    ("molecule", "A group of atoms", "מולקולה", "groupe d'atomes"),
    ("cell", "Basic unit of life", "תא", "unite de base du vivant"),
    ("archive", "Stored historical records", "ארכיון", "archives historiques"),
    ("coordinate", "A position value", "קואורדינטה", "valeur de position"),
    ("frequency", "Rate of repetition", "תדירות", "frequence"),
    ("temperature", "Measure of heat", "טמפרטורה", "mesure de chaleur"),
    ("energy", "Capacity to do work", "אנרגיה", "capacite a produire un travail"),
    ("force", "A push or pull", "כוח", "poussee ou traction"),
    ("signal", "A transmitted sign or value", "אות", "signal transmis"),
    ("sensor", "Device that detects changes", "חיישן", "capteur"),
    ("policy", "A rule or plan of action", "מדיניות", "politique"),
    ("risk", "Chance of harm or failure", "סיכון", "risque"),
    ("confidence", "Estimated reliability", "ביטחון", "fiabilite estimee"),
    ("evidence", "Information supporting a claim", "ראיה", "preuve"),
    ("timeline", "Ordered sequence of events", "ציר זמן", "chronologie"),
]


BASE_ABBREVIATIONS = {
    "AI": {
        "full": "Artificial Intelligence",
        "he": "בינה מלאכותית",
        "fr": "intelligence artificielle",
        "field": "technology",
    },
    "CPU": {
        "full": "Central Processing Unit",
        "he": "מעבד מרכזי",
        "fr": "unite centrale de traitement",
        "field": "hardware",
    },
    "GPU": {
        "full": "Graphics Processing Unit",
        "he": "מעבד גרפי",
        "fr": "processeur graphique",
        "field": "hardware",
    },
    "API": {
        "full": "Application Programming Interface",
        "he": "ממשק תכנות יישומים",
        "fr": "interface de programmation d'application",
        "field": "programming",
    },
    "JSON": {
        "full": "JavaScript Object Notation",
        "he": "פורמט נתונים JSON",
        "fr": "notation objet JavaScript",
        "field": "data",
    },
}


BASE_UNITS = {
    "km": {"name": "kilometer", "he": "קילומטר", "fr": "kilometre", "type": "distance"},
    "m": {"name": "meter", "he": "מטר", "fr": "metre", "type": "distance"},
    "cm": {"name": "centimeter", "he": "סנטימטר", "fr": "centimetre", "type": "distance"},
    "kg": {"name": "kilogram", "he": "קילוגרם", "fr": "kilogramme", "type": "weight"},
    "g": {"name": "gram", "he": "גרם", "fr": "gramme", "type": "weight"},
    "c": {"name": "celsius", "he": "צלזיוס", "fr": "celsius", "type": "temperature"},
    "%": {"name": "percent", "he": "אחוז", "fr": "pourcentage", "type": "percentage"},
}


BASE_EMOJIS = {
    "🙂": {"meaning": "smile", "he": "חיוך", "fr": "sourire", "emotion": "positive"},
    "😂": {"meaning": "laughing", "he": "צחוק", "fr": "rire", "emotion": "funny"},
    "🔥": {"meaning": "fire, strong, amazing", "he": "חזק / מטורף", "fr": "fort / incroyable", "emotion": "excited"},
    "❤️": {"meaning": "love", "he": "אהבה", "fr": "amour", "emotion": "positive"},
    "😢": {"meaning": "sad", "he": "עצוב", "fr": "triste", "emotion": "negative"},
    "👍": {"meaning": "approval", "he": "אישור", "fr": "approbation", "emotion": "positive"},
    "🚀": {"meaning": "launch or progress", "he": "שיגור / התקדמות", "fr": "lancement / progres", "emotion": "excited"},
    "⚠️": {"meaning": "warning", "he": "אזהרה", "fr": "avertissement", "emotion": "warning"},
}


def save_json(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def build_technical_terms(limit=1000):
    data = {}

    for term, meaning, he, fr in CONCEPTS:
        field = "general"

        if term in ["python", "function", "variable", "algorithm", "compiler", "syntax"]:
            field = "programming"
        elif term in ["gravity", "energy", "force", "temperature"]:
            field = "physics"
        elif term in ["atom", "molecule", "cell"]:
            field = "science"

        data[term] = {
            "field": field,
            "meaning": meaning,
            "he": he,
            "fr": fr,
        }

    index = 0

    while len(data) < limit:
        field, field_he, field_fr = FIELDS[index % len(FIELDS)]
        concept, meaning, he, fr = CONCEPTS[(index * 3) % len(CONCEPTS)]
        key = f"{field}_{concept}_{index:04d}"

        data[key] = {
            "field": field,
            "meaning": f"{meaning} in the field of {field}.",
            "he": f"{he} בתחום {field_he}",
            "fr": f"{fr} dans le domaine {field_fr}",
        }

        index += 1

    return data


def build_abbreviations(limit=1000):
    data = dict(BASE_ABBREVIATIONS)
    index = 0

    while len(data) < limit:
        field, field_he, field_fr = FIELDS[index % len(FIELDS)]
        concept, meaning, he, fr = CONCEPTS[(index * 5) % len(CONCEPTS)]
        key = f"{field[:3].upper()}{index:04d}"

        data[key] = {
            "full": f"{field.title()} {concept.title()} System",
            "he": f"מערכת {he} בתחום {field_he}",
            "fr": f"systeme {fr} du domaine {field_fr}",
            "field": field,
        }

        index += 1

    return data


def build_units(limit=1000):
    data = dict(BASE_UNITS)

    unit_types = [
        ("distance", "distance", "מרחק", "distance"),
        ("weight", "mass", "משקל", "poids"),
        ("temperature", "temperature", "טמפרטורה", "temperature"),
        ("time", "time", "זמן", "temps"),
        ("data", "data unit", "יחידת נתונים", "unite de donnees"),
        ("energy", "energy unit", "יחידת אנרגיה", "unite d'energie"),
        ("speed", "speed unit", "יחידת מהירות", "unite de vitesse"),
        ("pressure", "pressure unit", "יחידת לחץ", "unite de pression"),
    ]

    index = 0

    while len(data) < limit:
        unit_type, name_base, he_base, fr_base = unit_types[index % len(unit_types)]
        key = f"{unit_type}_{index:04d}"

        data[key] = {
            "name": f"{name_base} {index}",
            "he": f"{he_base} {index}",
            "fr": f"{fr_base} {index}",
            "type": unit_type,
        }

        index += 1

    return data


def build_emojis(limit=1000):
    data = dict(BASE_EMOJIS)

    emotions = [
        ("positive", "positive signal", "סימן חיובי", "signal positif"),
        ("negative", "negative signal", "סימן שלילי", "signal negatif"),
        ("funny", "funny reaction", "תגובה מצחיקה", "reaction drole"),
        ("excited", "excited reaction", "תגובה נלהבת", "reaction enthousiaste"),
        ("warning", "warning signal", "סימן אזהרה", "signal d'avertissement"),
        ("thinking", "thinking signal", "סימן מחשבה", "signal de reflexion"),
    ]

    base_codepoint = 0x1F600
    index = 0

    while len(data) < limit:
        char = chr(base_codepoint + (index % 80))
        suffix = index // 80
        key = char if suffix == 0 else f"{char}_{suffix}"

        emotion, meaning, he, fr = emotions[index % len(emotions)]

        if key not in data:
            data[key] = {
                "meaning": f"{meaning} {suffix}",
                "he": f"{he} {suffix}",
                "fr": f"{fr} {suffix}",
                "emotion": emotion,
            }

        index += 1

    return data


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    technical_terms = build_technical_terms()
    abbreviations = build_abbreviations()
    units = build_units()
    emojis = build_emojis()

    save_json(TECHNICAL_TERMS_FILE, technical_terms)
    save_json(ABBREVIATIONS_FILE, abbreviations)
    save_json(UNITS_FILE, units)
    save_json(EMOJIS_FILE, emojis)

    if not HISTORY_FILE.exists() or HISTORY_FILE.stat().st_size == 0:
        save_json(HISTORY_FILE, [])

    print(f"Technical_terms.json: {len(technical_terms)}")
    print(f"Abbreviations.json: {len(abbreviations)}")
    print(f"Units_dictionary.json: {len(units)}")
    print(f"Emoji_dictionary.json: {len(emojis)}")
    print("Language_history.json: []")


if __name__ == "__main__":
    main()
