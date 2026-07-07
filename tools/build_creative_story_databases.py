import json
from itertools import product
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "data"

CREATIVE_SEEDS_FILE = DATA_DIR / "Creative_seed_bank.json"
CREATIVE_RULES_FILE = DATA_DIR / "Creative_scoring_rules.json"
CREATIVE_GRAPHS_FILE = DATA_DIR / "Creative_evolution_graphs.json"
CREATIVE_STATS_FILE = DATA_DIR / "Creative_statistics.json"

STORY_TEMPLATES_FILE = DATA_DIR / "Story_templates.json"
STORY_STRUCTURES_FILE = DATA_DIR / "Story_structures.json"
STORY_GENRES_FILE = DATA_DIR / "Story_genres.json"
STORY_STATS_FILE = DATA_DIR / "Story_statistics.json"

CHARACTER_TEMPLATES_FILE = DATA_DIR / "Character_templates.json"
CHARACTER_TRAITS_FILE = DATA_DIR / "Character_traits.json"
CHARACTER_STATS_FILE = DATA_DIR / "Character_statistics.json"

WORLD_TEMPLATES_FILE = DATA_DIR / "World_templates.json"
WORLD_RULES_FILE = DATA_DIR / "World_rules.json"
WORLD_STATS_FILE = DATA_DIR / "World_statistics.json"


DOMAINS = [
    "story", "code", "game", "science", "technology",
    "language", "geography", "history", "math", "security"
]

GENRES = [
    "fantasy", "science_fiction", "mystery", "adventure", "drama",
    "comedy", "horror", "historical", "superhero", "slice_of_life"
]

TONES = [
    "hopeful", "dark", "epic", "funny", "calm",
    "tense", "emotional", "mysterious", "warm", "tragic"
]

ARCHETYPES = [
    "reluctant_hero", "mentor", "trickster", "guardian", "rebel",
    "inventor", "detective", "wanderer", "healer", "rival"
]

TRAITS = [
    "brave", "curious", "impatient", "loyal", "secretive",
    "gentle", "ambitious", "anxious", "clever", "stubborn"
]

FLAWS = [
    "trusts too easily", "hides fear", "cannot forgive",
    "rushes decisions", "avoids responsibility", "lies to protect others",
    "needs control", "ignores warnings", "fears failure", "keeps secrets"
]

GOALS = [
    "find a lost truth", "protect a friend", "build something impossible",
    "escape a broken system", "solve an old mystery", "earn forgiveness",
    "save a home", "master a dangerous skill", "repair a mistake", "change a law"
]

WORLDS = [
    "floating_city", "desert_empire", "underwater_archive", "moon_colony",
    "ancient_forest", "clockwork_kingdom", "neon_megacity", "mountain_village",
    "memory_market", "storm_islands"
]

CONFLICTS = [
    "person_vs_self", "person_vs_society", "person_vs_nature",
    "person_vs_machine", "person_vs_fate", "person_vs_memory",
    "person_vs_time", "person_vs_family", "person_vs_truth", "person_vs_power"
]

STRUCTURES = {
    "three_act": ["setup", "inciting incident", "rising action", "climax", "resolution"],
    "hero_journey": ["ordinary world", "call to adventure", "trial", "ordeal", "return changed"],
    "mystery": ["strange event", "clues", "false lead", "reveal", "consequence"],
    "character_arc": ["want", "wound", "choice", "change", "new self"],
    "heist": ["target", "team", "plan", "complication", "escape"],
}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def build_creative_data():
    seeds = {}
    rules = {}
    graphs = {}
    index = 1

    for domain, genre, tone, archetype in product(DOMAINS, GENRES, TONES, ARCHETYPES):
        seed_id = f"creative_seed_{index:05d}_{domain}_{genre}_{tone}_{archetype}"
        seeds[seed_id] = {
            "id": seed_id,
            "domain": domain,
            "genre": genre,
            "tone": tone,
            "archetype": archetype,
            "ingredients": [
                genre,
                tone,
                archetype,
                GOALS[index % len(GOALS)],
                CONFLICTS[index % len(CONFLICTS)],
                WORLDS[index % len(WORLDS)]
            ],
            "prompt_shape": f"{tone} {genre} idea with a {archetype}",
            "novelty_bias": 60 + (index % 35),
            "coherence_bias": 70 + (index % 25)
        }
        rules[f"creative_rule_{index:05d}"] = {
            "id": f"creative_rule_{index:05d}",
            "domain": domain,
            "score_weights": {
                "relevance": 0.30,
                "novelty": 0.25,
                "coherence": 0.20,
                "usefulness": 0.15,
                "safety": 0.10
            },
            "stop_when": {
                "top_score_at_least": 88,
                "improvement_below": 2,
                "max_rounds": 5
            },
            "avoid": [
                "random contradiction",
                "unsafe instruction",
                "irrelevant weirdness",
                "copying one source too closely"
            ]
        }
        graphs[f"creative_graph_{index:05d}"] = {
            "id": f"creative_graph_{index:05d}",
            "seed_id": seed_id,
            "mutation_paths": [
                "swap genre",
                "invert flaw",
                "raise stakes",
                "change setting",
                "combine with memory term",
                "add constraint"
            ],
            "selection_rule": "keep high relevance and high novelty; reject incoherent ideas",
            "merge_strategy": "combine top concept, strongest conflict, and clearest goal"
        }
        index += 1

    return seeds, rules, graphs


