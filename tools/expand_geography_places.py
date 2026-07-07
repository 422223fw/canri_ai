import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
PLACES_FILE = PROJECT_DIR / "main_ai_canri" / "data" / "Geography_places.json"


COUNTRIES = [
    ("canada", "North America", "North America", "Ottawa", ["united states", "arctic ocean", "atlantic ocean", "pacific ocean"]),
    ("mexico", "North America", "North America", "Mexico City", ["united states", "guatemala", "belize", "pacific ocean"]),
    ("argentina", "South America", "Southern Cone", "Buenos Aires", ["chile", "uruguay", "brazil", "atlantic ocean"]),
    ("chile", "South America", "Southern Cone", "Santiago", ["argentina", "peru", "bolivia", "pacific ocean"]),
    ("peru", "South America", "Andes", "Lima", ["ecuador", "colombia", "brazil", "pacific ocean"]),
    ("colombia", "South America", "Northern South America", "Bogota", ["venezuela", "ecuador", "peru", "caribbean sea"]),
    ("venezuela", "South America", "Northern South America", "Caracas", ["colombia", "brazil", "guyana", "caribbean sea"]),
    ("ecuador", "South America", "Andes", "Quito", ["colombia", "peru", "pacific ocean", "galapagos islands"]),
    ("bolivia", "South America", "Andes", "Sucre", ["peru", "chile", "argentina", "brazil"]),
    ("uruguay", "South America", "Southern Cone", "Montevideo", ["argentina", "brazil", "atlantic ocean"]),
    ("paraguay", "South America", "Central South America", "Asuncion", ["argentina", "brazil", "bolivia"]),
    ("guyana", "South America", "Guiana Shield", "Georgetown", ["venezuela", "brazil", "suriname", "atlantic ocean"]),
    ("suriname", "South America", "Guiana Shield", "Paramaribo", ["guyana", "french guiana", "brazil", "atlantic ocean"]),
    ("united kingdom", "Europe", "Northern Europe", "London", ["ireland", "north sea", "atlantic ocean", "english channel"]),
    ("ireland", "Europe", "Northern Europe", "Dublin", ["united kingdom", "atlantic ocean", "irish sea"]),
    ("germany", "Europe", "Western Europe", "Berlin", ["france", "poland", "netherlands", "denmark"]),
    ("spain", "Europe", "Southern Europe", "Madrid", ["france", "portugal", "mediterranean sea", "atlantic ocean"]),
    ("portugal", "Europe", "Southern Europe", "Lisbon", ["spain", "atlantic ocean"]),
    ("italy", "Europe", "Southern Europe", "Rome", ["france", "switzerland", "austria", "mediterranean sea"]),
    ("switzerland", "Europe", "Central Europe", "Bern", ["france", "germany", "italy", "austria"]),
    ("austria", "Europe", "Central Europe", "Vienna", ["germany", "czech republic", "hungary", "italy"]),
    ("netherlands", "Europe", "Western Europe", "Amsterdam", ["belgium", "germany", "north sea"]),
    ("belgium", "Europe", "Western Europe", "Brussels", ["france", "netherlands", "germany", "north sea"]),
    ("poland", "Europe", "Central Europe", "Warsaw", ["germany", "czech republic", "slovakia", "ukraine"]),
    ("czech republic", "Europe", "Central Europe", "Prague", ["germany", "poland", "austria", "slovakia"]),
    ("hungary", "Europe", "Central Europe", "Budapest", ["austria", "slovakia", "romania", "serbia"]),
    ("romania", "Europe", "Eastern Europe", "Bucharest", ["hungary", "ukraine", "bulgaria", "black sea"]),
    ("ukraine", "Europe", "Eastern Europe", "Kyiv", ["poland", "romania", "russia", "black sea"]),
    ("greece", "Europe", "Southern Europe", "Athens", ["albania", "north macedonia", "turkey", "aegean sea"]),
    ("turkey", "Europe/Asia", "Anatolia", "Ankara", ["greece", "bulgaria", "syria", "black sea"]),
    ("norway", "Europe", "Northern Europe", "Oslo", ["sweden", "finland", "north sea", "arctic ocean"]),
    ("sweden", "Europe", "Northern Europe", "Stockholm", ["norway", "finland", "baltic sea"]),
    ("finland", "Europe", "Northern Europe", "Helsinki", ["sweden", "norway", "russia", "baltic sea"]),
    ("denmark", "Europe", "Northern Europe", "Copenhagen", ["germany", "sweden", "north sea", "baltic sea"]),
    ("iceland", "Europe", "North Atlantic", "Reykjavik", ["atlantic ocean", "greenland", "norwegian sea"]),
    ("south africa", "Africa", "Southern Africa", "Pretoria", ["namibia", "botswana", "zimbabwe", "indian ocean"]),
    ("nigeria", "Africa", "West Africa", "Abuja", ["benin", "niger", "chad", "cameroon"]),
    ("kenya", "Africa", "East Africa", "Nairobi", ["tanzania", "uganda", "ethiopia", "indian ocean"]),
    ("ethiopia", "Africa", "Horn of Africa", "Addis Ababa", ["eritrea", "djibouti", "somalia", "kenya"]),
    ("morocco", "Africa", "North Africa", "Rabat", ["algeria", "spain", "atlantic ocean", "mediterranean sea"]),
    ("algeria", "Africa", "North Africa", "Algiers", ["morocco", "tunisia", "libya", "sahara desert"]),
    ("tunisia", "Africa", "North Africa", "Tunis", ["algeria", "libya", "mediterranean sea"]),
    ("libya", "Africa", "North Africa", "Tripoli", ["tunisia", "algeria", "egypt", "mediterranean sea"]),
    ("sudan", "Africa", "Northeast Africa", "Khartoum", ["egypt", "ethiopia", "south sudan", "red sea"]),
    ("ghana", "Africa", "West Africa", "Accra", ["cote d ivoire", "burkina faso", "togo", "atlantic ocean"]),
    ("senegal", "Africa", "West Africa", "Dakar", ["mauritania", "mali", "guinea", "atlantic ocean"]),
    ("tanzania", "Africa", "East Africa", "Dodoma", ["kenya", "uganda", "zambia", "indian ocean"]),
    ("uganda", "Africa", "East Africa", "Kampala", ["kenya", "tanzania", "south sudan", "lake victoria"]),
    ("rwanda", "Africa", "East Africa", "Kigali", ["uganda", "tanzania", "burundi", "democratic republic of the congo"]),
    ("angola", "Africa", "Southern Africa", "Luanda", ["namibia", "zambia", "democratic republic of the congo", "atlantic ocean"]),
    ("namibia", "Africa", "Southern Africa", "Windhoek", ["angola", "botswana", "south africa", "atlantic ocean"]),
    ("botswana", "Africa", "Southern Africa", "Gaborone", ["south africa", "namibia", "zimbabwe", "zambia"]),
    ("zimbabwe", "Africa", "Southern Africa", "Harare", ["zambia", "mozambique", "south africa", "botswana"]),
    ("saudi arabia", "Asia", "Middle East", "Riyadh", ["jordan", "iraq", "kuwait", "red sea"]),
    ("jordan", "Asia", "Middle East", "Amman", ["israel", "syria", "iraq", "saudi arabia"]),
    ("lebanon", "Asia", "Middle East", "Beirut", ["syria", "israel", "mediterranean sea"]),
    ("syria", "Asia", "Middle East", "Damascus", ["turkey", "iraq", "jordan", "lebanon"]),
    ("iraq", "Asia", "Middle East", "Baghdad", ["turkey", "iran", "syria", "saudi arabia"]),
    ("iran", "Asia", "Western Asia", "Tehran", ["iraq", "turkey", "pakistan", "caspian sea"]),
    ("united arab emirates", "Asia", "Arabian Peninsula", "Abu Dhabi", ["oman", "saudi arabia", "persian gulf"]),
    ("qatar", "Asia", "Arabian Peninsula", "Doha", ["saudi arabia", "persian gulf"]),
    ("oman", "Asia", "Arabian Peninsula", "Muscat", ["united arab emirates", "saudi arabia", "arabian sea"]),
    ("pakistan", "Asia", "South Asia", "Islamabad", ["india", "afghanistan", "iran", "arabian sea"]),
    ("bangladesh", "Asia", "South Asia", "Dhaka", ["india", "myanmar", "bay of bengal"]),
    ("nepal", "Asia", "South Asia", "Kathmandu", ["india", "china", "himalayas"]),
    ("sri lanka", "Asia", "South Asia", "Sri Jayawardenepura Kotte", ["india", "indian ocean"]),
    ("myanmar", "Asia", "Southeast Asia", "Naypyidaw", ["india", "china", "thailand", "bay of bengal"]),
    ("thailand", "Asia", "Southeast Asia", "Bangkok", ["myanmar", "laos", "cambodia", "malaysia"]),
    ("vietnam", "Asia", "Southeast Asia", "Hanoi", ["china", "laos", "cambodia", "south china sea"]),
    ("cambodia", "Asia", "Southeast Asia", "Phnom Penh", ["thailand", "laos", "vietnam"]),
    ("laos", "Asia", "Southeast Asia", "Vientiane", ["thailand", "vietnam", "china", "myanmar"]),
    ("malaysia", "Asia", "Southeast Asia", "Kuala Lumpur", ["thailand", "indonesia", "singapore", "south china sea"]),
    ("singapore", "Asia", "Southeast Asia", "Singapore", ["malaysia", "indonesia", "strait of malacca"]),
    ("indonesia", "Asia", "Southeast Asia", "Jakarta", ["malaysia", "papua new guinea", "indian ocean", "pacific ocean"]),
    ("philippines", "Asia", "Southeast Asia", "Manila", ["south china sea", "philippine sea", "taiwan"]),
    ("south korea", "Asia", "East Asia", "Seoul", ["north korea", "japan", "yellow sea", "sea of japan"]),
    ("north korea", "Asia", "East Asia", "Pyongyang", ["china", "south korea", "yellow sea", "sea of japan"]),
    ("mongolia", "Asia", "Central/East Asia", "Ulaanbaatar", ["russia", "china", "gobi desert"]),
    ("kazakhstan", "Asia", "Central Asia", "Astana", ["russia", "china", "uzbekistan", "caspian sea"]),
    ("uzbekistan", "Asia", "Central Asia", "Tashkent", ["kazakhstan", "kyrgyzstan", "tajikistan", "afghanistan"]),
    ("afghanistan", "Asia", "Central/South Asia", "Kabul", ["pakistan", "iran", "turkmenistan", "tajikistan"]),
    ("new zealand", "Oceania", "Oceania", "Wellington", ["australia", "pacific ocean", "tasman sea"]),
    ("papua new guinea", "Oceania", "Melanesia", "Port Moresby", ["indonesia", "solomon islands", "pacific ocean"]),
    ("fiji", "Oceania", "Melanesia", "Suva", ["pacific ocean", "tonga", "vanuatu"]),
    ("cuba", "North America", "Caribbean", "Havana", ["caribbean sea", "gulf of mexico", "bahamas"]),
    ("jamaica", "North America", "Caribbean", "Kingston", ["caribbean sea", "cuba", "haiti"]),
    ("haiti", "North America", "Caribbean", "Port-au-Prince", ["dominican republic", "caribbean sea", "atlantic ocean"]),
    ("dominican republic", "North America", "Caribbean", "Santo Domingo", ["haiti", "caribbean sea", "atlantic ocean"]),
]


