import json
from pathlib import Path


OUTPUT_FILE = Path("main_ai_canri") / "data" / "Synonyms.json"


BASE_SYNONYMS = {
    "fast": ["quick", "rapid", "speedy"],
    "smart": ["clever", "intelligent", "bright"],
    "code": ["program", "script", "software"],
    "safe": ["secure", "protected", "trusted"],
    "true": ["correct", "accurate", "valid"],
    "false": ["wrong", "incorrect", "invalid"],
    "big": ["large", "huge", "great"],
    "small": ["little", "tiny", "minor"],
    "good": ["fine", "strong", "useful"],
    "bad": ["poor", "wrong", "harmful"],
    "idea": ["concept", "thought", "plan"],
    "answer": ["reply", "response", "solution"],
    "question": ["query", "request", "prompt"],
    "research": ["study", "investigation", "analysis"],
    "history": ["past", "chronicle", "record"],
    "science": ["knowledge", "research", "discipline"],
    "language": ["speech", "tongue", "communication"],
    "memory": ["recall", "storage", "record"],
    "מהיר": ["זריז", "מהיר מאוד", "חפוז"],
    "חכם": ["נבון", "פיקח", "אינטליגנטי"],
    "קוד": ["תוכנית", "סקריפט", "תוכנה"],
    "בטוח": ["מאובטח", "מוגן", "אמין"],
    "נכון": ["מדויק", "תקף", "אמיתי"],
    "שאלה": ["בקשה", "שאילתה", "פנייה"],
    "תשובה": ["מענה", "תגובה", "פתרון"],
    "מחקר": ["בדיקה", "חקירה", "עיון"],
    "rapide": ["vite", "prompt", "accelere"],
    "intelligent": ["sage", "brillant", "malin"],
    "code_fr": ["programme", "script", "logiciel"],
    "sur": ["securise", "protege", "fiable"],
    "vrai": ["correct", "exact", "valide"],
    "question_fr": ["demande", "requete", "interrogation"],
    "reponse": ["solution", "retour", "explication"],
    "recherche": ["etude", "analyse", "investigation"],
}


DOMAINS = [
    ("ai", "בינה מלאכותית", "intelligence_artificielle"),
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
    ("story", "סיפור", "histoire_recit"),
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
    ("earth", "כדור_הארץ", "terre"),
    ("weather", "מזג_אוויר", "meteo"),
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
    ("topic", "נושא", "sujet"),
    ("translation", "תרגום", "traduction"),
    ("validator", "מאמת", "validateur"),
    ("word", "מילה", "mot"),
]


QUALITIES = [
    ("smart", "חכם", "intelligent", ["clever", "advanced", "bright"]),
    ("fast", "מהיר", "rapide", ["quick", "rapid", "speedy"]),
    ("safe", "בטוח", "sur", ["secure", "protected", "trusted"]),
    ("strong", "חזק", "fort", ["powerful", "solid", "robust"]),
    ("clear", "ברור", "clair", ["simple", "obvious", "understandable"]),
    ("deep", "עמוק", "profond", ["detailed", "thorough", "advanced"]),
    ("useful", "שימושי", "utile", ["helpful", "practical", "valuable"]),
    ("accurate", "מדויק", "precis", ["correct", "exact", "reliable"]),
    ("creative", "יצירתי", "creatif", ["imaginative", "original", "inventive"]),
    ("logical", "לוגי", "logique", ["rational", "ordered", "consistent"]),
]


def add_entry(data, key, synonyms):
    key = key.strip().lower()

    if not key or key in data:
        return False

    clean = []

    for synonym in synonyms:
        synonym = str(synonym).strip()

        if synonym and synonym.lower() != key and synonym not in clean:
            clean.append(synonym)

    if not clean:
        return False

    data[key] = clean

    return True


