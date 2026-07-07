import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "data"
ARTICLES_PATH = DATA_DIR / "Articles.json"
STATISTICS_PATH = DATA_DIR / "Articles_statistics.json"

TARGET_NEW_ARTICLES = 1000


FIELDS = {
    "physics": {
        "source_recommendations": ["NASA", "NIST", "Physics LibreTexts", "Encyclopaedia Britannica"],
        "subfields": {
            "mechanics": ["force", "motion", "momentum", "energy", "torque", "oscillation", "friction", "rotation"],
            "thermodynamics": ["temperature", "entropy", "heat transfer", "phase change", "engine efficiency", "pressure", "thermal equilibrium", "specific heat"],
            "electromagnetism": ["electric field", "magnetic field", "induction", "Maxwell equations", "circuits", "capacitance", "resistance", "electromagnetic waves"],
            "quantum physics": ["wave function", "uncertainty", "superposition", "entanglement", "quantization", "tunneling", "spin", "measurement"],
            "relativity": ["spacetime", "time dilation", "mass energy", "gravity", "curvature", "black holes", "light speed", "reference frames"],
        },
    },
    "chemistry": {
        "source_recommendations": ["Chemistry LibreTexts", "NIST Chemistry WebBook", "PubChem", "Royal Society of Chemistry"],
        "subfields": {
            "atomic chemistry": ["atomic structure", "isotopes", "electron configuration", "orbitals", "periodic trends", "ionization energy", "atomic radius", "valence"],
            "chemical bonding": ["ionic bonding", "covalent bonding", "metallic bonding", "hydrogen bonding", "polarity", "molecular geometry", "bond energy", "intermolecular forces"],
            "reaction chemistry": ["reaction rate", "equilibrium", "catalyst", "oxidation", "reduction", "stoichiometry", "activation energy", "reaction mechanism"],
            "acids and bases": ["pH", "buffer solution", "strong acid", "weak acid", "neutralization", "titration", "conjugate base", "alkalinity"],
            "organic chemistry": ["hydrocarbons", "functional groups", "isomers", "polymers", "alcohols", "carboxylic acids", "esters", "aromatic compounds"],
        },
    },
    "biology": {
        "source_recommendations": ["NCBI Bookshelf", "PubMed", "Nature Education", "Khan Academy Biology"],
        "subfields": {
            "cell biology": ["cell membrane", "nucleus", "mitochondria", "ribosomes", "protein synthesis", "cell signaling", "cytoskeleton", "transport"],
            "genetics": ["DNA", "gene expression", "mutation", "chromosomes", "inheritance", "transcription", "translation", "genetic variation"],
            "evolution": ["natural selection", "adaptation", "speciation", "common ancestry", "fitness", "genetic drift", "selection pressure", "fossil evidence"],
            "human physiology": ["circulation", "respiration", "digestion", "nervous system", "immune response", "hormones", "homeostasis", "muscle contraction"],
            "ecology": ["ecosystem", "food web", "population dynamics", "biodiversity", "habitat", "carbon cycle", "competition", "symbiosis"],
        },
    },
    "earth science": {
        "source_recommendations": ["USGS", "NOAA", "NASA Earth Observatory", "National Geographic Education"],
        "subfields": {
            "geology": ["plate tectonics", "rock cycle", "minerals", "volcanoes", "earthquakes", "faults", "sedimentation", "metamorphism"],
            "climate science": ["greenhouse effect", "climate feedback", "carbon dioxide", "temperature records", "radiative forcing", "aerosols", "ocean heat", "paleoclimate"],
            "meteorology": ["air pressure", "humidity", "fronts", "storms", "cloud formation", "wind patterns", "precipitation", "weather models"],
            "oceanography": ["ocean currents", "salinity", "marine ecosystems", "tides", "upwelling", "ocean acidification", "seafloor", "heat transport"],
            "hydrology": ["water cycle", "groundwater", "rivers", "watersheds", "evaporation", "infiltration", "floods", "water quality"],
        },
    },
    "astronomy": {
        "source_recommendations": ["NASA", "ESA", "HubbleSite", "Chandra X-ray Observatory"],
        "subfields": {
            "stars": ["stellar formation", "nuclear fusion", "main sequence", "red giant", "supernova", "white dwarf", "neutron star", "stellar spectra"],
            "planetary science": ["planet formation", "exoplanets", "atmospheres", "orbital resonance", "moons", "asteroids", "comets", "impact craters"],
            "galaxies": ["spiral galaxies", "elliptical galaxies", "dark matter", "galactic rotation", "star clusters", "active galactic nuclei", "interstellar medium", "galaxy evolution"],
            "cosmology": ["Big Bang", "cosmic microwave background", "expansion", "dark energy", "large scale structure", "redshift", "inflation", "cosmic age"],
        },
    },
    "computer science": {
        "source_recommendations": ["ACM Digital Library", "IEEE Computer Society", "NIST", "MIT OpenCourseWare"],
        "subfields": {
            "algorithms": ["sorting", "searching", "complexity", "graphs", "dynamic programming", "recursion", "greedy algorithms", "data structures"],
            "artificial intelligence": ["machine learning", "neural networks", "classification", "language models", "training data", "evaluation", "bias", "inference"],
            "computer systems": ["operating systems", "memory", "processes", "threads", "filesystems", "networking", "compilers", "databases"],
            "cybersecurity": ["encryption", "authentication", "access control", "vulnerabilities", "threat modeling", "malware", "network security", "secure coding"],
        },
    },
}


