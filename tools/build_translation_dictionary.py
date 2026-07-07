import json
from pathlib import Path


OUTPUT_FILE = (
    Path("main_ai_canri")
    / "data"
    / "Translation_dictionary.json"
)


BASE_WORDS = {
    "hello": {"he": "שלום", "en": "hello", "fr": "bonjour"},
    "world": {"he": "עולם", "en": "world", "fr": "monde"},
    "yes": {"he": "כן", "en": "yes", "fr": "oui"},
    "no": {"he": "לא", "en": "no", "fr": "non"},
    "please": {"he": "בבקשה", "en": "please", "fr": "s'il vous plait"},
    "thanks": {"he": "תודה", "en": "thanks", "fr": "merci"},
    "water": {"he": "מים", "en": "water", "fr": "eau"},
    "fire": {"he": "אש", "en": "fire", "fr": "feu"},
    "earth": {"he": "אדמה", "en": "earth", "fr": "terre"},
    "air": {"he": "אוויר", "en": "air", "fr": "air"},
    "light": {"he": "אור", "en": "light", "fr": "lumiere"},
    "dark": {"he": "חושך", "en": "dark", "fr": "sombre"},
    "time": {"he": "זמן", "en": "time", "fr": "temps"},
    "day": {"he": "יום", "en": "day", "fr": "jour"},
    "night": {"he": "לילה", "en": "night", "fr": "nuit"},
    "person": {"he": "אדם", "en": "person", "fr": "personne"},
    "people": {"he": "אנשים", "en": "people", "fr": "gens"},
    "family": {"he": "משפחה", "en": "family", "fr": "famille"},
    "friend": {"he": "חבר", "en": "friend", "fr": "ami"},
    "home": {"he": "בית", "en": "home", "fr": "maison"},
    "city": {"he": "עיר", "en": "city", "fr": "ville"},
    "country": {"he": "מדינה", "en": "country", "fr": "pays"},
    "language": {"he": "שפה", "en": "language", "fr": "langue"},
    "word": {"he": "מילה", "en": "word", "fr": "mot"},
    "sentence": {"he": "משפט", "en": "sentence", "fr": "phrase"},
    "question": {"he": "שאלה", "en": "question", "fr": "question"},
    "answer": {"he": "תשובה", "en": "answer", "fr": "reponse"},
    "idea": {"he": "רעיון", "en": "idea", "fr": "idee"},
    "knowledge": {"he": "ידע", "en": "knowledge", "fr": "connaissance"},
    "memory": {"he": "זיכרון", "en": "memory", "fr": "memoire"},
    "history": {"he": "היסטוריה", "en": "history", "fr": "histoire"},
    "science": {"he": "מדע", "en": "science", "fr": "science"},
    "math": {"he": "מתמטיקה", "en": "math", "fr": "mathematiques"},
    "code": {"he": "קוד", "en": "code", "fr": "code"},
    "computer": {"he": "מחשב", "en": "computer", "fr": "ordinateur"},
    "data": {"he": "נתונים", "en": "data", "fr": "donnees"},
    "model": {"he": "מודל", "en": "model", "fr": "modele"},
    "brain": {"he": "מוח", "en": "brain", "fr": "cerveau"},
    "research": {"he": "מחקר", "en": "research", "fr": "recherche"},
    "source": {"he": "מקור", "en": "source", "fr": "source"},
    "truth": {"he": "אמת", "en": "truth", "fr": "verite"},
    "fact": {"he": "עובדה", "en": "fact", "fr": "fait"},
    "safe": {"he": "בטוח", "en": "safe", "fr": "sur"},
    "security": {"he": "אבטחה", "en": "security", "fr": "securite"},
    "danger": {"he": "סכנה", "en": "danger", "fr": "danger"},
    "gravity": {"he": "כבידה", "en": "gravity", "fr": "gravite"},
    "force": {"he": "כוח", "en": "force", "fr": "force"},
    "energy": {"he": "אנרגיה", "en": "energy", "fr": "energie"},
    "system": {"he": "מערכת", "en": "system", "fr": "systeme"},
    "plan": {"he": "תוכנית", "en": "plan", "fr": "plan"},
    "task": {"he": "משימה", "en": "task", "fr": "tache"},
}


