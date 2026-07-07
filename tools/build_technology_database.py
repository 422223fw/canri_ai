import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "data"


TECHNOLOGY_TERMS = {
    "software": {
        "domain": "software",
        "definition": "Programs, operating logic, and digital instructions that run on computing hardware.",
        "related": ["programming", "application", "operating system", "api", "database"],
        "use_cases": ["apps", "automation", "web systems", "tools"],
        "risks": ["bugs", "security vulnerabilities", "maintenance cost"],
        "needs_code": True,
    },
    "hardware": {
        "domain": "hardware",
        "definition": "Physical computing components such as processors, memory, storage, sensors, and boards.",
        "related": ["cpu", "gpu", "ram", "storage", "motherboard", "power supply"],
        "use_cases": ["computers", "robots", "embedded systems", "servers"],
        "risks": ["compatibility", "heat", "power limits", "physical failure"],
        "needs_code": False,
    },
    "cpu": {
        "domain": "hardware",
        "definition": "The central processing unit that executes instructions and coordinates general computing work.",
        "related": ["cores", "threads", "clock speed", "cache", "instruction set"],
        "use_cases": ["general computing", "compilation", "game logic", "server workloads"],
        "risks": ["bottleneck", "thermal throttling", "socket incompatibility"],
        "needs_code": False,
    },
    "gpu": {
        "domain": "hardware",
        "definition": "A graphics processing unit optimized for parallel processing, graphics rendering, and many AI workloads.",
        "related": ["vram", "cuda", "rendering", "parallel computing", "drivers"],
        "use_cases": ["gaming", "3d rendering", "machine learning", "video processing"],
        "risks": ["power demand", "driver issues", "vram limits", "cost"],
        "needs_code": False,
    },
    "ram": {
        "domain": "hardware",
        "definition": "Volatile memory used to hold active data and programs while a computer is running.",
        "related": ["memory", "ddr", "latency", "capacity", "bandwidth"],
        "use_cases": ["multitasking", "large files", "databases", "development tools"],
        "risks": ["insufficient capacity", "speed mismatch", "motherboard incompatibility"],
        "needs_code": False,
    },
    "ssd": {
        "domain": "hardware",
        "definition": "Solid-state storage that uses flash memory for fast persistent data access.",
        "related": ["nvme", "sata", "storage", "iops", "wear leveling"],
        "use_cases": ["operating systems", "applications", "databases", "game loading"],
        "risks": ["limited endurance", "capacity limits", "interface mismatch"],
        "needs_code": False,
    },
    "network": {
        "domain": "networking",
        "definition": "A system that connects computers and devices so they can exchange data.",
        "related": ["tcp", "ip", "dns", "router", "switch", "latency"],
        "use_cases": ["internet", "cloud systems", "multiplayer games", "iot"],
        "risks": ["packet loss", "latency", "misconfiguration", "security exposure"],
        "needs_code": False,
    },
    "api": {
        "domain": "software",
        "definition": "An application programming interface that defines how software components communicate.",
        "related": ["endpoint", "request", "response", "json", "authentication"],
        "use_cases": ["web apps", "integrations", "services", "automation"],
        "risks": ["breaking changes", "rate limits", "authentication mistakes"],
        "needs_code": True,
    },
    "database": {
        "domain": "data",
        "definition": "A structured system for storing, querying, and managing data.",
        "related": ["sql", "nosql", "index", "schema", "transaction"],
        "use_cases": ["user accounts", "analytics", "content storage", "search"],
        "risks": ["data loss", "slow queries", "schema mistakes", "security exposure"],
        "needs_code": True,
    },
    "cloud": {
        "domain": "cloud",
        "definition": "Remote computing infrastructure delivered as services over the internet.",
        "related": ["server", "storage", "scaling", "deployment", "availability"],
        "use_cases": ["hosting", "backups", "ai services", "distributed systems"],
        "risks": ["cost growth", "vendor lock-in", "network dependency", "misconfiguration"],
        "needs_code": False,
    },
    "cybersecurity": {
        "domain": "security",
        "definition": "The practice of protecting systems, networks, software, and data from unauthorized access or harm.",
        "related": ["authentication", "encryption", "vulnerability", "malware", "threat model"],
        "use_cases": ["safe apps", "account protection", "network defense", "secure coding"],
        "risks": ["data breach", "credential theft", "unsafe permissions"],
        "needs_code": False,
        "needs_security": True,
    },
    "encryption": {
        "domain": "security",
        "definition": "A method of transforming information so only authorized parties can read it.",
        "related": ["keys", "cipher", "tls", "hashing", "authentication"],
        "use_cases": ["secure messaging", "storage protection", "web security"],
        "risks": ["weak keys", "bad implementation", "lost keys"],
        "needs_code": True,
        "needs_security": True,
    },
    "artificial intelligence": {
        "domain": "ai",
        "definition": "Computer systems designed to perform tasks that normally require human-like reasoning, perception, or language understanding.",
        "related": ["machine learning", "neural network", "dataset", "model", "inference"],
        "use_cases": ["chatbots", "classification", "recommendations", "automation"],
        "risks": ["bias", "hallucination", "privacy", "evaluation gaps"],
        "needs_code": True,
    },
    "machine learning": {
        "domain": "ai",
        "definition": "A branch of AI where systems learn patterns from data instead of being explicitly programmed for every rule.",
        "related": ["training", "features", "labels", "model", "validation"],
        "use_cases": ["prediction", "classification", "computer vision", "language processing"],
        "risks": ["overfitting", "bad data", "bias", "unclear metrics"],
        "needs_code": True,
    },
    "robotics": {
        "domain": "robotics",
        "definition": "Technology that combines hardware, sensors, control systems, and software to make machines act in the physical world.",
        "related": ["sensor", "motor", "controller", "actuator", "feedback"],
        "use_cases": ["automation", "drones", "manufacturing", "education"],
        "risks": ["physical safety", "sensor noise", "power limits", "control errors"],
        "needs_code": True,
        "needs_security": True,
    },
    "microcontroller": {
        "domain": "electronics",
        "definition": "A small computer on a chip used to control hardware devices and embedded systems.",
        "related": ["arduino", "gpio", "sensor", "firmware", "pwm"],
        "use_cases": ["robots", "iot devices", "sensors", "automation"],
        "risks": ["voltage mismatch", "memory limits", "wiring mistakes"],
        "needs_code": True,
    },
    "operating system": {
        "domain": "systems",
        "definition": "System software that manages hardware resources and provides services for applications.",
        "related": ["kernel", "process", "memory", "filesystem", "driver"],
        "use_cases": ["desktop computers", "servers", "phones", "embedded devices"],
        "risks": ["driver issues", "permissions", "compatibility", "updates"],
        "needs_code": False,
    },
    "web application": {
        "domain": "software",
        "definition": "An application delivered through a browser using frontend, backend, and network technologies.",
        "related": ["html", "css", "javascript", "backend", "database", "api"],
        "use_cases": ["dashboards", "chat apps", "stores", "tools"],
        "risks": ["xss", "csrf", "slow performance", "bad authentication"],
        "needs_code": True,
        "needs_security": True,
    },
    "game engine": {
        "domain": "gaming_technology",
        "definition": "A software framework for building games, usually handling rendering, input, physics, audio, and assets.",
        "related": ["rendering", "physics", "animation", "assets", "input"],
        "use_cases": ["2d games", "3d games", "simulation", "interactive apps"],
        "risks": ["performance", "asset pipeline complexity", "platform compatibility"],
        "needs_code": True,
    },
    "internet of things": {
        "domain": "electronics",
        "definition": "A network of physical devices with sensors, software, and connectivity for collecting and exchanging data.",
        "related": ["sensor", "microcontroller", "wifi", "mqtt", "cloud"],
        "use_cases": ["smart home", "monitoring", "automation", "industry"],
        "risks": ["privacy", "weak authentication", "firmware updates", "network exposure"],
        "needs_code": True,
        "needs_security": True,
    },
}


