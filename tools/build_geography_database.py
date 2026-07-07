import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "main_ai_canri" / "data"


PLACES = {
    "japan": {
        "type": "country",
        "continent": "Asia",
        "region": "East Asia",
        "capital": "Tokyo",
        "coordinates": {"lat": 36.2048, "lon": 138.2529},
        "summary": "Japan is an island country in East Asia, located in the northwest Pacific Ocean.",
        "key_facts": [
            "It consists of four large main islands and many smaller islands.",
            "Tokyo is its capital and largest metropolitan area.",
            "Japan lies along active tectonic plate boundaries, making earthquakes and volcanoes important geographic factors."
        ],
        "nearby": ["south korea", "china", "russia", "pacific ocean"],
        "keywords": ["island", "east asia", "tokyo", "pacific", "earthquakes"]
    },
    "israel": {
        "type": "country",
        "continent": "Asia",
        "region": "Middle East",
        "capital": "Jerusalem",
        "coordinates": {"lat": 31.0461, "lon": 34.8516},
        "summary": "Israel is a country in the Middle East on the eastern shore of the Mediterranean Sea.",
        "key_facts": [
            "It has Mediterranean coastal plains, central highlands, desert areas, and the Jordan Rift Valley.",
            "Jerusalem is the seat of government.",
            "The Dead Sea area is one of the lowest land elevations on Earth."
        ],
        "nearby": ["lebanon", "syria", "jordan", "egypt", "mediterranean sea"],
        "keywords": ["middle east", "jerusalem", "mediterranean", "dead sea", "desert"]
    },
    "france": {
        "type": "country",
        "continent": "Europe",
        "region": "Western Europe",
        "capital": "Paris",
        "coordinates": {"lat": 46.2276, "lon": 2.2137},
        "summary": "France is a Western European country with Atlantic, Mediterranean, and Alpine geography.",
        "key_facts": [
            "Paris is the capital.",
            "The country includes major rivers such as the Seine, Loire, Rhône, and Garonne.",
            "The Alps and Pyrenees form important mountain regions."
        ],
        "nearby": ["spain", "germany", "italy", "belgium", "switzerland"],
        "keywords": ["paris", "western europe", "alps", "seine", "mediterranean"]
    },
    "brazil": {
        "type": "country",
        "continent": "South America",
        "region": "Latin America",
        "capital": "Brasília",
        "coordinates": {"lat": -14.235, "lon": -51.9253},
        "summary": "Brazil is the largest country in South America and contains much of the Amazon Basin.",
        "key_facts": [
            "Brasília is the capital.",
            "The Amazon rainforest and Amazon River are central to its geography.",
            "Brazil has a long Atlantic coastline."
        ],
        "nearby": ["argentina", "peru", "colombia", "atlantic ocean", "amazon river"],
        "keywords": ["amazon", "south america", "brasilia", "rainforest", "atlantic"]
    },
    "egypt": {
        "type": "country",
        "continent": "Africa",
        "region": "North Africa",
        "capital": "Cairo",
        "coordinates": {"lat": 26.8206, "lon": 30.8025},
        "summary": "Egypt is a North African country centered geographically around the Nile River and its delta.",
        "key_facts": [
            "Cairo is the capital.",
            "The Nile River is the dominant geographic feature.",
            "Most of the country is desert, with dense settlement near the Nile."
        ],
        "nearby": ["libya", "sudan", "israel", "red sea", "mediterranean sea"],
        "keywords": ["nile", "cairo", "north africa", "desert", "delta"]
    },
    "united states": {
        "type": "country",
        "continent": "North America",
        "region": "North America",
        "capital": "Washington, D.C.",
        "coordinates": {"lat": 37.0902, "lon": -95.7129},
        "summary": "The United States is a large North American country spanning diverse climates, landforms, and time zones.",
        "key_facts": [
            "Washington, D.C. is the capital.",
            "Major physical regions include the Rocky Mountains, Great Plains, Appalachian Mountains, and Mississippi Basin.",
            "It borders Canada and Mexico and has coastlines on the Atlantic and Pacific Oceans."
        ],
        "nearby": ["canada", "mexico", "atlantic ocean", "pacific ocean"],
        "keywords": ["north america", "washington dc", "rocky mountains", "mississippi", "great plains"]
    },
    "china": {
        "type": "country",
        "continent": "Asia",
        "region": "East Asia",
        "capital": "Beijing",
        "coordinates": {"lat": 35.8617, "lon": 104.1954},
        "summary": "China is a large East Asian country with major plains, deserts, plateaus, mountains, and river systems.",
        "key_facts": [
            "Beijing is the capital.",
            "The Yangtze and Yellow Rivers are major geographic and historical features.",
            "Western China includes high plateaus and mountain ranges, while eastern China has densely populated plains."
        ],
        "nearby": ["mongolia", "russia", "india", "east china sea", "yellow sea"],
        "keywords": ["beijing", "yangtze", "yellow river", "east asia", "plateau"]
    },
    "india": {
        "type": "country",
        "continent": "Asia",
        "region": "South Asia",
        "capital": "New Delhi",
        "coordinates": {"lat": 20.5937, "lon": 78.9629},
        "summary": "India is a South Asian country shaped by the Himalayas, Indo-Gangetic Plain, Deccan Plateau, and monsoon climate.",
        "key_facts": [
            "New Delhi is the capital.",
            "The Himalayas form a major northern boundary.",
            "The Ganges River system and monsoon patterns strongly influence settlement and agriculture."
        ],
        "nearby": ["pakistan", "china", "nepal", "bangladesh", "indian ocean"],
        "keywords": ["new delhi", "south asia", "himalayas", "ganges", "monsoon"]
    },
    "australia": {
        "type": "country",
        "continent": "Australia",
        "region": "Oceania",
        "capital": "Canberra",
        "coordinates": {"lat": -25.2744, "lon": 133.7751},
        "summary": "Australia is a country and continent surrounded by the Indian and Pacific Oceans.",
        "key_facts": [
            "Canberra is the capital.",
            "Much of the interior is arid or semi-arid.",
            "The Great Barrier Reef lies off the northeast coast."
        ],
        "nearby": ["indian ocean", "pacific ocean", "new zealand", "indonesia"],
        "keywords": ["canberra", "oceania", "outback", "great barrier reef", "island continent"]
    },
    "russia": {
        "type": "country",
        "continent": "Europe/Asia",
        "region": "Eurasia",
        "capital": "Moscow",
        "coordinates": {"lat": 61.524, "lon": 105.3188},
        "summary": "Russia is the world's largest country by area, extending across Eastern Europe and northern Asia.",
        "key_facts": [
            "Moscow is the capital.",
            "It spans many time zones and includes tundra, taiga, steppe, mountains, and large river systems.",
            "Siberia makes up a large part of its territory."
        ],
        "nearby": ["china", "mongolia", "kazakhstan", "arctic ocean", "europe"],
        "keywords": ["moscow", "siberia", "eurasia", "arctic", "taiga"]
    },
    "tokyo": {
        "type": "city",
        "country": "Japan",
        "continent": "Asia",
        "region": "Kanto",
        "coordinates": {"lat": 35.6762, "lon": 139.6503},
        "summary": "Tokyo is the capital of Japan and one of the world's largest metropolitan areas.",
        "key_facts": [
            "It lies on the eastern side of Honshu, Japan's largest island.",
            "Tokyo is part of the Kanto region.",
            "It is a major political, economic, cultural, and transport center."
        ],
        "nearby": ["yokohama", "mount fuji", "pacific ocean", "honshu"],
        "keywords": ["capital", "japan", "kanto", "honshu", "metropolitan"]
    },
    "paris": {
        "type": "city",
        "country": "France",
        "continent": "Europe",
        "region": "Île-de-France",
        "coordinates": {"lat": 48.8566, "lon": 2.3522},
        "summary": "Paris is the capital of France, located on the Seine River in northern France.",
        "key_facts": [
            "It is the political and cultural center of France.",
            "The Seine River crosses the city.",
            "Paris is part of the Île-de-France region."
        ],
        "nearby": ["seine river", "versailles", "northern france"],
        "keywords": ["capital", "france", "seine", "ile de france"]
    },
    "new york city": {
        "type": "city",
        "country": "United States",
        "continent": "North America",
        "region": "Northeastern United States",
        "coordinates": {"lat": 40.7128, "lon": -74.006},
        "summary": "New York City is a major city in the northeastern United States, located where the Hudson River meets the Atlantic Ocean.",
        "key_facts": [
            "It is made up of five boroughs.",
            "Its harbor helped make it a major global trade and immigration center.",
            "It is not the capital of New York State; Albany is."
        ],
        "nearby": ["hudson river", "atlantic ocean", "new jersey", "long island"],
        "keywords": ["nyc", "hudson", "atlantic", "five boroughs", "northeast"]
    },
    "amazon river": {
        "type": "river",
        "continent": "South America",
        "region": "Amazon Basin",
        "coordinates": {"lat": -3.4653, "lon": -62.2159},
        "summary": "The Amazon River is one of the world's largest rivers and drains the Amazon Basin in South America.",
        "key_facts": [
            "It carries an enormous volume of freshwater.",
            "Its basin contains the Amazon rainforest.",
            "It is connected to major biodiversity and climate systems."
        ],
        "nearby": ["brazil", "peru", "amazon rainforest", "atlantic ocean"],
        "keywords": ["river", "amazon basin", "rainforest", "south america", "freshwater"]
    },
    "nile river": {
        "type": "river",
        "continent": "Africa",
        "region": "Northeast Africa",
        "coordinates": {"lat": 30.0444, "lon": 31.2357},
        "summary": "The Nile River is a major north-flowing river in northeastern Africa.",
        "key_facts": [
            "It has historically supported agriculture and settlement in Egypt and Sudan.",
            "It flows toward the Mediterranean Sea.",
            "Its basin includes multiple tributaries and source regions."
        ],
        "nearby": ["egypt", "sudan", "mediterranean sea", "cairo"],
        "keywords": ["river", "egypt", "africa", "delta", "mediterranean"]
    },
    "himalayas": {
        "type": "mountain_range",
        "continent": "Asia",
        "region": "South Asia",
        "coordinates": {"lat": 28.5983, "lon": 83.9311},
        "summary": "The Himalayas are a major mountain range in Asia, separating the Indian subcontinent from the Tibetan Plateau.",
        "key_facts": [
            "They include Mount Everest, the highest mountain above sea level.",
            "The range influences climate, rivers, and settlement patterns in South Asia.",
            "It formed from the collision of the Indian and Eurasian plates."
        ],
        "nearby": ["india", "nepal", "china", "tibetan plateau", "mount everest"],
        "keywords": ["mountains", "everest", "south asia", "plate tectonics", "nepal"]
    },
    "sahara desert": {
        "type": "desert",
        "continent": "Africa",
        "region": "North Africa",
        "coordinates": {"lat": 23.4162, "lon": 25.6628},
        "summary": "The Sahara is the largest hot desert in the world, covering much of North Africa.",
        "key_facts": [
            "It includes sand seas, rocky plateaus, mountains, and dry basins.",
            "Its climate is extremely arid.",
            "It spans parts of many North African countries."
        ],
        "nearby": ["egypt", "libya", "algeria", "mali", "niger"],
        "keywords": ["desert", "north africa", "arid", "sand", "hot desert"]
    },
    "pacific ocean": {
        "type": "ocean",
        "coordinates": {"lat": 0.0, "lon": -160.0},
        "summary": "The Pacific Ocean is the largest and deepest ocean on Earth.",
        "key_facts": [
            "It lies between Asia and Australia to the west and the Americas to the east.",
            "It contains many island chains and deep ocean trenches.",
            "The Pacific Ring of Fire is associated with frequent earthquakes and volcanoes around its margins."
        ],
        "nearby": ["asia", "australia", "north america", "south america", "ring of fire"],
        "keywords": ["ocean", "largest", "ring of fire", "trenches", "islands"]
    },
    "mediterranean sea": {
        "type": "sea",
        "coordinates": {"lat": 34.5531, "lon": 18.048},
        "summary": "The Mediterranean Sea lies between Southern Europe, North Africa, and Western Asia.",
        "key_facts": [
            "It connects to the Atlantic Ocean through the Strait of Gibraltar.",
            "It has strongly influenced trade, climate, and settlement around its shores.",
            "Many coastal regions have a Mediterranean climate with dry summers and mild wet winters."
        ],
        "nearby": ["europe", "north africa", "western asia", "gibraltar"],
        "keywords": ["sea", "europe", "north africa", "gibraltar", "mediterranean climate"]
    }
}


