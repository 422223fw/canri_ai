"""Build idempotent professional geography data and fast retrieval indexes."""

import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "main_ai_canri" / "data"


def load(name, default):
    path = DATA / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save(name, value):
    (DATA / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )


ADDITIONAL_COUNTRIES = [
    ("albania", "Tirana", "Europe", "Southern Europe"),
    ("andorra", "Andorra la Vella", "Europe", "Southern Europe"),
    ("armenia", "Yerevan", "Asia", "Western Asia"),
    ("azerbaijan", "Baku", "Asia", "Western Asia"),
    ("bahrain", "Manama", "Asia", "Middle East"),
    ("belarus", "Minsk", "Europe", "Eastern Europe"),
    ("belize", "Belmopan", "North America", "Central America"),
    ("benin", "Porto-Novo", "Africa", "West Africa"),
    ("bhutan", "Thimphu", "Asia", "South Asia"),
    ("bosnia and herzegovina", "Sarajevo", "Europe", "Southeastern Europe"),
    ("brunei", "Bandar Seri Begawan", "Asia", "Southeast Asia"),
    ("bulgaria", "Sofia", "Europe", "Southeastern Europe"),
    ("burkina faso", "Ouagadougou", "Africa", "West Africa"),
    ("burundi", "Gitega", "Africa", "East Africa"),
    ("cabo verde", "Praia", "Africa", "West Africa"),
    ("cameroon", "Yaounde", "Africa", "Central Africa"),
    ("central african republic", "Bangui", "Africa", "Central Africa"),
    ("chad", "N'Djamena", "Africa", "Central Africa"),
    ("comoros", "Moroni", "Africa", "East Africa"),
    ("costa rica", "San Jose", "North America", "Central America"),
    ("cote d'ivoire", "Yamoussoukro", "Africa", "West Africa"),
    ("cyprus", "Nicosia", "Asia", "Eastern Mediterranean"),
    ("democratic republic of the congo", "Kinshasa", "Africa", "Central Africa"),
    ("djibouti", "Djibouti", "Africa", "Horn of Africa"),
    ("dominica", "Roseau", "North America", "Caribbean"),
    ("el salvador", "San Salvador", "North America", "Central America"),
    ("eritrea", "Asmara", "Africa", "Horn of Africa"),
    ("estonia", "Tallinn", "Europe", "Northern Europe"),
    ("eswatini", "Mbabane", "Africa", "Southern Africa"),
    ("gabon", "Libreville", "Africa", "Central Africa"),
    ("gambia", "Banjul", "Africa", "West Africa"),
    ("georgia", "Tbilisi", "Asia", "Caucasus"),
    ("grenada", "St. George's", "North America", "Caribbean"),
    ("guatemala", "Guatemala City", "North America", "Central America"),
    ("guinea", "Conakry", "Africa", "West Africa"),
    ("guinea-bissau", "Bissau", "Africa", "West Africa"),
    ("honduras", "Tegucigalpa", "North America", "Central America"),
    ("kiribati", "South Tarawa", "Oceania", "Micronesia"),
    ("kuwait", "Kuwait City", "Asia", "Middle East"),
    ("kyrgyzstan", "Bishkek", "Asia", "Central Asia"),
    ("latvia", "Riga", "Europe", "Northern Europe"),
    ("lesotho", "Maseru", "Africa", "Southern Africa"),
    ("liberia", "Monrovia", "Africa", "West Africa"),
    ("liechtenstein", "Vaduz", "Europe", "Central Europe"),
    ("lithuania", "Vilnius", "Europe", "Northern Europe"),
    ("luxembourg", "Luxembourg", "Europe", "Western Europe"),
    ("madagascar", "Antananarivo", "Africa", "East Africa"),
    ("malawi", "Lilongwe", "Africa", "Southern Africa"),
    ("maldives", "Male", "Asia", "South Asia"),
    ("mali", "Bamako", "Africa", "West Africa"),
    ("malta", "Valletta", "Europe", "Southern Europe"),
    ("marshall islands", "Majuro", "Oceania", "Micronesia"),
    ("mauritania", "Nouakchott", "Africa", "West Africa"),
    ("mauritius", "Port Louis", "Africa", "East Africa"),
    ("micronesia", "Palikir", "Oceania", "Micronesia"),
    ("moldova", "Chisinau", "Europe", "Eastern Europe"),
    ("monaco", "Monaco", "Europe", "Western Europe"),
    ("montenegro", "Podgorica", "Europe", "Southeastern Europe"),
    ("mozambique", "Maputo", "Africa", "Southern Africa"),
    ("nicaragua", "Managua", "North America", "Central America"),
    ("niger", "Niamey", "Africa", "West Africa"),
    ("north macedonia", "Skopje", "Europe", "Southeastern Europe"),
    ("palau", "Ngerulmud", "Oceania", "Micronesia"),
    ("panama", "Panama City", "North America", "Central America"),
    ("republic of the congo", "Brazzaville", "Africa", "Central Africa"),
    ("saint kitts and nevis", "Basseterre", "North America", "Caribbean"),
    ("saint lucia", "Castries", "North America", "Caribbean"),
    ("saint vincent and the grenadines", "Kingstown", "North America", "Caribbean"),
    ("samoa", "Apia", "Oceania", "Polynesia"),
    ("san marino", "San Marino", "Europe", "Southern Europe"),
    ("sao tome and principe", "Sao Tome", "Africa", "Central Africa"),
    ("serbia", "Belgrade", "Europe", "Southeastern Europe"),
    ("seychelles", "Victoria", "Africa", "East Africa"),
    ("sierra leone", "Freetown", "Africa", "West Africa"),
    ("slovakia", "Bratislava", "Europe", "Central Europe"),
    ("slovenia", "Ljubljana", "Europe", "Central Europe"),
    ("solomon islands", "Honiara", "Oceania", "Melanesia"),
    ("somalia", "Mogadishu", "Africa", "Horn of Africa"),
    ("south sudan", "Juba", "Africa", "East Africa"),
    ("tajikistan", "Dushanbe", "Asia", "Central Asia"),
    ("timor-leste", "Dili", "Asia", "Southeast Asia"),
    ("togo", "Lome", "Africa", "West Africa"),
    ("tonga", "Nuku'alofa", "Oceania", "Polynesia"),
    ("trinidad and tobago", "Port of Spain", "North America", "Caribbean"),
    ("turkmenistan", "Ashgabat", "Asia", "Central Asia"),
    ("tuvalu", "Funafuti", "Oceania", "Polynesia"),
    ("vanuatu", "Port Vila", "Oceania", "Melanesia"),
    ("vatican city", "Vatican City", "Europe", "Southern Europe"),
    ("zambia", "Lusaka", "Africa", "Southern Africa"),
]


