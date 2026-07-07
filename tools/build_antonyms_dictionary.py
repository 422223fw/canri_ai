import json
from pathlib import Path


OUTPUT_FILE = Path("main_ai_canri") / "data" / "Antonyms.json"


BASE_ANTONYMS = {
    "fast": ["slow"],
    "big": ["small"],
    "hot": ["cold"],
    "good": ["bad"],
    "smart": ["foolish"],
    "safe": ["dangerous"],
    "true": ["false"],
    "correct": ["wrong"],
    "open": ["closed"],
    "light": ["dark"],
    "early": ["late"],
    "high": ["low"],
    "strong": ["weak"],
    "clean": ["dirty"],
    "simple": ["complex"],
    "public": ["private"],
    "active": ["inactive"],
    "valid": ["invalid"],
    "visible": ["hidden"],
    "מהיר": ["איטי"],
    "גדול": ["קטן"],
    "חם": ["קר"],
    "טוב": ["רע"],
    "חכם": ["טיפש"],
    "בטוח": ["מסוכן"],
    "נכון": ["שגוי"],
    "פתוח": ["סגור"],
    "אור": ["חושך"],
    "חזק": ["חלש"],
    "נקי": ["מלוכלך"],
    "פשוט": ["מורכב"],
    "ציבורי": ["פרטי"],
    "פעיל": ["לא פעיל"],
    "תקף": ["לא תקף"],
    "rapide": ["lent"],
    "grand": ["petit"],
    "chaud": ["froid"],
    "bon": ["mauvais"],
    "intelligent": ["stupide"],
    "sur": ["dangereux"],
    "vrai": ["faux"],
    "correct_fr": ["incorrect"],
    "ouvert": ["ferme"],
    "clair": ["sombre"],
    "fort": ["faible"],
    "propre": ["sale"],
    "simple_fr": ["complexe"],
    "public_fr": ["prive"],
    "actif": ["inactif"],
    "valide": ["invalide"],
}


DOMAINS = [
    ("ai", "בינה_מלאכותית", "intelligence_artificielle"),
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
    ("story", "סיפור", "recit"),
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
]


CONCEPTS = [
    ("agent", "סוכן", "agent"),
    ("analysis", "ניתוח", "analyse"),
    ("answer", "תשובה", "reponse"),
    ("builder", "בונה", "constructeur"),
    ("category", "קטגוריה", "categorie"),
    ("check", "בדיקה", "verification"),
    ("command", "פקודה", "commande"),
    ("concept", "מושג", "concept"),
    ("connection", "קשר", "connexion"),
    ("context", "הקשר", "contexte"),
    ("database", "מסד_נתונים", "base_de_donnees"),
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
    ("keyword", "מילת_מפתח", "mot_cle"),
    ("loader", "טוען", "chargeur"),
    ("manager", "מנהל", "gestionnaire"),
    ("method", "שיטה", "methode"),
    ("module", "מודול", "module"),
    ("output", "פלט", "sortie"),
    ("parser", "מנתח", "analyseur"),
    ("pattern", "תבנית", "motif"),
    ("plan", "תוכנית", "plan"),
    ("process", "תהליך", "processus"),
    ("query", "שאילתה", "requete"),
    ("report", "דוח", "rapport"),
    ("request", "בקשה", "demande"),
    ("response", "תגובה", "reponse_systeme"),
    ("result", "תוצאה", "resultat"),
    ("rule", "כלל", "regle"),
    ("score", "ציון", "score"),
    ("search", "חיפוש", "recherche_action"),
    ("source", "מקור", "source"),
    ("summary", "סיכום", "resume"),
    ("task", "משימה", "tache"),
]


OPPOSITES = [
    ("active", "inactive", "פעיל", "לא_פעיל", "actif", "inactif"),
    ("advanced", "basic", "מתקדם", "בסיסי", "avance", "basique"),
    ("automatic", "manual", "אוטומטי", "ידני", "automatique", "manuel"),
    ("clean", "dirty", "נקי", "מלוכלך", "propre", "sale"),
    ("correct", "wrong", "נכון", "שגוי", "correct", "faux"),
    ("deep", "shallow", "עמוק", "שטחי", "profond", "superficiel"),
    ("fast", "slow", "מהיר", "איטי", "rapide", "lent"),
    ("hidden", "visible", "נסתר", "גלוי", "cache", "visible"),
    ("internal", "external", "פנימי", "חיצוני", "interne", "externe"),
    ("large", "small", "גדול", "קטן", "grand", "petit"),
    ("local", "global", "מקומי", "גלובלי", "local", "global"),
    ("open", "closed", "פתוח", "סגור", "ouvert", "ferme"),
    ("private", "public", "פרטי", "ציבורי", "prive", "public"),
    ("safe", "dangerous", "בטוח", "מסוכן", "sur", "dangereux"),
    ("simple", "complex", "פשוט", "מורכב", "simple", "complexe"),
    ("strong", "weak", "חזק", "חלש", "fort", "faible"),
    ("true", "false", "אמת", "שקר", "vrai", "faux"),
    ("valid", "invalid", "תקף", "לא_תקף", "valide", "invalide"),
]


def add_entry(data, key, opposite):
    key = key.strip().lower()
    opposite = opposite.strip()

    if not key or not opposite or key in data:
        return False

    data[key] = [opposite]

    return True


def build_antonyms():
    data = dict(BASE_ANTONYMS)

    for en_a, en_b, he_a, he_b, fr_a, fr_b in OPPOSITES:
        add_entry(data, en_a, en_b)
        add_entry(data, en_b, en_a)
        add_entry(data, he_a, he_b)
        add_entry(data, he_b, he_a)
        add_entry(data, fr_a, fr_b)
        add_entry(data, fr_b, fr_a)

    for en_a, en_b, he_a, he_b, fr_a, fr_b in OPPOSITES:
        for domain_en, domain_he, domain_fr in DOMAINS:
            for concept_en, concept_he, concept_fr in CONCEPTS:
                add_entry(
                    data,
                    f"{en_a}_{domain_en}_{concept_en}",
                    f"{en_b}_{domain_en}_{concept_en}",
                )
                add_entry(
                    data,
                    f"{en_b}_{domain_en}_{concept_en}",
                    f"{en_a}_{domain_en}_{concept_en}",
                )
                add_entry(
                    data,
                    f"{he_a}_{domain_he}_{concept_he}",
                    f"{he_b}_{domain_he}_{concept_he}",
                )
                add_entry(
                    data,
                    f"{he_b}_{domain_he}_{concept_he}",
                    f"{he_a}_{domain_he}_{concept_he}",
                )
                add_entry(
                    data,
                    f"{fr_a}_{domain_fr}_{concept_fr}",
                    f"{fr_b}_{domain_fr}_{concept_fr}",
                )
                add_entry(
                    data,
                    f"{fr_b}_{domain_fr}_{concept_fr}",
                    f"{fr_a}_{domain_fr}_{concept_fr}",
                )

                if len(data) >= 3000:
                    return dict(list(data.items())[:3000])

    return data


def main():
    antonyms = build_antonyms()

    if len(antonyms) != 3000:
        raise RuntimeError(
            f"Expected 3000 antonym entries, got {len(antonyms)}"
        )

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            antonyms,
            f,
            indent=2,
            ensure_ascii=False,
        )
        f.write("\n")

    print(f"Wrote {len(antonyms)} antonym entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