def build_story_data():
    genres = {}
    structures = {}
    templates = {}

    for genre in GENRES:
        genres[genre] = {
            "genre": genre,
            "core_promises": [
                f"deliver a clear {genre} experience",
                "keep conflict visible",
                "make ending follow from character choice"
            ],
            "common_tones": TONES[:6],
            "recommended_structures": list(STRUCTURES.keys())
        }

    for name, steps in STRUCTURES.items():
        structures[name] = {
            "name": name,
            "steps": steps,
            "use_when": f"use {name} when the story needs this shape",
            "quality_checks": [
                "each scene changes something",
                "conflict escalates",
                "ending answers the central question"
            ]
        }

    index = 1
    for genre, tone, structure_name, conflict in product(GENRES, TONES, STRUCTURES, CONFLICTS):
        template_id = f"story_template_{index:05d}_{genre}_{tone}_{structure_name}"
        templates[template_id] = {
            "id": template_id,
            "genre": genre,
            "tone": tone,
            "structure": structure_name,
            "conflict_type": conflict,
            "default_outline": STRUCTURES[structure_name],
            "needed_brains": ["Creative_brain", "Character_brain", "World_brain", "Emotion_brain"],
            "difficulty": 45 + (index % 45),
            "confidence": 78 + (index % 18)
        }
        index += 1

    return genres, structures, templates


def build_character_data():
    templates = {}
    traits = {}
    index = 1

    for trait in TRAITS:
        traits[trait] = {
            "trait": trait,
            "strength": f"{trait} can help the character act decisively",
            "shadow": f"{trait} can become a problem under pressure",
            "development_question": f"when should {trait} help or hurt the character?"
        }

    for archetype, trait, flaw, goal, conflict in product(ARCHETYPES, TRAITS, FLAWS, GOALS, CONFLICTS):
        template_id = f"character_template_{index:05d}_{archetype}_{trait}"
        templates[template_id] = {
            "id": template_id,
            "archetype": archetype,
            "trait": trait,
            "flaw": flaw,
            "goal": goal,
            "conflict_type": conflict,
            "voice_style": TONES[index % len(TONES)],
            "arc": ["desire", "pressure", "mistake", "choice", "change"],
            "real_person_check_required": False,
            "confidence": 80 + (index % 15)
        }
        index += 1

    return traits, templates


def build_world_data():
    templates = {}
    rules = {}
    index = 1

    for world, genre, conflict, tone in product(WORLDS, GENRES, CONFLICTS, TONES):
        world_id = f"world_template_{index:05d}_{world}_{genre}"
        templates[world_id] = {
            "id": world_id,
            "world_type": world,
            "genre": genre,
            "tone": tone,
            "central_conflict": conflict,
            "systems": [
                "geography",
                "culture",
                "power_structure",
                "daily_life",
                "danger",
                "mystery"
            ],
            "hooks": [
                f"a secret hidden inside the {world}",
                f"a rule everyone in the {world} fears",
                f"a place in the {world} that should not exist"
            ],
            "confidence": 78 + (index % 17)
        }
        rules[f"world_rule_{index:05d}"] = {
            "id": f"world_rule_{index:05d}",
            "world_type": world,
            "rule": "world details must affect plot, not just decorate it",
            "consistency_checks": [
                "geography affects travel",
                "culture affects choices",
                "power structure creates conflict",
                "magic or technology has limits"
            ]
        }
        index += 1

    return templates, rules


def main():
    seeds, creative_rules, creative_graphs = build_creative_data()
    story_genres, story_structures, story_templates = build_story_data()
    character_traits, character_templates = build_character_data()
    world_templates, world_rules = build_world_data()

    write_json(CREATIVE_SEEDS_FILE, seeds)
    write_json(CREATIVE_RULES_FILE, creative_rules)
    write_json(CREATIVE_GRAPHS_FILE, creative_graphs)
    write_json(CREATIVE_STATS_FILE, {"Creative_brain": {"seeds": len(seeds), "rules": len(creative_rules), "graphs": len(creative_graphs)}})

    write_json(STORY_GENRES_FILE, story_genres)
    write_json(STORY_STRUCTURES_FILE, story_structures)
    write_json(STORY_TEMPLATES_FILE, story_templates)
    write_json(STORY_STATS_FILE, {"Story_brain": {"genres": len(story_genres), "structures": len(story_structures), "templates": len(story_templates)}})

    write_json(CHARACTER_TRAITS_FILE, character_traits)
    write_json(CHARACTER_TEMPLATES_FILE, character_templates)
    write_json(CHARACTER_STATS_FILE, {"Character_brain": {"traits": len(character_traits), "templates": len(character_templates)}})

    write_json(WORLD_TEMPLATES_FILE, world_templates)
    write_json(WORLD_RULES_FILE, world_rules)
    write_json(WORLD_STATS_FILE, {"World_brain": {"templates": len(world_templates), "rules": len(world_rules)}})

    print(json.dumps({
        "creative_seeds": len(seeds),
        "creative_rules": len(creative_rules),
        "creative_graphs": len(creative_graphs),
        "story_templates": len(story_templates),
        "character_templates": len(character_templates),
        "world_templates": len(world_templates)
    }, indent=2))


if __name__ == "__main__":
    main()