CONCEPT_GROUPS = {
    "location": ["absolute location", "relative location", "latitude", "longitude", "hemisphere", "equator", "prime meridian", "time zone", "map projection", "scale", "legend", "compass rose", "geocoding", "reverse geocoding", "great-circle distance"],
    "landforms": ["continent", "island", "archipelago", "peninsula", "isthmus", "cape", "plateau", "plain", "valley", "canyon", "basin", "delta", "dune", "oasis", "karst", "glacier", "volcano", "caldera", "fault", "mountain pass"],
    "water": ["ocean", "sea", "gulf", "bay", "strait", "channel", "river", "tributary", "watershed", "drainage basin", "lake", "lagoon", "wetland", "estuary", "aquifer", "groundwater", "waterfall", "floodplain"],
    "climate": ["weather", "climate", "climate zone", "tropical climate", "arid climate", "temperate climate", "continental climate", "polar climate", "monsoon", "rain shadow", "ocean current", "prevailing wind", "precipitation", "humidity", "drought", "cyclone"],
    "human geography": ["population density", "urbanization", "migration", "settlement", "metropolitan area", "capital city", "administrative division", "border", "landlocked country", "coastal country", "territory", "sovereignty", "cultural region", "economic geography", "transport corridor", "trade route"],
    "ecology": ["biome", "ecosystem", "rainforest", "savanna", "grassland", "desert", "tundra", "taiga", "biodiversity hotspot", "habitat", "conservation area", "national park", "natural resource", "soil", "erosion"]
}