CITIES = [
    ("london", "United Kingdom", "Europe", "Northern Europe"),
    ("berlin", "Germany", "Europe", "Western Europe"),
    ("rome", "Italy", "Europe", "Southern Europe"),
    ("madrid", "Spain", "Europe", "Southern Europe"),
    ("lisbon", "Portugal", "Europe", "Southern Europe"),
    ("amsterdam", "Netherlands", "Europe", "Western Europe"),
    ("brussels", "Belgium", "Europe", "Western Europe"),
    ("vienna", "Austria", "Europe", "Central Europe"),
    ("prague", "Czech Republic", "Europe", "Central Europe"),
    ("warsaw", "Poland", "Europe", "Central Europe"),
    ("athens", "Greece", "Europe", "Southern Europe"),
    ("istanbul", "Turkey", "Europe/Asia", "Marmara"),
    ("moscow", "Russia", "Europe", "Eastern Europe"),
    ("beijing", "China", "Asia", "East Asia"),
    ("shanghai", "China", "Asia", "East Asia"),
    ("seoul", "South Korea", "Asia", "East Asia"),
    ("bangkok", "Thailand", "Asia", "Southeast Asia"),
    ("singapore city", "Singapore", "Asia", "Southeast Asia"),
    ("jakarta", "Indonesia", "Asia", "Southeast Asia"),
    ("manila", "Philippines", "Asia", "Southeast Asia"),
    ("new delhi", "India", "Asia", "South Asia"),
    ("mumbai", "India", "Asia", "South Asia"),
    ("dubai", "United Arab Emirates", "Asia", "Middle East"),
    ("riyadh", "Saudi Arabia", "Asia", "Middle East"),
    ("cairo", "Egypt", "Africa", "North Africa"),
    ("nairobi", "Kenya", "Africa", "East Africa"),
    ("cape town", "South Africa", "Africa", "Southern Africa"),
    ("lagos", "Nigeria", "Africa", "West Africa"),
    ("toronto", "Canada", "North America", "North America"),
    ("vancouver", "Canada", "North America", "North America"),
    ("los angeles", "United States", "North America", "Western United States"),
    ("chicago", "United States", "North America", "Midwestern United States"),
    ("mexico city", "Mexico", "North America", "North America"),
    ("buenos aires", "Argentina", "South America", "Southern Cone"),
    ("santiago", "Chile", "South America", "Southern Cone"),
    ("lima", "Peru", "South America", "Andes"),
    ("bogota", "Colombia", "South America", "Northern South America"),
    ("sao paulo", "Brazil", "South America", "Brazil"),
    ("rio de janeiro", "Brazil", "South America", "Brazil"),
    ("sydney", "Australia", "Australia", "Oceania"),
    ("melbourne", "Australia", "Australia", "Oceania"),
    ("auckland", "New Zealand", "Oceania", "Oceania"),
]


