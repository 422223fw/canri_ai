import json
from itertools import product
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "data"

TYPES_FILE = DATA_DIR / "Game_types.json"
MECHANICS_FILE = DATA_DIR / "Game_mechanics.json"
SYSTEMS_FILE = DATA_DIR / "Game_systems.json"
BALANCE_FILE = DATA_DIR / "Game_balance_rules.json"
GRAPH_FILE = DATA_DIR / "Game_design_graph.json"
STATS_FILE = DATA_DIR / "Game_statistics.json"


GAME_TYPES = [
    "platformer", "rpg", "puzzle", "survival", "strategy",
    "shooter", "racing", "simulation", "card_game", "adventure"
]

PERSPECTIVES = [
    "2d", "top_down", "side_scroller", "first_person", "third_person",
    "isometric", "text_based", "grid_based", "turn_based", "real_time"
]

TARGETS = [
    "beginner", "casual", "advanced", "children", "teens",
    "speedrunners", "story_players", "competitive", "solo", "co_op"
]

MECHANICS = [
    "movement", "jumping", "combat", "inventory", "crafting",
    "quests", "dialogue", "stealth", "resource_management", "building",
    "leveling", "score", "timer", "physics", "pathfinding",
    "enemy_ai", "save_load", "shop", "skills", "unlockables"
]

SYSTEMS = [
    "player_system", "enemy_system", "inventory_system", "combat_system",
    "level_system", "world_system", "ui_system", "audio_system",
    "save_system", "quest_system", "dialogue_system", "crafting_system",
    "physics_system", "input_system", "camera_system", "score_system",
    "progression_system", "economy_system", "network_system", "tutorial_system"
]

DIFFICULTIES = [
    "easy", "normal", "hard", "expert", "adaptive"
]


TYPE_CORE_LOOPS = {
    "platformer": ["move", "jump", "avoid hazards", "collect", "reach goal"],
    "rpg": ["explore", "talk", "fight", "collect loot", "level up"],
    "puzzle": ["observe", "test rule", "solve", "unlock", "advance"],
    "survival": ["gather", "craft", "manage needs", "avoid danger", "survive longer"],
    "strategy": ["collect resources", "build", "plan", "command units", "win objective"],
    "shooter": ["aim", "shoot", "take cover", "manage ammo", "clear area"],
    "racing": ["accelerate", "steer", "optimize route", "avoid mistakes", "finish fast"],
    "simulation": ["manage system", "observe feedback", "adjust", "expand", "optimize"],
    "card_game": ["draw", "choose card", "combine effects", "counter opponent", "win round"],
    "adventure": ["explore", "find clues", "use items", "solve obstacle", "progress story"]
}


TYPE_REQUIRED_SYSTEMS = {
    "platformer": ["player_system", "physics_system", "level_system", "enemy_system", "camera_system"],
    "rpg": ["player_system", "inventory_system", "combat_system", "quest_system", "save_system"],
    "puzzle": ["level_system", "input_system", "ui_system", "progression_system", "save_system"],
    "survival": ["inventory_system", "crafting_system", "world_system", "save_system", "enemy_system"],
    "strategy": ["economy_system", "enemy_system", "ui_system", "save_system", "network_system"],
    "shooter": ["player_system", "combat_system", "enemy_system", "camera_system", "audio_system"],
    "racing": ["physics_system", "camera_system", "score_system", "input_system", "level_system"],
    "simulation": ["economy_system", "ui_system", "save_system", "progression_system", "tutorial_system"],
    "card_game": ["ui_system", "progression_system", "enemy_system", "save_system", "tutorial_system"],
    "adventure": ["world_system", "dialogue_system", "quest_system", "inventory_system", "save_system"]
}


def difficulty_score(game_type, perspective, target, difficulty):
    score = 35
    if game_type in ["rpg", "strategy", "survival", "simulation"]:
        score += 20
    if perspective in ["first_person", "third_person", "isometric", "real_time"]:
        score += 12
    if target in ["competitive", "co_op", "speedrunners"]:
        score += 8
    if difficulty in ["hard", "expert", "adaptive"]:
        score += 15
    return min(score, 100)


def build_types():
    data = {}
    index = 1
    for game_type, perspective, target, difficulty in product(GAME_TYPES, PERSPECTIVES, TARGETS, DIFFICULTIES):
        item_id = f"game_type_{index:05d}_{game_type}_{perspective}_{target}_{difficulty}"
        score = difficulty_score(game_type, perspective, target, difficulty)
        data[item_id] = {
            "id": item_id,
            "game_type": game_type,
            "perspective": perspective,
            "target_audience": target,
            "difficulty_mode": difficulty,
            "core_loop": TYPE_CORE_LOOPS[game_type],
            "required_systems": TYPE_REQUIRED_SYSTEMS[game_type],
            "difficulty_score": score,
            "estimated_scope": "large" if score >= 75 else "medium" if score >= 55 else "small",
            "needed_brains": ["Planner_brain", "Creative_brain", "Code_brain", "Technology_brain"]
        }
        index += 1
    return data


def build_mechanics():
    data = {}
    index = 1
    for game_type, mechanic, difficulty, target in product(GAME_TYPES, MECHANICS, DIFFICULTIES, TARGETS):
        item_id = f"game_mechanic_{index:05d}_{game_type}_{mechanic}_{difficulty}"
        data[item_id] = {
            "id": item_id,
            "game_type": game_type,
            "mechanic": mechanic,
            "difficulty_mode": difficulty,
            "target_audience": target,
            "purpose": f"{mechanic.replace('_', ' ')} supports the {game_type} core loop.",
            "inputs": ["player action", "game state"],
            "outputs": ["state change", "feedback"],
            "quality_checks": [
                "mechanic is understandable",
                "feedback is immediate",
                "failure state is clear",
                "reward supports progression"
            ],
            "risk": "high" if mechanic in ["network_system", "physics", "enemy_ai"] else "medium"
        }
        index += 1
    return data