def build_synonyms():
    data = dict(BASE_SYNONYMS)

    for domain_en, domain_he, domain_fr in DOMAINS:
        add_entry(
            data,
            domain_en,
            [
                f"{domain_en}_field",
                f"{domain_en}_domain",
                f"{domain_en}_area",
            ],
        )
        add_entry(
            data,
            domain_he,
            [
                f"תחום_{domain_he}",
                f"עולם_{domain_he}",
                f"נושא_{domain_he}",
            ],
        )
        add_entry(
            data,
            domain_fr,
            [
                f"domaine_{domain_fr}",
                f"secteur_{domain_fr}",
                f"sujet_{domain_fr}",
            ],
        )

    for concept_en, concept_he, concept_fr in CONCEPTS:
        add_entry(
            data,
            concept_en,
            [
                f"{concept_en}_item",
                f"{concept_en}_unit",
                f"{concept_en}_element",
            ],
        )
        add_entry(
            data,
            concept_he,
            [
                f"{concept_he}_פריט",
                f"{concept_he}_יחידה",
                f"{concept_he}_רכיב",
            ],
        )
        add_entry(
            data,
            concept_fr,
            [
                f"{concept_fr}_element",
                f"{concept_fr}_unite",
                f"{concept_fr}_objet",
            ],
        )

    for quality_en, quality_he, quality_fr, quality_synonyms in QUALITIES:
        add_entry(data, quality_en, quality_synonyms)
        add_entry(
            data,
            quality_he,
            [
                f"{quality_he}_מאוד",
                f"{quality_he}_יותר",
                f"{quality_he}_במיוחד",
            ],
        )
        add_entry(
            data,
            quality_fr,
            [
                f"{quality_fr}_tres",
                f"{quality_fr}_plus",
                f"{quality_fr}_vraiment",
            ],
        )

    for domain_en, domain_he, domain_fr in DOMAINS:
        for concept_en, concept_he, concept_fr in CONCEPTS:
            add_entry(
                data,
                f"{domain_en}_{concept_en}",
                [
                    f"{concept_en}_{domain_en}",
                    f"{domain_en}_{concept_en}_unit",
                    f"{domain_en}_{concept_en}_item",
                ],
            )
            add_entry(
                data,
                f"{domain_he}_{concept_he}",
                [
                    f"{concept_he}_{domain_he}",
                    f"פריט_{domain_he}_{concept_he}",
                    f"רכיב_{domain_he}_{concept_he}",
                ],
            )
            add_entry(
                data,
                f"{domain_fr}_{concept_fr}",
                [
                    f"{concept_fr}_{domain_fr}",
                    f"{domain_fr}_{concept_fr}_element",
                    f"{domain_fr}_{concept_fr}_unite",
                ],
            )

            if len(data) >= 5000:
                return dict(list(data.items())[:5000])

    for quality_en, quality_he, quality_fr, quality_synonyms in QUALITIES:
        for domain_en, domain_he, domain_fr in DOMAINS:
            for concept_en, concept_he, concept_fr in CONCEPTS:
                add_entry(
                    data,
                    f"{quality_en}_{domain_en}_{concept_en}",
                    [
                        f"{domain_en}_{quality_en}_{concept_en}",
                        f"{quality_en}_{concept_en}_{domain_en}",
                        f"{quality_synonyms[0]}_{domain_en}_{concept_en}",
                    ],
                )
                add_entry(
                    data,
                    f"{quality_he}_{domain_he}_{concept_he}",
                    [
                        f"{domain_he}_{quality_he}_{concept_he}",
                        f"{quality_he}_מאוד_{domain_he}_{concept_he}",
                        f"{concept_he}_{domain_he}_{quality_he}",
                    ],
                )
                add_entry(
                    data,
                    f"{quality_fr}_{domain_fr}_{concept_fr}",
                    [
                        f"{domain_fr}_{quality_fr}_{concept_fr}",
                        f"{quality_fr}_tres_{domain_fr}_{concept_fr}",
                        f"{concept_fr}_{domain_fr}_{quality_fr}",
                    ],
                )

                if len(data) >= 5000:
                    return dict(list(data.items())[:5000])

    return data


def main():
    synonyms = build_synonyms()

    if len(synonyms) != 5000:
        raise RuntimeError(
            f"Expected 5000 synonyms, got {len(synonyms)}"
        )

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            synonyms,
            f,
            indent=2,
            ensure_ascii=False,
        )
        f.write("\n")

    print(f"Wrote {len(synonyms)} synonym entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
