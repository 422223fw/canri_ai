import importlib.util


for package in ["nltk", "wordnet", "wordfreq", "wordfreq_top_n", "wordninja"]:
    print(package, importlib.util.find_spec(package) is not None)

try:
    from nltk.corpus import wordnet as wn

    print("nltk_wordnet_synsets", len(list(wn.all_synsets())))
except Exception as exc:
    print("nltk_wordnet_error", type(exc).__name__, str(exc).splitlines()[0])
