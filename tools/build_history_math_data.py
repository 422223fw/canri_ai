"""Build indexed History and Math data without replacing existing databases."""

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "main_ai_canri" / "data"


def save(name, value):
    path = DATA / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


HISTORY_EVENTS = [
    ("writing_mesopotamia", "Early writing in Mesopotamia", -3200, "ancient", "Mesopotamia", "Cuneiform writing developed from accounting marks and enabled durable administration and literature."),
    ("old_kingdom_egypt", "Old Kingdom of Egypt", -2686, "ancient", "Egypt", "A centralized pharaonic state built major pyramid complexes and developed durable administrative institutions."),
    ("code_hammurabi", "Code of Hammurabi", -1754, "ancient", "Babylonia", "A Babylonian legal collection recorded judgments and social obligations under King Hammurabi."),
    ("athenian_democracy", "Development of Athenian democracy", -508, "classical", "Greece", "Reforms associated with Cleisthenes broadened citizen participation while excluding women, enslaved people, and foreigners."),
    ("roman_republic", "Roman Republic", -509, "classical", "Rome", "Rome replaced monarchy with republican institutions that distributed authority among magistrates, assemblies, and the Senate."),
    ("alexander_conquests", "Conquests of Alexander the Great", -334, "classical", "Eastern Mediterranean and Asia", "Alexander's campaigns defeated the Achaemenid Empire and accelerated Hellenistic cultural exchange."),
    ("qin_unification", "Qin unification of China", -221, "ancient", "China", "The Qin state unified competing kingdoms and standardized administration, weights, measures, writing practices, and infrastructure."),
    ("roman_empire_start", "Augustus and the Roman Empire", -27, "classical", "Rome", "Octavian became Augustus, establishing a durable imperial political order after decades of civil war."),
    ("han_silk_road", "Han expansion of Silk Road exchange", -130, "ancient", "Central and East Asia", "Han diplomacy and expansion strengthened long-distance exchange networks across Eurasia."),
    ("western_roman_fall", "End of the Western Roman Empire", 476, "late_antiquity", "Western Europe", "The removal of Romulus Augustulus conventionally marks the end of western imperial rule, though Roman institutions changed gradually."),
    ("hijra", "The Hijra", 622, "medieval", "Arabia", "Muhammad and his followers migrated from Mecca to Medina; the event anchors the Islamic calendar."),
    ("tang_dynasty", "Tang dynasty", 618, "medieval", "China", "Tang rule supported a large imperial state, examination culture, trade, urban growth, and artistic exchange."),
    ("magna_carta", "Magna Carta", 1215, "medieval", "England", "English barons compelled King John to accept a charter limiting some royal actions and affirming specified legal protections."),
    ("mongol_empire", "Expansion of the Mongol Empire", 1206, "medieval", "Eurasia", "Mongol conquests created the largest contiguous land empire and reshaped trade, warfare, and political connections."),
    ("black_death", "Black Death in Europe", 1347, "late_medieval", "Europe and Mediterranean", "A major plague pandemic killed a large share of the population and transformed labor, society, and religious life."),
    ("printing_press", "European movable-type printing", 1450, "early_modern", "Europe", "Johannes Gutenberg's printing system made the reproduction of texts faster and cheaper, expanding circulation of knowledge."),
    ("renaissance", "Renaissance", 1350, "early_modern", "Europe", "Renewed study of classical texts, urban patronage, artistic experimentation, and humanist scholarship reshaped European culture and education."),
    ("columbus_1492", "Columbus reaches the Caribbean", 1492, "early_modern", "Atlantic", "The voyage initiated sustained European colonization and intensified the Columbian Exchange with catastrophic consequences for Indigenous peoples."),
    ("protestant_reformation", "Protestant Reformation", 1517, "early_modern", "Europe", "Martin Luther's challenge to church practices helped trigger religious fragmentation, reform, and political conflict."),
    ("mughal_empire", "Foundation of the Mughal Empire", 1526, "early_modern", "South Asia", "Babur's victory at Panipat established a dynasty that later governed much of the Indian subcontinent."),
    ("scientific_revolution", "Scientific Revolution", 1543, "early_modern", "Europe", "New observations, mathematical methods, instruments, and institutions transformed explanations of nature."),
    ("english_civil_war", "English Civil Wars", 1642, "early_modern", "Britain", "Conflicts over sovereignty, religion, and taxation led to civil war, regicide, republican rule, and eventual constitutional change."),
    ("american_revolution", "American Revolution", 1775, "modern", "North America", "Thirteen colonies fought Britain and established an independent republic shaped by Enlightenment ideas and unresolved slavery."),
    ("french_revolution", "French Revolution", 1789, "modern", "France", "Fiscal crisis, inequality, political conflict, and popular mobilization overturned the monarchy and transformed citizenship and law."),
    ("haitian_revolution", "Haitian Revolution", 1791, "modern", "Caribbean", "Enslaved people in Saint-Domingue defeated colonial and imperial armies and founded independent Haiti in 1804."),
    ("industrial_revolution", "Industrial Revolution", 1760, "modern", "Britain and global economy", "Mechanization, fossil energy, factories, and new transport systems changed production, urbanization, labor, and the environment."),
    ("latin_independence", "Spanish American wars of independence", 1808, "modern", "Latin America", "Political crises in Spain and colonial movements produced new independent states across much of the Americas."),
    ("abolition_us", "Abolition of slavery in the United States", 1865, "modern", "United States", "The Thirteenth Amendment abolished slavery after the Civil War, though racial oppression continued through new institutions."),
    ("meiji_restoration", "Meiji Restoration", 1868, "modern", "Japan", "Political change restored imperial authority and accelerated centralized state-building, industrialization, and military reform."),
    ("scramble_africa", "Partition of Africa by European powers", 1884, "modern", "Africa", "European imperial states formalized territorial claims, often through violence and without African consent."),
    ("world_war_1", "First World War", 1914, "contemporary", "Global", "Alliance tensions, militarism, imperial rivalry, nationalism, and the Sarajevo assassination contributed to a global industrial war."),
    ("russian_revolution", "Russian Revolution", 1917, "contemporary", "Russia", "War, economic breakdown, and political crisis ended tsarist rule and enabled the Bolsheviks to seize power."),
    ("great_depression", "Great Depression", 1929, "contemporary", "Global", "Financial collapse, banking failures, falling demand, and policy errors produced prolonged unemployment and economic contraction."),
    ("world_war_2", "Second World War", 1939, "contemporary", "Global", "Expansionist dictatorships, unresolved postwar tensions, and failed collective security led to a global war and genocide."),
    ("united_nations", "Founding of the United Nations", 1945, "contemporary", "Global", "States created the United Nations to support collective security, diplomacy, development, and international cooperation."),
    ("india_independence", "Independence and partition of India", 1947, "contemporary", "South Asia", "British colonial rule ended as India and Pakistan became independent amid partition, displacement, and mass violence."),
    ("israel_established", "Establishment of the State of Israel", 1948, "contemporary", "Middle East", "Israel declared independence amid the end of the British Mandate, war, and the mass displacement of Palestinians known as the Nakba."),
    ("china_prc", "Founding of the People's Republic of China", 1949, "contemporary", "China", "The Chinese Communist Party established the PRC after victory in the Chinese Civil War."),
    ("decolonization_africa", "African decolonization", 1957, "contemporary", "Africa", "National movements and changing global conditions brought independence to most African colonies, with varied transitions and borders."),
    ("moon_landing", "Apollo 11 Moon landing", 1969, "contemporary", "Moon and United States", "Apollo 11 landed humans on the Moon, demonstrating major advances in computing, engineering, and spaceflight."),
    ("internet_arpanet", "ARPANET begins operation", 1969, "contemporary", "United States", "ARPANET connected research computers and helped develop networking methods that contributed to the modern Internet."),
    ("berlin_wall_fall", "Fall of the Berlin Wall", 1989, "contemporary", "Germany", "Mass protest, political reform, and East German policy failure opened the border and accelerated German reunification."),
    ("soviet_dissolution", "Dissolution of the Soviet Union", 1991, "contemporary", "Eurasia", "Political, national, and economic crises ended the USSR and produced fifteen independent states."),
    ("world_wide_web", "World Wide Web released publicly", 1991, "contemporary", "Global", "Tim Berners-Lee's web standards linked documents over the Internet and enabled broad public information publishing."),
]


