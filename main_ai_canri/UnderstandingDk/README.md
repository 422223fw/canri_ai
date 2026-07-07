📚 README.md מתוקן ל־UnderstandingDk
# 📚 UnderstandingDk

A Python dictionary + grammar + semantic connections engine.

---

# 🚀 Installation

Clone or copy the folder into your project:


YourProject/
├── main.py
└── UnderstandingDk/


---

# ⚡ Import

```python
from UnderstandingDk import *
📘 Full Command Reference
🔹 Core
Function	How to write	What it does
load	load()	Loads all dictionary, grammar, and connections data into memory
🔹 Search
Function	How to write	What it does
search_word	search_word("go")	Returns full data for a specific word
search_prefix	search_prefix("pro")	Finds words that start with a prefix
search_ending	search_ending("ing")	Finds words that end with a suffix
search_range	search_range("a-d")	Finds words within alphabetical range
search_length	search_length(5)	Finds words by exact length
search_length_range	search_length_range(3, 8)	Finds words within length range
search_type	search_type("verb")	Finds words by type
search_definition	search_definition("fast")	Searches inside definitions
🔹 Info
Function	How to write	What it does
get_meanings	get_meanings("run")	Returns all definitions of a word
get_all_words	get_all_words()	Returns all words in database
count_words	count_words()	Returns total number of words
get_word_types	get_word_types()	Returns available word types
word_exists	word_exists("go")	Checks if word exists
stats	stats()	Returns dictionary statistics
🔹 Connections
Function	How to write	What it does
related	related("love")	Returns related words
suggest	suggest("lov")	Suggests similar words
🔹 Random
Function	How to write	What it does
random_word	random_word()	Returns a random word
🔹 Grammar
Function	How to write	What it does
grammar_exists	grammar_exists("go")	Checks if word exists in grammar dictionary
get_forms	get_forms("go")	Returns verb forms (base/past/etc.)
get_tense	get_tense("go", "past")	Returns specific tense
convert_tense	convert_tense("go", "present", "past")	Converts between tenses
get_all_by_tense	get_all_by_tense("past")	Returns all words in a tense
detect_tense	detect_tense("went")	Detects tense of word
get_verb_base	get_verb_base("went")	Returns base form
🔹 Sentences
Function	How to write	What it does
analyze_sentence	analyze_sentence("I go home")	Analyzes sentence word by word
fix_sentence	fix_sentence("I go yesterday")	Fixes basic grammar mistakes
⚠️ Notes
Works offline
Loads JSON files automatically
Designed for learning, AI experiments, and language processing