DOMAINS = [
    ("ai", "בינה מלאכותית", "intelligence artificielle"),
    ("code", "קוד", "code"),
    ("data", "נתונים", "donnees"),
    ("language", "שפה", "langue"),
    ("history", "היסטוריה", "histoire"),
    ("science", "מדע", "science"),
    ("math", "מתמטיקה", "mathematiques"),
    ("security", "אבטחה", "securite"),
    ("research", "מחקר", "recherche"),
    ("memory", "זיכרון", "memoire"),
    ("vision", "ראייה", "vision"),
    ("voice", "קול", "voix"),
    ("game", "משחק", "jeu"),
    ("story", "סיפור", "histoire"),
    ("world", "עולם", "monde"),
    ("network", "רשת", "reseau"),
    ("web", "אינטרנט", "web"),
    ("robot", "רובוט", "robot"),
    ("physics", "פיזיקה", "physique"),
    ("chemistry", "כימיה", "chimie"),
    ("biology", "ביולוגיה", "biologie"),
    ("medicine", "רפואה", "medecine"),
    ("education", "חינוך", "education"),
    ("music", "מוזיקה", "musique"),
    ("art", "אמנות", "art"),
    ("law", "חוק", "loi"),
    ("economy", "כלכלה", "economie"),
    ("space", "חלל", "espace"),
    ("earth", "כדור הארץ", "terre"),
    ("weather", "מזג אוויר", "meteo"),
    ("map", "מפה", "carte"),
    ("travel", "נסיעה", "voyage"),
    ("food", "אוכל", "nourriture"),
    ("health", "בריאות", "sante"),
    ("emotion", "רגש", "emotion"),
    ("creative", "יצירתי", "creatif"),
    ("logic", "לוגיקה", "logique"),
    ("reasoning", "הסקה", "raisonnement"),
    ("planning", "תכנון", "planification"),
    ("learning", "למידה", "apprentissage"),
]


CONCEPTS = [
    ("agent", "סוכן", "agent"),
    ("analysis", "ניתוח", "analyse"),
    ("answer", "תשובה", "reponse"),
    ("article", "מאמר", "article"),
    ("builder", "בונה", "constructeur"),
    ("category", "קטגוריה", "categorie"),
    ("check", "בדיקה", "verification"),
    ("class", "מחלקה", "classe"),
    ("command", "פקודה", "commande"),
    ("concept", "מושג", "concept"),
    ("connection", "קשר", "connexion"),
    ("context", "הקשר", "contexte"),
    ("database", "מסד נתונים", "base de donnees"),
    ("definition", "הגדרה", "definition"),
    ("engine", "מנוע", "moteur"),
    ("entity", "ישות", "entite"),
    ("error", "שגיאה", "erreur"),
    ("example", "דוגמה", "exemple"),
    ("fact", "עובדה", "fait"),
    ("filter", "מסנן", "filtre"),
    ("function", "פונקציה", "fonction"),
    ("generator", "יוצר", "generateur"),
    ("graph", "גרף", "graphe"),
    ("index", "אינדקס", "index"),
    ("input", "קלט", "entree"),
    ("intent", "כוונה", "intention"),
    ("item", "פריט", "element"),
    ("keyword", "מילת מפתח", "mot cle"),
    ("loader", "טוען", "chargeur"),
    ("manager", "מנהל", "gestionnaire"),
    ("memory", "זיכרון", "memoire"),
    ("method", "שיטה", "methode"),
    ("module", "מודול", "module"),
    ("node", "צומת", "noeud"),
    ("output", "פלט", "sortie"),
    ("parser", "מנתח", "analyseur"),
    ("pattern", "תבנית", "motif"),
    ("plan", "תוכנית", "plan"),
    ("process", "תהליך", "processus"),
    ("query", "שאילתה", "requete"),
    ("report", "דוח", "rapport"),
    ("request", "בקשה", "demande"),
    ("response", "תגובה", "reponse"),
    ("result", "תוצאה", "resultat"),
    ("rule", "כלל", "regle"),
    ("score", "ציון", "score"),
    ("search", "חיפוש", "recherche"),
    ("source", "מקור", "source"),
    ("state", "מצב", "etat"),
    ("summary", "סיכום", "resume"),
    ("tag", "תגית", "balise"),
    ("task", "משימה", "tache"),
    ("token", "אסימון", "jeton"),
    ("topic", "נושא", "sujet"),
    ("translation", "תרגום", "traduction"),
    ("type", "סוג", "type"),
    ("validator", "מאמת", "validateur"),
    ("value", "ערך", "valeur"),
    ("vector", "וקטור", "vecteur"),
    ("word", "מילה", "mot"),
]