CONCEPT_DEFINITIONS = {
    "absolute location": "The exact position of a place, commonly expressed with latitude and longitude.",
    "relative location": "The position of a place described in relation to other places, directions, or distances.",
    "latitude": "Angular distance north or south of the Equator, measured in degrees.",
    "longitude": "Angular distance east or west of the Prime Meridian, measured in degrees.",
    "hemisphere": "One half of Earth, usually divided into northern and southern or eastern and western halves.",
    "equator": "The imaginary line at zero degrees latitude that divides Earth into northern and southern hemispheres.",
    "prime meridian": "The reference line at zero degrees longitude used to measure east-west position.",
    "time zone": "A region that uses a common standard time, generally related to longitude and political boundaries.",
    "map projection": "A method for representing Earth's curved surface on a flat map, always with some distortion.",
    "scale": "The relationship between a distance on a map and the corresponding distance on the ground.",
    "geocoding": "The process of converting a place name or address into geographic coordinates.",
    "great-circle distance": "The shortest distance between two points measured along the surface of a sphere.",
    "archipelago": "A group or chain of islands located near one another.",
    "peninsula": "Land surrounded by water on most sides but connected to a larger landmass.",
    "isthmus": "A narrow strip of land connecting two larger land areas and separating bodies of water.",
    "plateau": "A broad area of elevated, relatively level land.",
    "plain": "A broad area of mostly flat or gently rolling land with limited relief.",
    "valley": "A low area between hills or mountains, often shaped by a river or glacier.",
    "basin": "A low or enclosed area in which water, sediment, or drainage collects.",
    "delta": "A landform built from sediment deposited where a river enters slower-moving water.",
    "glacier": "A persistent mass of ice that forms on land and moves slowly under its own weight.",
    "volcano": "An opening or landform through which magma, gases, and ash can reach Earth's surface.",
    "fault": "A fracture in Earth's crust along which blocks of rock have moved.",
    "strait": "A narrow natural waterway connecting two larger bodies of water.",
    "tributary": "A stream or river that flows into a larger river or lake.",
    "watershed": "A boundary of higher ground separating neighboring drainage basins; the term can also refer to a drainage area in some usage.",
    "drainage basin": "The land area where precipitation and streams drain toward the same river, lake, or other outlet.",
    "wetland": "Land that is permanently or seasonally saturated with water and supports water-adapted ecosystems.",
    "estuary": "A partly enclosed coastal body of water where river freshwater mixes with seawater.",
    "aquifer": "A permeable underground layer of rock or sediment that stores and transmits groundwater.",
    "floodplain": "Low land beside a river that is naturally subject to flooding.",
    "weather": "Short-term atmospheric conditions at a specific place and time.",
    "climate": "The long-term pattern and variability of weather conditions in a region.",
    "monsoon": "A seasonal reversal of prevailing winds that often produces distinct wet and dry periods.",
    "rain shadow": "A dry region on the sheltered side of mountains where descending air receives less precipitation.",
    "ocean current": "A persistent, directed movement of ocean water driven by wind, density differences, and Earth's rotation.",
    "precipitation": "Water falling from the atmosphere as rain, snow, sleet, or hail.",
    "population density": "The number of people living per unit of area.",
    "urbanization": "The growth of urban populations and the expansion or development of cities.",
    "migration": "The movement of people from one place to another for temporary or permanent settlement.",
    "metropolitan area": "A city and the surrounding communities that are socially and economically linked to it.",
    "administrative division": "A territorial unit created by a government for administration, such as a state, province, or district.",
    "border": "A line or zone separating political or geographic areas.",
    "landlocked country": "A country with no direct coastline on an ocean or open sea.",
    "biome": "A large ecological region characterized by climate, vegetation, and associated animal life.",
    "ecosystem": "A community of organisms interacting with one another and with their physical environment.",
    "biodiversity hotspot": "A region with exceptional concentrations of endemic species that also faces major habitat loss.",
    "erosion": "The removal and transport of soil or rock by water, wind, ice, or gravity."
}