FEATURES = [
    ("atlantic ocean", "ocean", "The Atlantic Ocean separates the Americas from Europe and Africa.", ["americas", "europe", "africa", "ocean"]),
    ("indian ocean", "ocean", "The Indian Ocean lies between Africa, Asia, Australia, and Antarctica.", ["africa", "asia", "australia", "ocean"]),
    ("arctic ocean", "ocean", "The Arctic Ocean surrounds the North Pole and borders northern Eurasia and North America.", ["arctic", "north pole", "ocean"]),
    ("southern ocean", "ocean", "The Southern Ocean surrounds Antarctica and connects the major southern ocean basins.", ["antarctica", "ocean", "circumpolar"]),
    ("red sea", "sea", "The Red Sea lies between Northeast Africa and the Arabian Peninsula.", ["egypt", "saudi arabia", "sudan", "sea"]),
    ("black sea", "sea", "The Black Sea is bordered by Eastern Europe, the Caucasus, and Anatolia.", ["turkey", "ukraine", "romania", "sea"]),
    ("caspian sea", "sea", "The Caspian Sea is the world's largest inland body of water.", ["kazakhstan", "russia", "iran", "inland sea"]),
    ("caribbean sea", "sea", "The Caribbean Sea lies southeast of the Gulf of Mexico and north of South America.", ["caribbean", "cuba", "jamaica", "sea"]),
    ("gulf of mexico", "gulf", "The Gulf of Mexico is an ocean basin bordered by the United States, Mexico, and Cuba.", ["mexico", "united states", "cuba", "gulf"]),
    ("andes", "mountain_range", "The Andes are the longest continental mountain range, running along western South America.", ["south america", "chile", "peru", "mountains"]),
    ("rocky mountains", "mountain_range", "The Rocky Mountains stretch through western North America.", ["canada", "united states", "mountains"]),
    ("alps", "mountain_range", "The Alps are a major European mountain system across several countries.", ["france", "switzerland", "italy", "austria"]),
    ("pyrenees", "mountain_range", "The Pyrenees form a mountain boundary between Spain and France.", ["spain", "france", "mountains"]),
    ("ural mountains", "mountain_range", "The Ural Mountains are often used as a geographic boundary between Europe and Asia.", ["russia", "eurasia", "mountains"]),
    ("gobi desert", "desert", "The Gobi Desert spans parts of Mongolia and northern China.", ["mongolia", "china", "desert"]),
    ("arabian desert", "desert", "The Arabian Desert covers much of the Arabian Peninsula.", ["saudi arabia", "oman", "desert"]),
    ("kalahari desert", "desert", "The Kalahari is a large semi-arid sandy region in Southern Africa.", ["botswana", "namibia", "south africa"]),
    ("amazon rainforest", "rainforest", "The Amazon rainforest is the largest tropical rainforest on Earth.", ["brazil", "peru", "colombia", "rainforest"]),
    ("congo river", "river", "The Congo River is a major river system in Central Africa.", ["central africa", "river", "rainforest"]),
    ("yangtze river", "river", "The Yangtze River is the longest river in Asia.", ["china", "river", "east asia"]),
    ("yellow river", "river", "The Yellow River is a major river in northern China.", ["china", "river", "loess"]),
    ("mississippi river", "river", "The Mississippi River is a major river system in North America.", ["united states", "river", "north america"]),
    ("danube river", "river", "The Danube River flows through or along many countries in Europe.", ["europe", "river", "central europe"]),
    ("rhine river", "river", "The Rhine River is a major river of Western and Central Europe.", ["germany", "netherlands", "switzerland"]),
    ("volga river", "river", "The Volga is the longest river in Europe.", ["russia", "river", "europe"]),
    ("mount everest", "mountain", "Mount Everest is the highest mountain above sea level.", ["himalayas", "nepal", "china", "mountain"]),
    ("mount kilimanjaro", "mountain", "Mount Kilimanjaro is the highest mountain in Africa.", ["tanzania", "africa", "mountain"]),
    ("mount fuji", "mountain", "Mount Fuji is a prominent volcanic mountain in Japan.", ["japan", "honshu", "volcano"]),
]


