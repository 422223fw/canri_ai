"""Deterministic high-signal instruction examples for CANRI's native model."""

from __future__ import annotations

from collections.abc import Iterator

from .instruction_dataset import InstructionExample


def _examples(
    prompts: tuple[str, ...],
    answer: str,
    source: str,
) -> Iterator[InstructionExample]:
    for prompt in prompts:
        yield InstructionExample(
            user=prompt,
            assistant=answer,
            source=source,
            quality=100.0,
        )


def iter_behavior_examples() -> Iterator[InstructionExample]:
    conversations = (
        (
            ("Hello, who are you?", "Hi. Introduce yourself in one short sentence."),
            "Hello, I am Canri, an AI assistant. What would you like help with?",
        ),
        (
            ("Good morning.", "Say good morning and ask how you can help."),
            "Good morning. How can I help you today?",
        ),
        (
            ("Can we talk for a moment?", "I would like to have a short conversation."),
            "Of course. What would you like to talk about?",
        ),
        (
            ("Thank you for helping me.", "I appreciate your help."),
            "You are welcome. I am glad I could help.",
        ),
        (
            ("I did not understand that answer.", "Please respond more clearly."),
            "I will explain it more clearly and focus directly on your question.",
        ),
    )
    for prompts, answer in conversations:
        yield from _examples(prompts, answer, "generated_behavior_conversation_en")

    hebrew_conversations = (
        (("שלום, מי אתה?", "הצג את עצמך בקצרה."), "שלום, אני Canri, עוזר בינה מלאכותית. במה אוכל לעזור?"),
        (("בוקר טוב.", "אמור לי בוקר טוב ושאל איך אפשר לעזור."), "בוקר טוב. איך אוכל לעזור לך היום?"),
        (("אפשר לדבר איתך?", "אני רוצה לנהל שיחה קצרה."), "כמובן. על מה תרצה לדבר?"),
        (("תודה שעזרת לי.", "אני מעריך את העזרה שלך."), "בשמחה. אני שמח שעזרתי."),
        (("לא הבנתי את התשובה.", "תסביר את זה בצורה ברורה יותר."), "אסביר שוב בצורה פשוטה וישירה יותר."),
    )
    for prompts, answer in hebrew_conversations:
        yield from _examples(prompts, answer, "generated_behavior_conversation_he")

    support_pairs = (
        (
            ("I had a difficult and exhausting day.", "Today was stressful and I feel tired."),
            "That sounds exhausting. Give yourself a moment to rest, then choose one small thing that would make tonight easier. What part of the day felt hardest?",
        ),
        (
            ("I am nervous about a test tomorrow.", "I feel anxious about tomorrow's exam."),
            "It makes sense to feel nervous. Review one small topic, prepare what you need, and leave time for sleep. Which topic worries you most?",
        ),
        (
            ("I made a mistake and feel disappointed.", "I am upset with myself because I failed."),
            "A mistake can hurt without defining you. Identify what went wrong, choose one repair you can make, and treat the result as information for the next attempt.",
        ),
    )
    for prompts, answer in support_pairs:
        yield from _examples(prompts, answer, "generated_behavior_emotional_support")

    hebrew_support = (
        (
            ("היה לי יום קשה ומעייף.", "היום היה מלחיץ ואני עייף."),
            "זה נשמע מתיש. כדאי לעצור לרגע, לנוח, ולבחור דבר קטן אחד שיקל על הערב. מה היה החלק הקשה ביותר ביום?",
        ),
        (
            ("אני לחוץ בגלל מבחן מחר.", "אני מפחד מהמבחן של מחר."),
            "זה טבעי להרגיש לחץ. התמקד בנושא קטן אחד, הכן את הדברים מראש והשאר זמן לשינה. איזה נושא הכי מדאיג אותך?",
        ),
    )
    for prompts, answer in hebrew_support:
        yield from _examples(prompts, answer, "generated_behavior_conversation_he")

    science_facts = (
        ("gravity", "Gravity is the attraction between objects with mass. Near Earth, it pulls objects toward the planet's center and gives them weight."),
        ("photosynthesis", "Photosynthesis is the process plants use to convert light energy, water, and carbon dioxide into sugars, releasing oxygen."),
        ("electric current", "Electric current is the rate at which electric charge moves through a material. It is measured in amperes."),
        ("an atom", "An atom is a basic unit of matter made of a nucleus containing protons and neutrons, surrounded by electrons."),
        ("the water cycle", "The water cycle moves water through evaporation, condensation, precipitation, and collection."),
        ("DNA", "DNA is the molecule that stores hereditary instructions used by living cells to develop and function."),
        ("friction", "Friction is a force that opposes relative motion between surfaces in contact and often converts motion into heat."),
        ("a computer processor", "A processor executes instructions by performing arithmetic, logic, control, and data movement operations."),
    )
    for subject, answer in science_facts:
        prompts = (
            f"Explain {subject} in simple language.",
            f"What is {subject}? Give a direct factual answer.",
            f"Give me a short and reliable explanation of {subject}.",
        )
        yield from _examples(prompts, answer, "generated_behavior_science")

    task_pairs = (
        (
            ("Return only the word ready, with no explanation.", "Output one word only: ready."),
            "ready",
        ),
        (
            ("Give exactly three colors as a numbered list.", "List three colors and nothing else."),
            "1. Red\n2. Green\n3. Blue",
        ),
        (
            ("Answer in one sentence: why is sleep important?", "Explain the value of sleep using one sentence only."),
            "Sleep supports memory, physical recovery, emotional regulation, and healthy brain function.",
        ),
        (
            ("Rewrite this politely: Send it now.", "Make this sentence polite: Give me the file."),
            "Could you please send it now?",
        ),
        (
            ("Summarize this in five words: Regular practice improves difficult skills over time.",),
            "Practice steadily improves difficult skills.",
        ),
    )
    for prompts, answer in task_pairs:
        yield from _examples(prompts, answer, "generated_behavior_task_following")

    for index in range(120):
        left = 3 + index % 37
        right = 2 + (index * 5) % 29
        yield InstructionExample(
            user=(
                f"Add {left} and {right}. Return only the integer result, "
                "without a label or explanation."
            ),
            assistant=str(left + right),
            source="generated_behavior_task_following",
            quality=100.0,
        )
        words = (f"delta{index}", f"alpha{index}", f"charlie{index}")
        yield InstructionExample(
            user=(
                "Sort these three values alphabetically and return one "
                f"comma-separated line: {', '.join(words)}"
            ),
            assistant=", ".join(sorted(words)),
            source="generated_behavior_task_following",
            quality=100.0,
        )
        yield InstructionExample(
            user=(
                f"Return a JSON object with exactly two keys: item set to "
                f"\"entry-{index}\" and active set to true."
            ),
            assistant=f'{{"item":"entry-{index}","active":true}}',
            source="generated_behavior_task_following",
            quality=100.0,
        )

    for index in range(80):
        number = 10 + index
        answer = "כן" if number % 2 == 0 else "לא"
        yield InstructionExample(
            user=f"האם המספר {number} זוגי? החזר רק כן או לא.",
            assistant=answer,
            source="generated_behavior_task_following",
            quality=100.0,
        )

    context_pairs = (
        (
            "Earlier I chose the project name Aurora. What project name did I choose?",
            "You chose the project name Aurora.",
        ),
        (
            "My previous message said the meeting is on Tuesday at 10:00. When is the meeting?",
            "The meeting is on Tuesday at 10:00.",
        ),
        (
            "Continue this sentence naturally: The small door opened, and behind it",
            "The small door opened, and behind it shimmered a quiet city no larger than a suitcase.",
        ),
        (
            "We were discussing gravity. Continue with one everyday example.",
            "For example, when you release a ball, gravity accelerates it toward the ground.",
        ),
        (
            "I asked for a Python program, not a story. Correct the direction of the answer.",
            "Understood. I will provide the requested Python program and preserve its stated requirements.",
        ),
    )
    for prompt, answer in context_pairs:
        yield InstructionExample(
            user=prompt,
            assistant=answer,
            source="generated_behavior_context",
            quality=100.0,
        )

    for index in range(120):
        project = f"Project-{index:03d}"
        yield InstructionExample(
            user=(
                f"Earlier in this conversation I selected the name {project}. "
                "Reply with the selected name only."
            ),
            assistant=project,
            source="generated_behavior_context",
            quality=100.0,
        )

    for index in range(80):
        chosen = 20 + index
        yield InstructionExample(
            user=f"קודם בשיחה בחרתי במספר {chosen}. החזר רק את המספר שבחרתי.",
            assistant=str(chosen),
            source="generated_behavior_context",
            quality=100.0,
        )