ALIASES = {
    "united states": ["usa", "u.s.", "united states of america"],
    "united kingdom": ["uk", "u.k.", "britain", "great britain"],
    "united arab emirates": ["uae", "u.a.e."],
    "democratic republic of the congo": ["drc", "dr congo", "congo-kinshasa"],
    "republic of the congo": ["congo republic", "congo-brazzaville"],
    "cote d'ivoire": ["ivory coast", "cote d ivoire"],
    "czech republic": ["czechia"],
    "south korea": ["republic of korea"],
    "north korea": ["democratic people's republic of korea"],
    "russia": ["russian federation"],
}


def normalize_token(value):
    return re.findall(r"[a-zA-Z][a-zA-Z0-9'\-]{1,}", str(value).lower())


def enrich_places(places):
    for name, capital, continent, region in ADDITIONAL_COUNTRIES:
        places.setdefault(name, {
            "type": "country", "continent": continent, "region": region,
            "capital": capital,
            "summary": f"{name.title()} is a country in {region}, {continent}.",
            "key_facts": [f"{capital} is its capital.", f"It is part of {region}.", "Current statistics should be verified with Research_brain."],
            "nearby": [region.lower(), continent.lower()],
            "keywords": [name, capital.lower(), region.lower(), continent.lower(), "country"]
        })

    countries = [(name, data) for name, data in places.items() if data.get("type") == "country"]
    for country, data in countries:
        capital = str(data.get("capital", "")).strip()
        if capital and capital.lower() not in places:
            places[capital.lower()] = {
                "type": "city", "country": country.title(),
                "continent": data.get("continent", ""), "region": data.get("region", ""),
                "summary": f"{capital} is the capital city of {country.title()}.",
                "key_facts": [f"It is the capital of {country.title()}.", "Current population should be verified with Research_brain."],
                "nearby": [country, str(data.get("region", "")).lower()],
                "keywords": [capital.lower(), country, "capital", "city"]
            }

    for name, data in places.items():
        data["canonical_name"] = name
        data["aliases"] = list(dict.fromkeys(ALIASES.get(name, []) + data.get("aliases", [])))
        data["hierarchy"] = [
            {"level": key, "name": data[key]}
            for key in ["continent", "region", "country"]
            if data.get(key)
        ]
        data["stable_fields"] = [key for key in ["type", "continent", "region", "country", "capital", "coordinates"] if data.get(key) is not None]
        data["live_fields"] = ["population", "weather", "borders", "travel time", "political status"]
        data["verification_policy"] = "Use local data for stable geography and Research_brain for current or disputed facts."
        data["keywords"] = list(dict.fromkeys([name, data.get("type", "place")] + data.get("keywords", [])))
    return places


def build_concepts(existing):
    for category, names in CONCEPT_GROUPS.items():
        for name in names:
            existing.setdefault(name, {
                "definition": CONCEPT_DEFINITIONS.get(
                    name,
                    f"{name.title()} is a recognized concept used in {category} to describe geographic patterns, places, or processes."
                ),
                "category": category,
                "keywords": list(dict.fromkeys([name, category] + normalize_token(name))),
                "aliases": [], "examples": [],
                "related_concepts": [item for item in names if item != name][:6],
                "needs_live_lookup": name in {"weather", "border", "population density", "sovereignty"}
            })
            record = existing[name]
            if name in CONCEPT_DEFINITIONS or "geographic concept in the category" in str(record.get("definition", "")).lower():
                record["definition"] = CONCEPT_DEFINITIONS.get(
                    name,
                    f"{name.title()} is a recognized concept used in {category} to describe geographic patterns, places, or processes."
                )
            record.setdefault("category", category)
            record.setdefault("aliases", [])
            record.setdefault("examples", [])
            record.setdefault("related_concepts", [item for item in names if item != name][:6])
    return existing