CAUSES = {
    "world_war_1": ["alliance competition", "militarism", "imperial rivalry", "nationalism", "the assassination at Sarajevo"],
    "world_war_2": ["aggressive expansion", "the legacy of the First World War", "economic and political crisis", "failed collective security"],
    "french_revolution": ["fiscal crisis", "unequal taxation", "food-price pressure", "political conflict", "Enlightenment debate"],
    "industrial_revolution": ["capital and trade", "accessible coal", "technical innovation", "agricultural change", "labor and markets"],
    "roman_republic": ["rejection of monarchy", "elite competition", "citizen military organization"],
    "berlin_wall_fall": ["mass protest", "Soviet reform", "economic pressure", "a mistaken border announcement"],
}


CONSEQUENCES = {
    "world_war_1": ["mass casualties", "collapsed empires", "new borders", "political radicalization", "the League of Nations"],
    "world_war_2": ["mass death and genocide", "the United Nations", "decolonization", "Cold War rivalry", "new international institutions"],
    "french_revolution": ["end of feudal privileges", "republican politics", "war across Europe", "legal reform", "Napoleon's rise"],
    "industrial_revolution": ["factory production", "urbanization", "new social classes", "higher output", "pollution and labor conflict"],
    "printing_press": ["cheaper books", "faster circulation of ideas", "larger reading publics", "religious and scientific debate"],
    "berlin_wall_fall": ["German reunification", "weakened communist governments", "accelerated end of the Cold War"],
}