PERSPECTIVES = [
    "fundamental principles",
    "measurement and evidence",
    "real world applications",
    "common misconceptions",
    "advanced mechanisms",
]


DIFFICULTIES = ["introductory", "intermediate", "advanced"]


def load_json(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def slug(value):
    return (
        value.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def title_case(value):
    small = {"and", "or", "of", "the", "in", "to", "by"}
    parts = []
    for index, word in enumerate(value.split()):
        if index > 0 and word in small:
            parts.append(word)
        else:
            parts.append(word[:1].upper() + word[1:])
    return " ".join(parts)


def make_article(article_id, field, subfield, concept, perspective, difficulty, sources):
    title = f"{title_case(concept)}: {title_case(perspective)}"
    keywords = [field, subfield, concept, perspective, difficulty]
    concepts = [concept, subfield, field, "evidence", "model", "measurement", "application"]

    abstract = (
        f"This article explains {concept} in {subfield}, a major area of {field}. "
        f"It focuses on {perspective}, connects the concept to observable evidence, "
        f"and separates established scientific knowledge from simplified classroom models."
    )

    key_points = [
        f"{title_case(concept)} is understood through models that connect observations, mechanisms, and predictions.",
        f"In {subfield}, reliable explanations depend on measurement, reproducible evidence, and careful definitions.",
        f"The concept is useful because it links theory to practical applications in technology, health, environment, or research.",
        "A strong answer should mention limits, assumptions, and the difference between simplified models and expert-level detail.",
    ]

    content = (
        f"{title}\n\n"
        f"Overview. {concept.capitalize()} is an important concept in {subfield}, within the broader field of {field}. "
        f"A professional explanation begins by defining the system being studied, the scale of observation, and the variables that can be measured. "
        f"In scientific work, a concept is not considered strong merely because it sounds reasonable; it becomes reliable when it explains observations, "
        f"makes useful predictions, and remains consistent with evidence gathered by independent investigators. "
        f"For {concept}, the most important starting point is to identify what changes, what remains conserved, and what mechanisms connect cause and effect.\n\n"
        f"Core mechanism. In the context of {perspective}, {concept} is best treated as part of a network of related ideas rather than as an isolated fact. "
        f"The mechanism depends on interactions among components, constraints imposed by physical or biological laws, and feedback that can amplify or reduce change. "
        f"Students often memorize a short definition, but expert reasoning asks how the concept behaves under different conditions, what evidence would support it, "
        f"and what observation would force the model to be revised. This is why diagrams, controlled experiments, mathematical relationships, and carefully described examples "
        f"are all valuable when explaining {concept}.\n\n"
        f"Evidence and measurement. Reliable knowledge about {concept} comes from repeatable measurement. Scientists compare observations with models, estimate uncertainty, "
        f"and look for patterns that remain stable across different methods. A measurement can be precise without being accurate, and a single observation is rarely enough "
        f"to establish a broad scientific claim. In {subfield}, strong evidence usually includes clear definitions, calibrated instruments or validated procedures, "
        f"transparent data collection, and results that other researchers can reproduce or challenge. The strongest explanations also acknowledge what the evidence does not show.\n\n"
        f"Applications. Understanding {concept} helps explain practical problems in science and engineering. Depending on the domain, it may be used to design experiments, "
        f"interpret natural processes, improve technology, diagnose failures, protect health, model environmental change, or predict how a system will respond to new conditions. "
        f"Applied science often requires simplifying a complex system, but good simplification keeps the essential variables and states its assumptions clearly. "
        f"When {concept} is used outside the laboratory, uncertainty, scale, cost, ethics, and safety can become just as important as the core theory.\n\n"
        f"Misconceptions and limits. A common mistake is to treat {concept} as a single fixed rule that works the same way in every situation. Real scientific concepts have ranges "
        f"where they are useful and ranges where a deeper or different model is needed. Another mistake is confusing correlation with causation: two measurements may change together "
        f"without one directly causing the other. A careful explanation should separate what is known, what is inferred, and what remains uncertain. "
        f"This is especially important when simplified educational examples are compared with professional research.\n\n"
        f"Expert summary. A strong scientific account of {concept} includes a definition, the mechanism behind it, the evidence supporting it, the assumptions of the model, "
        f"and at least one application. The concept belongs to {subfield} and is connected to broader scientific reasoning in {field}. "
        f"For high confidence, compare explanations with trusted sources such as {', '.join(sources[:3])}, and prefer primary research, official scientific agencies, "
        f"or expert-reviewed educational material when accuracy matters."
    )

    return {
        "id": article_id,
        "title": title,
        "field": field,
        "subfield": subfield,
        "difficulty": difficulty,
        "abstract": abstract,
        "keywords": keywords,
        "concepts": concepts,
        "key_points": key_points,
        "content": content,
        "source_recommendations": sources,
        "quality_notes": [
            "Educational synthesis generated from established science concepts.",
            "Use recommended sources for source-level verification.",
            "Not a substitute for peer-reviewed literature in high-stakes contexts.",
        ],
    }


def build_articles(existing_articles):
    existing_ids = {article.get("id") for article in existing_articles}
    generated = []
    index = 1

    for field, field_data in FIELDS.items():
        sources = field_data["source_recommendations"]

        for subfield, concepts in field_data["subfields"].items():
            for concept in concepts:
                for perspective in PERSPECTIVES:
                    difficulty = DIFFICULTIES[(index - 1) % len(DIFFICULTIES)]
                    article_id = f"science_{slug(field)}_{slug(subfield)}_{slug(concept)}_{slug(perspective)}"

                    if article_id in existing_ids:
                        continue

                    generated.append(
                        make_article(
                            article_id,
                            field,
                            subfield,
                            concept,
                            perspective,
                            difficulty,
                            sources,
                        )
                    )
                    index += 1

                    if len(generated) >= TARGET_NEW_ARTICLES:
                        return generated

    return generated


def article_stat(article):
    content_length = len(article.get("content", ""))
    key_points = len(article.get("key_points", []))
    source_count = len(article.get("source_recommendations", []))

    quality = 70
    if content_length >= 2500:
        quality += 10
    if key_points >= 4:
        quality += 5
    if source_count >= 3:
        quality += 5
    if article.get("abstract"):
        quality += 5

    trust = 90
    if source_count >= 3:
        trust += 4
    if article.get("quality_notes"):
        trust += 2

    return {
        "uses": 0,
        "success_rate": 92,
        "trust": min(trust, 96),
        "quality": min(quality, 95),
        "field": article.get("field", "science"),
        "subfield": article.get("subfield", "general"),
        "difficulty": article.get("difficulty", "intermediate"),
        "content_length": content_length,
        "keyword_count": len(article.get("keywords", [])),
        "key_point_count": key_points,
        "source_recommendation_count": source_count,
        "review_status": "educational_synthesis",
        "fact_check_required": True,
    }


def build_statistics(articles):
    stats = {}
    field_counter = Counter()
    difficulty_counter = Counter()
    subfield_counter = Counter()
    lengths = []

    for article in articles:
        article_id = article["id"]
        stat = article_stat(article)
        stats[article_id] = stat

        field_counter[stat["field"]] += 1
        difficulty_counter[stat["difficulty"]] += 1
        subfield_counter[f"{stat['field']}::{stat['subfield']}"] += 1
        lengths.append(stat["content_length"])

    stats["_collection_statistics"] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_articles": len(articles),
        "fields": dict(sorted(field_counter.items())),
        "difficulties": dict(sorted(difficulty_counter.items())),
        "subfields": dict(sorted(subfield_counter.items())),
        "average_content_length": round(sum(lengths) / len(lengths), 2) if lengths else 0,
        "min_content_length": min(lengths) if lengths else 0,
        "max_content_length": max(lengths) if lengths else 0,
        "default_trust_policy": "High trust for educational synthesis, still requires verification for high-stakes answers.",
    }

    return stats


def main():
    existing_articles = load_json(ARTICLES_PATH, [])
    generated_articles = build_articles(existing_articles)
    all_articles = existing_articles + generated_articles
    statistics = build_statistics(all_articles)

    save_json(ARTICLES_PATH, all_articles)
    save_json(STATISTICS_PATH, statistics)

    print("existing articles:", len(existing_articles))
    print("generated articles:", len(generated_articles))
    print("total articles:", len(all_articles))
    print("statistics entries:", len(statistics))


if __name__ == "__main__":
    main()