def build_regions(existing, places):
    grouped = defaultdict(list)
    continents = defaultdict(list)
    for name, data in places.items():
        if data.get("region"):
            grouped[str(data["region"]).lower()].append(name)
        if data.get("continent"):
            continents[str(data["continent"]).lower()].append(name)
    for region, members in grouped.items():
        countries = [name for name in members if places[name].get("type") == "country"]
        existing.setdefault(region, {})
        existing[region].update({
            "description": existing[region].get("description") or f"{region.title()} is a geographic region represented by countries, cities, and natural features in the local database.",
            "continent": existing[region].get("continent") or next((places[name].get("continent") for name in members if places[name].get("continent")), ""),
            "countries": countries[:80], "major_places": members[:80],
            "keywords": list(dict.fromkeys([region, "region"] + normalize_token(region) + countries[:20]))
        })
    for continent, members in continents.items():
        existing.setdefault(continent, {
            "description": f"{continent.title()} is a continent-level geographic grouping.",
            "continent": continent.title(),
            "countries": [name for name in members if places[name].get("type") == "country"][:100],
            "major_places": members[:100],
            "keywords": [continent, "continent", "world region"]
        })
    return existing


def build_relations(places, regions):
    relations = {}
    region_members = defaultdict(list)
    for name, data in places.items():
        relation = {
            "nearby": list(dict.fromkeys(data.get("nearby", []))),
            "same_region": [], "capital_of": [], "has_capital": [],
            "located_in": [value for value in [data.get("country"), data.get("region"), data.get("continent")] if value]
        }
        if data.get("region"):
            region_members[str(data["region"]).lower()].append(name)
        if data.get("capital"):
            relation["has_capital"] = [str(data["capital"]).lower()]
        if data.get("type") == "city" and data.get("country"):
            country_key = str(data["country"]).lower()
            if country_key in places and str(places[country_key].get("capital", "")).lower() == name:
                relation["capital_of"] = [country_key]
        relations[name] = relation
    for region, members in region_members.items():
        for name in members:
            relations[name]["same_region"] = [item for item in members if item != name][:20]
    return relations


def build_creative_profiles(places):
    cues = {
        "country": ["contrasting regions", "capital and hinterland", "border transitions"],
        "city": ["street rhythm", "public spaces", "transport and neighborhoods"],
        "river": ["moving water", "banks and crossings", "upstream and downstream"],
        "mountain": ["thin air", "steep relief", "changing visibility"],
        "mountain_range": ["passes", "valleys", "snow lines"],
        "desert": ["dry wind", "wide horizons", "temperature contrast"],
        "ocean": ["open horizon", "currents", "weather fronts"],
        "sea": ["coasts", "ports", "changing light"],
        "rainforest": ["layered canopy", "humidity", "dense biodiversity"]
    }
    profiles = {}
    for name, data in places.items():
        profile_cues = cues.get(data.get("type"), ["terrain", "weather", "human movement"])
        profiles[name] = {
            "place": name, "type": data.get("type"),
            "setting_summary": data.get("summary", ""),
            "sensory_cues": profile_cues,
            "spatial_constraints": ["respect real scale", "keep the place hierarchy consistent", "separate stable facts from invented details"],
            "story_seeds": [
                f"A journey shaped by {profile_cues[0]} in {name.title()}.",
                f"A discovery connecting {name.title()} to {str(data.get('region', 'its region')).title()}.",
                f"A conflict caused by terrain, distance, or movement around {name.title()}."
            ],
            "related_places": data.get("nearby", [])[:8],
            "fact_boundary": "Creative details may be invented, but real geographic claims must use the factual place record."
        }
    return profiles