def load_places():
    if not PLACES_FILE.exists():
        return {}

    with PLACES_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def country_entry(name, continent, region, capital, nearby):
    return {
        "type": "country",
        "continent": continent,
        "region": region,
        "capital": capital,
        "summary": f"{name.title()} is a country in {region}, {continent}.",
        "key_facts": [
            f"{capital} is its capital.",
            f"It is part of the {region} geographic region.",
            "Its geography is described here as stable background knowledge; current statistics should be checked with Research_brain."
        ],
        "nearby": nearby,
        "keywords": [
            name,
            capital.lower(),
            continent.lower(),
            region.lower(),
            "country"
        ]
    }


def city_entry(name, country, continent, region):
    return {
        "type": "city",
        "country": country,
        "continent": continent,
        "region": region,
        "summary": f"{name.title()} is a major city in {country}.",
        "key_facts": [
            f"It is located in {region}.",
            f"It is useful for capital, location, regional, and map-related geography questions.",
            "Current population or live route data should be checked with Research_brain."
        ],
        "nearby": [
            country.lower(),
            region.lower()
        ],
        "keywords": [
            name,
            country.lower(),
            continent.lower(),
            region.lower(),
            "city"
        ]
    }


def feature_entry(name, feature_type, summary, keywords):
    return {
        "type": feature_type,
        "summary": summary,
        "key_facts": [
            summary,
            "This entry is geographic background knowledge.",
            "Precise current measurements should be checked with Research_brain."
        ],
        "nearby": keywords[:4],
        "keywords": list(dict.fromkeys([name, feature_type] + keywords))
    }


def main():
    places = load_places()

    for row in COUNTRIES:
        name, continent, region, capital, nearby = row
        places.setdefault(
            name,
            country_entry(name, continent, region, capital, nearby)
        )

    for row in CITIES:
        name, country, continent, region = row
        places.setdefault(
            name,
            city_entry(name, country, continent, region)
        )

    for row in FEATURES:
        name, feature_type, summary, keywords = row
        places.setdefault(
            name,
            feature_entry(name, feature_type, summary, keywords)
        )

    with PLACES_FILE.open("w", encoding="utf-8") as file:
        json.dump(places, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(json.dumps({
        "places": len(places),
        "countries_added": len(COUNTRIES),
        "cities_added": len(CITIES),
        "features_added": len(FEATURES)
    }, indent=2))


if __name__ == "__main__":
    main()