ALIASES = {
    "writing_mesopotamia": ["invention of writing", "early writing", "cuneiform writing"],
    "old_kingdom_egypt": ["ancient egypt", "egyptian civilization", "pyramid age"],
    "roman_empire_start": ["roman empire", "augustan empire"],
    "han_silk_road": ["silk road", "silk routes"],
    "printing_press": ["printing press", "gutenberg press"],
    "renaissance": ["the renaissance", "european renaissance"],
    "industrial_revolution": ["the industrial revolution"],
    "french_revolution": ["the french revolution"],
    "moon_landing": ["first moon landing", "apollo 11 moon landing"],
    "internet_arpanet": ["development of the internet", "internet development", "arpanet"],
    "world_wide_web": ["world wide web", "the web"],
}


FIGURES = {
    "cleisthenes": ("Cleisthenes", -570, -508, "Athens", "Political reformer associated with institutions that broadened citizen participation."),
    "augustus": ("Augustus", -63, 14, "Rome", "First Roman emperor, who built an imperial settlement after civil war."),
    "hammurabi": ("Hammurabi", -1810, -1750, "Babylonia", "King remembered for conquest, administration, and a major legal collection."),
    "muhammad": ("Muhammad", 570, 632, "Arabia", "Prophet of Islam and leader of the early Muslim community."),
    "gutenberg": ("Johannes Gutenberg", 1400, 1468, "Mainz", "Printer associated with a practical European movable-type printing system."),
    "martin_luther": ("Martin Luther", 1483, 1546, "Holy Roman Empire", "Theologian whose criticism of church practices helped begin the Protestant Reformation."),
    "newton": ("Isaac Newton", 1643, 1727, "England", "Mathematician and natural philosopher whose work unified terrestrial and celestial mechanics."),
    "washington": ("George Washington", 1732, 1799, "United States", "Military commander in the American Revolution and first U.S. president."),
    "toussaint": ("Toussaint Louverture", 1743, 1803, "Saint-Domingue", "Revolutionary leader central to the struggle against slavery and colonial rule."),
    "meiji": ("Emperor Meiji", 1852, 1912, "Japan", "Emperor during rapid political centralization and industrial transformation."),
    "gandhi": ("Mahatma Gandhi", 1869, 1948, "India", "Leader who developed mass nonviolent resistance against British colonial rule."),
    "turing": ("Alan Turing", 1912, 1954, "Britain", "Mathematician who made foundational contributions to computation and wartime cryptanalysis."),
    "berners_lee": ("Tim Berners-Lee", 1955, None, "Britain and CERN", "Inventor of the World Wide Web's foundational protocols and formats."),
}