HARDWARE_COMPONENTS = {
    "cpu": {
        "category": "processor",
        "role": "Executes general instructions and coordinates system logic.",
        "important_specs": ["core count", "thread count", "clock speed", "cache", "socket", "tdp"],
        "compatibility_checks": ["motherboard socket", "chipset support", "cooling capacity", "power delivery"],
        "common_bottlenecks": ["too few cores", "thermal throttling", "old architecture"],
    },
    "gpu": {
        "category": "graphics and acceleration",
        "role": "Renders graphics and accelerates parallel workloads such as AI and video processing.",
        "important_specs": ["vram", "memory bandwidth", "compute units", "power draw", "driver support"],
        "compatibility_checks": ["pcie slot", "power supply wattage", "case size", "monitor outputs"],
        "common_bottlenecks": ["low vram", "weak cooling", "driver instability"],
    },
    "ram": {
        "category": "memory",
        "role": "Stores active data for fast access while programs run.",
        "important_specs": ["capacity", "speed", "latency", "ddr generation", "channels"],
        "compatibility_checks": ["motherboard support", "cpu memory controller", "module count"],
        "common_bottlenecks": ["not enough capacity", "single-channel memory", "wrong speed profile"],
    },
    "motherboard": {
        "category": "platform",
        "role": "Connects the CPU, RAM, storage, expansion cards, and power delivery.",
        "important_specs": ["socket", "chipset", "ram slots", "pcie slots", "m.2 slots", "vrm quality"],
        "compatibility_checks": ["cpu socket", "case size", "bios support", "ram generation"],
        "common_bottlenecks": ["limited expansion", "weak vrm", "missing bios update"],
    },
    "power supply": {
        "category": "power",
        "role": "Converts wall power into stable voltages for computer components.",
        "important_specs": ["wattage", "efficiency rating", "connectors", "protections", "rail stability"],
        "compatibility_checks": ["gpu connectors", "cpu connector", "case fit", "total system power"],
        "common_bottlenecks": ["insufficient wattage", "low quality unit", "missing connectors"],
    },
    "sensor": {
        "category": "electronics",
        "role": "Measures physical conditions such as light, distance, temperature, motion, or pressure.",
        "important_specs": ["range", "accuracy", "sample rate", "interface", "voltage"],
        "compatibility_checks": ["microcontroller voltage", "i2c/spi/analog pins", "calibration needs"],
        "common_bottlenecks": ["noise", "poor calibration", "slow sampling"],
    },
}