GEOGRAPHY_CONCEPTS = {
    "coordinates": {
        "definition": "Latitude and longitude values that identify a position on Earth.",
        "keywords": ["latitude", "longitude", "gps", "map", "position"],
        "needs_live_lookup": False
    },
    "gps": {
        "definition": "A satellite-based positioning system used to estimate location, movement, and time.",
        "keywords": ["coordinates", "location", "satellite", "navigation"],
        "needs_live_lookup": True
    },
    "climate": {
        "definition": "The long-term pattern of weather conditions in a region.",
        "keywords": ["temperature", "rainfall", "weather", "region", "season"],
        "needs_live_lookup": False
    },
    "weather": {
        "definition": "Short-term atmospheric conditions at a specific place and time.",
        "keywords": ["temperature", "rain", "wind", "forecast", "current"],
        "needs_live_lookup": True
    },
    "population": {
        "definition": "The number of people living in a place; this changes over time and should be verified with current data.",
        "keywords": ["people", "demographics", "census", "city", "country"],
        "needs_live_lookup": True
    },
    "border": {
        "definition": "A line or zone separating political or administrative areas.",
        "keywords": ["country", "boundary", "neighbor", "territory"],
        "needs_live_lookup": True
    },
    "capital": {
        "definition": "A city where a country's government is officially located.",
        "keywords": ["country", "government", "city"],
        "needs_live_lookup": False
    },
    "river": {
        "definition": "A natural flowing body of water that usually moves toward a sea, lake, or another river.",
        "keywords": ["water", "basin", "tributary", "delta"],
        "needs_live_lookup": False
    },
    "mountain": {
        "definition": "A high natural elevation of Earth's surface, often formed by tectonic or volcanic processes.",
        "keywords": ["elevation", "range", "peak", "tectonic"],
        "needs_live_lookup": False
    }
}