def _code_example(prompt: str, code: str) -> InstructionExample:
    return InstructionExample(
        user=prompt,
        assistant=f"```python\n{code.strip()}\n```",
        source="generated_behavior_code",
        quality=100.0,
    )


def iter_code_behavior_examples() -> Iterator[InstructionExample]:
    greeting_loop = '''
def main():
    while True:
        name = input("Name (or exit): ").strip()
        if name.casefold() == "exit":
            break
        if not name:
            print("Please enter a name.")
            continue
        print(f"Hello, {name}!")


if __name__ == "__main__":
    main()
'''
    for prompt in (
        "Write a runnable Python program that greets names until the user enters exit. Return only code.",
        "Create a terminal greeting loop in Python. Empty names must be rejected and exit must stop it. Output code only.",
        "Build a complete Python name greeter with safe input and an exit command. Give only the final code.",
    ):
        yield _code_example(prompt, greeting_loop)

    safe_number = '''
def read_number(prompt):
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Please enter a valid number.")


def main():
    left = read_number("First number: ")
    right = read_number("Second number: ")
    print(f"Total: {left + right:g}")


if __name__ == "__main__":
    main()
'''
    for prompt in (
        "Return only a complete Python program that safely reads two numbers and prints their sum.",
        "Write runnable Python code for adding two user-entered numbers, retrying invalid input.",
        "Create a standard-library terminal number adder with input validation. Output only code.",
    ):
        yield _code_example(prompt, safe_number)

    json_store = '''
import json
from pathlib import Path

DATA_FILE = Path("items.json")


def load_items():
    if not DATA_FILE.exists():
        return []
    try:
        value = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def save_items(items):
    DATA_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
'''
    for prompt in (
        "Write Python functions that safely save and load a list from items.json. Return only code.",
        "Create standard-library JSON persistence for a list, including missing and invalid file handling.",
        "Give complete Python code for robust list loading and saving with pathlib and JSON.",
    ):
        yield _code_example(prompt, json_store)

    syntax_fix = '''
def main():
    print("Program started.")


if __name__ == "__main__":
    main()
'''
    for prompt in (
        "Fix the Python entry-point syntax and return only the corrected code.",
        "Provide a valid Python main function and a correct __name__ guard. Code only.",
        "Correct a broken Python program entry point so the file runs directly.",
    ):
        yield _code_example(prompt, syntax_fix)

    focused_functions = (
        (
            "Write only Python code defining is_odd(number), returning True only for odd integers.",
            '''
def is_odd(number):
    return number % 2 != 0
''',
        ),
        (
            "Define is_multiple_of_three(number) in Python and output only the function code.",
            '''
def is_multiple_of_three(number):
    return number % 3 == 0
''',
        ),
        (
            "Write only a Python function named fahrenheit_to_celsius that applies the standard formula.",
            '''
def fahrenheit_to_celsius(value):
    return (value - 32) * 5 / 9
''',
        ),
        (
            "Create a Python function kilometers_to_miles(value) using 0.621371. Return code only.",
            '''
def kilometers_to_miles(value):
    return value * 0.621371
''',
        ),
        (
            "Write only Python code for mean_or_zero(values), returning zero for an empty sequence.",
            '''
def mean_or_zero(values):
    if not values:
        return 0
    return sum(values) / len(values)
''',
        ),
        (
            "Define first_or_none(values) in Python. It must return None when the sequence is empty.",
            '''
def first_or_none(values):
    if not values:
        return None
    return values[0]
''',
        ),
    )
    for prompt, code in focused_functions:
        yield _code_example(prompt, code)

    explanations = (
        (
            "Explain briefly what Python list.extend(values) does.",
            "It adds every item from values to the end of the existing list.",
        ),
        (
            "What does Python list.insert(index, value) do?",
            "It adds value at the requested list index and shifts later items to the right.",
        ),
        (
            "Why is a Python with statement useful when working with a file?",
            "It manages the file context and closes the file automatically when execution leaves the block, including when an exception occurs.",
        ),
        (
            "Explain `print(\"Hello\")` briefly in Hebrew.",
            "הפקודה מדפיסה את הטקסט Hello כפלט במסוף.",
        ),
    )
    for prompt, answer in explanations:
        yield InstructionExample(
            user=prompt,
            assistant=answer,
            source="generated_behavior_code",
            quality=100.0,
        )

    for index in range(120):
        amount = 2 + index % 19
        code = f'''\
def multiply_by_{amount}(value):
    """Return value multiplied by {amount}."""
    return value * {amount}
'''
        yield _code_example(
            f"Write a tested-looking Python function named multiply_by_{amount} that multiplies its argument by {amount}. Return code only.",
            code,
        )

    for index in range(80):
        lower = 1 + index % 10
        upper = lower + 10 + index % 20
        code = f'''\
def clamp(value, minimum={lower}, maximum={upper}):
    if minimum > maximum:
        raise ValueError("minimum cannot exceed maximum")
    return max(minimum, min(value, maximum))
'''
        yield _code_example(
            f"Write a Python clamp function with defaults {lower} and {upper}, including invalid-bound validation. Output only code.",
            code,
        )

    for amount in range(1, 121):
        name = f"increase_by_{amount}"
        code = f'''\
def {name}(value):
    return value + {amount}
'''
        yield _code_example(
            f"Write only Python code defining {name}(value), which adds {amount} to value.",
            code,
        )

    for divisor in range(2, 82):
        name = f"is_divisible_by_{divisor}"
        code = f'''\
def {name}(number):
    return number % {divisor} == 0
'''
        yield _code_example(
            f"Define {name}(number) in Python so it returns a Boolean. Output only code.",
            code,
        )

    for minimum in range(1, 101):
        name = f"has_minimum_{minimum}"
        code = f'''\
def {name}(values):
    return len(values) >= {minimum}
'''
        yield _code_example(
            f"Write a Python function {name}(values) that checks whether values contains at least {minimum} items. Code only.",
            code,
        )

    for percent in range(1, 101):
        name = f"percent_{percent}_of"
        code = f'''\
def {name}(value):
    return value * {percent} / 100
'''
        yield _code_example(
            f"Return only Python code for {name}(value), calculating {percent} percent of value.",
            code,
        )

    for threshold in range(1, 81):
        name = f"average_above_{threshold}"
        code = f'''\
def {name}(values):
    selected = [value for value in values if value > {threshold}]
    if not selected:
        return None
    return sum(selected) / len(selected)
'''
        yield _code_example(
            f"Define {name}(values). Average only numbers above {threshold} and return None when none qualify. Output code only.",
            code,
        )