STACK_TEMPLATES = {
    "ai_chat_system": {
        "goal": "Build an AI chat system",
        "recommended_stack": ["Python", "JSON data files", "Understanding_brain", "Memory_brain", "Manager_brain", "Response_brain"],
        "components": ["spelling", "understanding", "memory", "routing", "research", "response", "security"],
        "risks": ["bad data quality", "weak safety checks", "slow search in large JSON files"],
        "next_brains": ["Research_brain", "Security_brain", "Planner_brain"],
    },
    "web_app": {
        "goal": "Build a web application",
        "recommended_stack": ["HTML", "CSS", "JavaScript", "Python backend or Node backend", "database", "authentication"],
        "components": ["frontend", "backend", "api", "database", "auth", "deployment"],
        "risks": ["xss", "csrf", "bad authentication", "slow queries"],
        "next_brains": ["Code_brain", "Security_brain", "Research_brain"],
    },
    "robot_project": {
        "goal": "Build a robot or hardware automation project",
        "recommended_stack": ["microcontroller", "sensors", "motors", "power supply", "firmware", "safety testing"],
        "components": ["controller", "sensors", "actuators", "power", "control loop", "failsafe"],
        "risks": ["wrong voltage", "physical damage", "unsafe motion", "sensor noise"],
        "next_brains": ["Security_brain", "Code_brain", "Research_brain"],
    },
    "game_project": {
        "goal": "Build a game",
        "recommended_stack": ["game engine", "rendering", "input system", "physics", "assets", "save system"],
        "components": ["loop", "player", "world", "physics", "ui", "audio", "save data"],
        "risks": ["performance", "asset complexity", "scope creep"],
        "next_brains": ["Game_brain", "Code_brain", "Planner_brain"],
    },
    "secure_api": {
        "goal": "Build a secure API",
        "recommended_stack": ["backend framework", "authentication", "authorization", "input validation", "logging", "rate limiting"],
        "components": ["routes", "schema", "auth", "database", "tests", "monitoring"],
        "risks": ["injection", "broken authentication", "data exposure", "rate abuse"],
        "next_brains": ["Security_brain", "Code_brain", "Research_brain"],
    },
}


STATISTICS = {
    "Technology_brain": {
        "uses": 0,
        "success_rate": 90,
        "trust": 88,
        "local_terms": len(TECHNOLOGY_TERMS),
        "hardware_components": len(HARDWARE_COMPONENTS),
        "stack_templates": len(STACK_TEMPLATES),
    }
}


def save_json(name, data):
    path = DATA_DIR / name
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    save_json("Technology_terms.json", TECHNOLOGY_TERMS)
    save_json("Hardware_dictionary.json", HARDWARE_COMPONENTS)
    save_json("Tech_stack_templates.json", STACK_TEMPLATES)
    save_json("Technology_statistics.json", STATISTICS)

    print("Technology_terms.json:", len(TECHNOLOGY_TERMS))
    print("Hardware_dictionary.json:", len(HARDWARE_COMPONENTS))
    print("Tech_stack_templates.json:", len(STACK_TEMPLATES))
    print("Technology_statistics.json:", len(STATISTICS))


if __name__ == "__main__":
    main()