def build_history():
    events = {}
    for event_id, title, year, era, region, summary in HISTORY_EVENTS:
        events[event_id] = {
            "id": event_id,
            "title": title,
            "start_year": year,
            "display_year": f"{abs(year)} BCE" if year < 0 else str(year),
            "era": era,
            "region": region,
            "summary": summary,
            "causes": CAUSES.get(event_id, []),
            "consequences": CONSEQUENCES.get(event_id, []),
            "keywords": sorted(set(title.lower().replace("'", "").split() + region.lower().split() + [era])),
            "aliases": ALIASES.get(event_id, []),
            "confidence": 92,
            "verification_status": "curated_stable_summary",
        }

    figures = {
        figure_id: {
            "id": figure_id, "name": value[0], "birth_year": value[1],
            "death_year": value[2], "region": value[3], "summary": value[4],
            "confidence": 92,
        }
        for figure_id, value in FIGURES.items()
    }

    timelines = {}
    for era in sorted({event[3] for event in HISTORY_EVENTS}):
        ids = [event[0] for event in HISTORY_EVENTS if event[3] == era]
        timelines[era] = {"id": era, "title": era.replace("_", " ").title(), "event_ids": ids}
    timelines["computing_history"] = {
        "id": "computing_history", "title": "Computing and network history",
        "event_ids": ["internet_arpanet", "world_wide_web"],
    }
    timelines["revolutions"] = {
        "id": "revolutions", "title": "Political and industrial revolutions",
        "event_ids": ["american_revolution", "french_revolution", "haitian_revolution", "industrial_revolution", "russian_revolution"],
    }

    index = {"terms": {}, "years": {}, "eras": {}, "regions": {}}
    for event_id, event in events.items():
        text = " ".join([event["title"], event["region"], event["era"], event["summary"]]).lower()
        terms = {word.strip(".,()") for word in text.split() if len(word.strip(".,()")) >= 3}
        for term in terms:
            index["terms"].setdefault(term, []).append(event_id)
        index["years"].setdefault(str(event["start_year"]), []).append(event_id)
        index["eras"].setdefault(event["era"], []).append(event_id)
        index["regions"].setdefault(event["region"].lower(), []).append(event_id)
    index["metadata"] = {"events": len(events), "figures": len(figures), "timelines": len(timelines), "format": 1}

    save("History_events.json", events)
    save("History_figures.json", figures)
    save("History_timelines.json", timelines)
    save("History_index.json", index)