REGIONS = {
    "east asia": {
        "continent": "Asia",
        "description": "A region of Asia including countries such as China, Japan, South Korea, North Korea, Mongolia, and Taiwan in many geographic classifications.",
        "keywords": ["china", "japan", "korea", "mongolia", "pacific"]
    },
    "middle east": {
        "continent": "Asia/Africa",
        "description": "A transcontinental region around Western Asia and Egypt, important for deserts, seas, trade routes, and cultural history.",
        "keywords": ["western asia", "arabian peninsula", "levant", "persian gulf", "desert"]
    },
    "north africa": {
        "continent": "Africa",
        "description": "The northern part of Africa, strongly shaped by the Sahara Desert, Mediterranean coast, and Nile system.",
        "keywords": ["sahara", "egypt", "libya", "algeria", "mediterranean"]
    },
    "south asia": {
        "continent": "Asia",
        "description": "A region including India, Pakistan, Bangladesh, Nepal, Bhutan, Sri Lanka, and nearby areas.",
        "keywords": ["india", "himalayas", "ganges", "monsoon", "indian ocean"]
    },
    "western europe": {
        "continent": "Europe",
        "description": "A region of Europe with dense urban networks, Atlantic and Mediterranean influences, and major river systems.",
        "keywords": ["france", "germany", "benelux", "alps", "atlantic"]
    }
}


STATISTICS = {
    "Geography_brain": {
        "uses": 0,
        "success_rate": 90,
        "trust": 87,
        "places": len(PLACES),
        "concepts": len(GEOGRAPHY_CONCEPTS),
        "regions": len(REGIONS),
        "last_confidence": 0,
        "last_place": None
    }
}


def save_json(name, data):
    path = DATA_DIR / name
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    save_json("Geography_places.json", PLACES)
    save_json("Geography_concepts.json", GEOGRAPHY_CONCEPTS)
    save_json("Geography_regions.json", REGIONS)
    save_json("Geography_statistics.json", STATISTICS)

    print("Geography_places.json:", len(PLACES))
    print("Geography_concepts.json:", len(GEOGRAPHY_CONCEPTS))
    print("Geography_regions.json:", len(REGIONS))
    print("Geography_statistics.json:", len(STATISTICS))


if __name__ == "__main__":
    main()