def build_systems():
    data = {}
    index = 1
    for game_type, system, perspective, target in product(GAME_TYPES, SYSTEMS, PERSPECTIVES, TARGETS):
        item_id = f"game_system_{index:05d}_{game_type}_{system}_{perspective}"
        data[item_id] = {
            "id": item_id,
            "game_type": game_type,
            "system": system,
            "perspective": perspective,
            "target_audience": target,
            "responsibility": f"{system.replace('_', ' ')} handles one major part of a {game_type} game.",
            "depends_on": dependencies_for_system(system),
            "feeds_into": feeds_for_system(system),
            "suggested_code_units": code_units_for_system(system),
            "needed_brains": ["Code_brain", "Planner_brain", "Technology_brain"]
        }
        index += 1
    return data


def dependencies_for_system(system):
    deps = {
        "enemy_system": ["player_system", "world_system"],
        "combat_system": ["player_system", "enemy_system"],
        "inventory_system": ["player_system"],
        "quest_system": ["dialogue_system", "world_system"],
        "save_system": ["player_system", "world_system"],
        "camera_system": ["player_system"],
        "score_system": ["player_system"],
        "crafting_system": ["inventory_system"],
        "network_system": ["input_system", "player_system"],
    }
    return deps.get(system, ["input_system"] if system != "input_system" else [])


def feeds_for_system(system):
    feeds = {
        "player_system": ["camera_system", "combat_system", "inventory_system"],
        "enemy_system": ["combat_system", "score_system"],
        "inventory_system": ["crafting_system", "quest_system"],
        "world_system": ["quest_system", "save_system"],
        "input_system": ["player_system", "ui_system"],
    }
    return feeds.get(system, ["ui_system"])


def code_units_for_system(system):
    base = system.replace("_system", "")
    return [
        f"{base}_class",
        f"{base}_update",
        f"{base}_serialize",
        f"{base}_validate"
    ]


def build_balance_rules():
    data = {}
    index = 1
    for game_type, mechanic, difficulty, target in product(GAME_TYPES, MECHANICS, DIFFICULTIES, TARGETS):
        item_id = f"game_balance_{index:05d}_{game_type}_{mechanic}_{difficulty}_{target}"
        data[item_id] = {
            "id": item_id,
            "game_type": game_type,
            "mechanic": mechanic,
            "difficulty_mode": difficulty,
            "target_audience": target,
            "rule": f"In {game_type}, {mechanic.replace('_', ' ')} should stay fair for {target} players.",
            "tuning_values": {
                "easy": {"enemy_pressure": 0.6, "reward_rate": 1.4, "forgiveness": 1.5},
                "normal": {"enemy_pressure": 1.0, "reward_rate": 1.0, "forgiveness": 1.0},
                "hard": {"enemy_pressure": 1.35, "reward_rate": 0.85, "forgiveness": 0.75},
                "expert": {"enemy_pressure": 1.7, "reward_rate": 0.7, "forgiveness": 0.5},
                "adaptive": {"enemy_pressure": "dynamic", "reward_rate": "dynamic", "forgiveness": "dynamic"}
            }.get(difficulty, {}),
            "signals_to_watch": ["fail rate", "time to complete", "resource starvation", "player confusion"],
            "fixes": ["increase feedback", "smooth difficulty curve", "reduce hidden punishment"]
        }
        index += 1
    return data


def build_design_graph():
    data = {}
    index = 1
    for game_type, perspective, system, mechanic in product(GAME_TYPES, PERSPECTIVES, SYSTEMS, MECHANICS):
        item_id = f"game_graph_{index:05d}_{game_type}_{perspective}_{system}_{mechanic}"
        data[item_id] = {
            "id": item_id,
            "game_type": game_type,
            "perspective": perspective,
            "system": system,
            "mechanic": mechanic,
            "requires": dependencies_for_system(system),
            "connects_to": list(dict.fromkeys(feeds_for_system(system) + [mechanic])),
            "design_order": design_order(system),
            "implementation_hint": f"Build {system} before polishing {mechanic}.",
            "graph_confidence": 82
        }
        index += 1
    return data


def design_order(system):
    order = {
        "input_system": 10,
        "player_system": 20,
        "world_system": 30,
        "level_system": 35,
        "enemy_system": 40,
        "combat_system": 50,
        "inventory_system": 50,
        "quest_system": 60,
        "ui_system": 70,
        "save_system": 85,
        "tutorial_system": 90
    }
    return order.get(system, 55)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    types = build_types()
    mechanics = build_mechanics()
    systems = build_systems()
    balance = build_balance_rules()
    graph = build_design_graph()
    stats = {
        "Game_brain": {
            "types": len(types),
            "mechanics": len(mechanics),
            "systems": len(systems),
            "balance_rules": len(balance),
            "design_graph": len(graph),
            "last_build": "generated"
        }
    }

    write_json(TYPES_FILE, types)
    write_json(MECHANICS_FILE, mechanics)
    write_json(SYSTEMS_FILE, systems)
    write_json(BALANCE_FILE, balance)
    write_json(GRAPH_FILE, graph)
    write_json(STATS_FILE, stats)

    print(json.dumps(stats["Game_brain"], indent=2))


if __name__ == "__main__":
    main()
