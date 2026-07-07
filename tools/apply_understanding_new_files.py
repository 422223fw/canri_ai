from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "main_ai_canri" / "UnderstandingDk" / "data"
FILES = [
    "main_dictionary.json",
    "Connections_Dictionary.json",
    "Grammar_dictionary.json",
]


def main():
    for name in FILES:
        source = DATA_DIR / f"{name}.new"
        target = DATA_DIR / name

        if not source.exists():
            print(name, "missing .new file")
            continue

        try:
            source.replace(target)
            print(name, "updated")
        except PermissionError:
            print(name, "blocked - close it in VS Code and run again")


if __name__ == "__main__":
    main()