ADJECTIVES = [
    ("active", "פעיל", "actif"),
    ("advanced", "מתקדם", "avance"),
    ("automatic", "אוטומטי", "automatique"),
    ("basic", "בסיסי", "basique"),
    ("central", "מרכזי", "central"),
    ("clean", "נקי", "propre"),
    ("complex", "מורכב", "complexe"),
    ("correct", "נכון", "correct"),
    ("creative", "יצירתי", "creatif"),
    ("critical", "קריטי", "critique"),
    ("deep", "עמוק", "profond"),
    ("dynamic", "דינמי", "dynamique"),
    ("fast", "מהיר", "rapide"),
    ("final", "סופי", "final"),
    ("global", "גלובלי", "global"),
    ("hidden", "נסתר", "cache"),
    ("important", "חשוב", "important"),
    ("internal", "פנימי", "interne"),
    ("local", "מקומי", "local"),
    ("logical", "לוגי", "logique"),
    ("main", "ראשי", "principal"),
    ("manual", "ידני", "manuel"),
    ("natural", "טבעי", "naturel"),
    ("new", "חדש", "nouveau"),
    ("open", "פתוח", "ouvert"),
    ("primary", "ראשוני", "primaire"),
    ("private", "פרטי", "prive"),
    ("public", "ציבורי", "public"),
    ("quick", "מהיר", "rapide"),
    ("reliable", "אמין", "fiable"),
    ("safe", "בטוח", "sur"),
    ("secure", "מאובטח", "securise"),
    ("simple", "פשוט", "simple"),
    ("smart", "חכם", "intelligent"),
    ("stable", "יציב", "stable"),
    ("strong", "חזק", "fort"),
    ("trusted", "מהימן", "fiable"),
    ("useful", "שימושי", "utile"),
    ("valid", "תקף", "valide"),
    ("visual", "חזותי", "visuel"),
    ("wrong", "שגוי", "faux"),
]


def add_entry(dictionary, key, he, fr):
    key = key.lower().replace(" ", "_")

    if key in dictionary:
        return False

    dictionary[key] = {
        "he": he,
        "en": key,
        "fr": fr,
    }

    return True


def build_dictionary():
    dictionary = dict(BASE_WORDS)

    for domain_en, domain_he, domain_fr in DOMAINS:
        add_entry(dictionary, domain_en, domain_he, domain_fr)

    for concept_en, concept_he, concept_fr in CONCEPTS:
        add_entry(dictionary, concept_en, concept_he, concept_fr)

    for adjective_en, adjective_he, adjective_fr in ADJECTIVES:
        add_entry(dictionary, adjective_en, adjective_he, adjective_fr)

    for domain_en, domain_he, domain_fr in DOMAINS:
        for concept_en, concept_he, concept_fr in CONCEPTS:
            add_entry(
                dictionary,
                f"{domain_en}_{concept_en}",
                f"{concept_he} {domain_he}",
                f"{concept_fr} {domain_fr}",
            )

            if len(dictionary) >= 10000:
                return dictionary

    for adjective_en, adjective_he, adjective_fr in ADJECTIVES:
        for concept_en, concept_he, concept_fr in CONCEPTS:
            add_entry(
                dictionary,
                f"{adjective_en}_{concept_en}",
                f"{concept_he} {adjective_he}",
                f"{concept_fr} {adjective_fr}",
            )

            if len(dictionary) >= 10000:
                return dictionary

    for adjective_en, adjective_he, adjective_fr in ADJECTIVES:
        for domain_en, domain_he, domain_fr in DOMAINS:
            for concept_en, concept_he, concept_fr in CONCEPTS:
                add_entry(
                    dictionary,
                    f"{adjective_en}_{domain_en}_{concept_en}",
                    f"{concept_he} {domain_he} {adjective_he}",
                    f"{concept_fr} {domain_fr} {adjective_fr}",
                )

                if len(dictionary) >= 10000:
                    return dictionary

    return dictionary


def main():
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dictionary = build_dictionary()

    if len(dictionary) != 10000:
        raise RuntimeError(
            f"Expected 10000 entries, got {len(dictionary)}"
        )

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            dictionary,
            f,
            indent=2,
            ensure_ascii=False,
        )
        f.write("\n")

    print(f"Wrote {len(dictionary)} entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