def build_query_patterns():
    intents = {
        "location_lookup": ["where is", "located", "location", "coordinates"],
        "capital_lookup": ["capital of", "capital city", "what is the capital"],
        "distance_lookup": ["distance between", "how far", "kilometers from"],
        "regional_comparison": ["compare", "difference between", "larger than"],
        "physical_geography": ["river", "mountain", "desert", "ocean", "landform"],
        "weather_lookup": ["weather", "forecast", "temperature today"],
        "population_lookup": ["population", "people live", "population density"],
        "border_lookup": ["border", "neighboring countries", "shares a border"],
        "route_lookup": ["route", "travel from", "directions", "map"],
        "geography_explanation": ["explain", "what is", "geography of"]
    }
    profiles = ["concise", "detailed", "student", "comparison", "map_ready", "fact_checked", "creative", "technical", "accessible", "structured"]
    focuses = ["identity", "hierarchy", "coordinates", "relations", "climate", "terrain", "human", "evidence", "uncertainty", "current_data"]
    patterns = {}
    for intent, markers in intents.items():
        for profile in profiles:
            for focus in focuses:
                key = f"geo_query_{intent}_{profile}_{focus}"
                patterns[key] = {
                    "id": key, "intent": intent, "markers": markers,
                    "profile": profile, "focus": focus,
                    "required_context": ["matched place", "place type", focus],
                    "needs_live_lookup": intent in {"weather_lookup", "population_lookup", "border_lookup", "route_lookup"},
                    "response_checks": ["answer the requested relation directly", "do not confuse similarly named places", "mark live data requirements"]
                }
    return patterns


def build_index(places, concepts, regions):
    terms = defaultdict(list)
    exact = defaultdict(list)
    records = {}
    for prefix, collection in [("place", places), ("concept", concepts), ("region", regions)]:
        for name, data in collection.items():
            reference = f"{prefix}:{name}"
            compact = {key: data.get(key) for key in ["type", "country", "continent", "region", "capital", "coordinates", "summary", "definition", "description", "nearby", "keywords", "aliases"] if data.get(key) not in [None, "", []]}
            compact["name"] = name
            compact["record_type"] = prefix
            records[reference] = compact
            aliases = [name] + data.get("aliases", [])
            for alias in aliases:
                exact[str(alias).lower()].append(reference)
            searchable = aliases + data.get("keywords", []) + data.get("nearby", [])
            searchable += [data.get(key, "") for key in ["type", "country", "continent", "region", "capital", "category"]]
            for value in searchable:
                normalized = str(value).lower().strip()
                if normalized:
                    terms[normalized].append(reference)
                for token in normalize_token(value):
                    terms[token].append(reference)
    return {
        "metadata": {"format": "geography_inverted_index_v1", "places": len(places), "concepts": len(concepts), "regions": len(regions)},
        "exact": {key: list(dict.fromkeys(value)) for key, value in exact.items()},
        "terms": {key: list(dict.fromkeys(value)) for key, value in terms.items()},
        "records": records
    }


def main():
    places = enrich_places(load("Geography_places.json", {}))
    concepts = build_concepts(load("Geography_concepts.json", {}))
    regions = build_regions(load("Geography_regions.json", {}), places)
    relations = build_relations(places, regions)
    profiles = build_creative_profiles(places)
    patterns = build_query_patterns()
    index = build_index(places, concepts, regions)
    save("Geography_places.json", places)
    save("Geography_concepts.json", concepts)
    save("Geography_regions.json", regions)
    save("Geography_relations.json", relations)
    save("Geography_creative_profiles.json", profiles)
    save("Geography_query_patterns.json", patterns)
    save("Geography_index.json", index)
    print(json.dumps({
        "places": len(places), "concepts": len(concepts), "regions": len(regions),
        "relations": len(relations), "creative_profiles": len(profiles),
        "query_patterns": len(patterns), "indexed_terms": len(index["terms"]),
        "indexed_records": len(index["records"])
    }, indent=2))


if __name__ == "__main__":
    main()