FORMULAS = {
    "arithmetic_order": ("Order of operations", "parentheses, powers, multiplication/division, addition/subtraction", ["arithmetic", "expression", "pemdas"]),
    "percentage_of": ("Percentage of a number", "result = percent / 100 * whole", ["percent", "percentage", "of"]),
    "percentage_change": ("Percentage change", "change_percent = (new - old) / old * 100", ["increase", "decrease", "change"]),
    "linear_equation": ("Linear equation", "a*x + b = c; x = (c - b) / a", ["linear", "equation", "solve"]),
    "quadratic_formula": ("Quadratic formula", "x = (-b +/- sqrt(b^2 - 4*a*c)) / (2*a)", ["quadratic", "roots", "discriminant"]),
    "system_cramer": ("Two-variable linear system", "det = a*e - b*d; substitute or use determinants", ["system", "simultaneous", "equations"]),
    "mean": ("Arithmetic mean", "mean = sum(values) / count(values)", ["average", "mean", "statistics"]),
    "median": ("Median", "sort values and select the middle value or mean of two middle values", ["median", "statistics"]),
    "mode": ("Mode", "value or values with the greatest frequency", ["mode", "frequency", "statistics"]),
    "variance_population": ("Population variance", "variance = sum((x - mean)^2) / n", ["variance", "statistics"]),
    "simple_interest": ("Simple interest", "A = P * (1 + r*t)", ["interest", "principal", "rate"]),
    "compound_interest": ("Compound interest", "A = P * (1 + r/n)^(n*t)", ["compound", "interest", "finance"]),
    "rectangle_area": ("Rectangle area", "area = width * height", ["rectangle", "area"]),
    "triangle_area": ("Triangle area", "area = base * height / 2", ["triangle", "area"]),
    "circle_area": ("Circle area", "area = pi * radius^2", ["circle", "radius", "area"]),
    "circle_circumference": ("Circle circumference", "circumference = 2 * pi * radius", ["circle", "circumference"]),
    "pythagorean": ("Pythagorean theorem", "a^2 + b^2 = c^2", ["triangle", "hypotenuse", "pythagorean"]),
    "distance": ("Distance", "distance = speed * time", ["distance", "speed", "time"]),
    "probability": ("Simple probability", "probability = favorable outcomes / total outcomes", ["probability", "chance", "outcomes"]),
    "density": ("Density", "density = mass / volume", ["density", "mass", "volume"]),
}


def build_math():
    formulas = {
        formula_id: {"id": formula_id, "name": value[0], "formula": value[1], "trigger_terms": value[2], "verification": "substitute inputs and recompute"}
        for formula_id, value in FORMULAS.items()
    }

    levels = ["basic", "intermediate", "advanced", "word_problem", "verification"]
    styles = ["solve", "calculate", "explain", "check", "compare", "estimate", "derive", "apply", "reverse", "multi_step"]
    patterns = {}
    examples = {}
    index = {"terms": {}, "formula_patterns": {}}
    sequence = 0
    for formula_id, formula in formulas.items():
        index["formula_patterns"][formula_id] = []
        for level in levels:
            for style in styles:
                pattern_id = f"math_{formula_id}_{level}_{style}"
                patterns[pattern_id] = {
                    "id": pattern_id,
                    "formula_id": formula_id,
                    "level": level,
                    "style": style,
                    "trigger_terms": formula["trigger_terms"] + [style, level],
                    "solver_contract": ["parse values", "select formula", "show substitutions", "compute", "independently verify"],
                    "expected_output": ["answer", "steps", "verification", "confidence"],
                }
                index["formula_patterns"][formula_id].append(pattern_id)
                for term in patterns[pattern_id]["trigger_terms"]:
                    index["terms"].setdefault(term, []).append(pattern_id)

                a = sequence % 17 + 2
                b = sequence % 11 + 1
                example_id = f"example_{sequence:04d}"
                examples[example_id] = {
                    "id": example_id, "formula_id": formula_id, "level": level,
                    "inputs": [a, b], "instruction": f"{style.title()} a {level} {formula['name'].lower()} problem using {a} and {b}.",
                    "verification_required": True,
                }
                sequence += 1

    index["metadata"] = {"formulas": len(formulas), "patterns": len(patterns), "examples": len(examples), "format": 1}
    save("Math_formulas.json", formulas)
    save("Math_problem_patterns.json", patterns)
    save("Math_examples.json", examples)
    save("Math_index.json", index)


if __name__ == "__main__":
    build_history()
    build_math()
    print("Built professional History and Math data indexes.")
