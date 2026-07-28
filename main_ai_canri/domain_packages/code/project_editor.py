"""Conservative, request-driven transformations for existing Agent projects."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any


class ExistingProjectEditor:
    """Apply known project transformations without discarding unrelated files."""

    @staticmethod
    def _normalize_files(files: Any) -> dict[str, str]:
        if not isinstance(files, dict):
            return {}
        normalized = {}
        for path, content in files.items():
            clean_path = PurePosixPath(str(path).replace("\\", "/")).as_posix()
            if clean_path and isinstance(content, str):
                normalized[clean_path] = content
        return normalized

    @staticmethod
    def _request_evidence(text: str, report: dict[str, Any]) -> str:
        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        requirements = contract.get("requirements", [])
        requirement_text = []
        for item in requirements if isinstance(requirements, list) else []:
            if isinstance(item, dict):
                requirement_text.append(str(item.get("text") or item.get("requirement") or ""))
            else:
                requirement_text.append(str(item))
        details = contract.get("detail_inventory", {})
        details = details if isinstance(details, dict) else {}
        for item in details.get("explicit_details", []):
            if isinstance(item, dict):
                requirement_text.append(str(item.get("text") or ""))
        return " ".join([str(text or ""), *requirement_text]).casefold()

    @staticmethod
    def _continuation_requested(report: dict[str, Any]) -> bool:
        contract = report.get("request_contract", {})
        contract = contract if isinstance(contract, dict) else {}
        continuation = contract.get("continuation", {})
        continuation = continuation if isinstance(continuation, dict) else {}
        return bool(continuation.get("requested"))

    @staticmethod
    def _is_guessing_game(files: dict[str, str], evidence: str) -> bool:
        combined = "\n".join(files.values()).casefold()
        file_names = {PurePosixPath(path).name.casefold() for path in files}
        code_signals = sum(
            signal in combined
            for signal in ("random.randint", "secret", "guess", "too high", "too low")
        )
        request_signal = "guess" in evidence or "number-guessing" in evidence
        return bool(code_signals >= 2 or (request_signal and {"game.py", "main.py"}.issubset(file_names)))

    @staticmethod
    def _requests_graphics(evidence: str) -> bool:
        return any(
            signal in evidence
            for signal in (
                "graphical", "graphics", "gui", "window", "tkinter",
                "not in the terminal", "screen interface",
            )
        )

    @staticmethod
    def _requests_music(evidence: str) -> bool:
        return any(signal in evidence for signal in ("music", "melody", "background sound", "soundtrack"))

    @staticmethod
    def _game_module() -> str:
        return '''"""Core number-guessing game logic, independent from the user interface."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class GuessResult:
    status: str
    message: str
    attempts: int
    finished: bool = False


class GuessingGame:
    def __init__(self, minimum: int = 1, maximum: int = 100) -> None:
        if minimum >= maximum:
            raise ValueError("minimum must be smaller than maximum")
        self.minimum = minimum
        self.maximum = maximum
        self.secret = minimum
        self.attempts = 0
        self.finished = False
        self.reset()

    def reset(self) -> None:
        self.secret = random.randint(self.minimum, self.maximum)
        self.attempts = 0
        self.finished = False

    def submit_guess(self, guess: int) -> GuessResult:
        if self.finished:
            return GuessResult("finished", "Start a new game to keep playing.", self.attempts, True)
        if not self.minimum <= guess <= self.maximum:
            return GuessResult(
                "invalid",
                f"Enter a whole number from {self.minimum} to {self.maximum}.",
                self.attempts,
            )

        self.attempts += 1
        if guess < self.secret:
            return GuessResult("low", "Too low. Try a larger number.", self.attempts)
        if guess > self.secret:
            return GuessResult("high", "Too high. Try a smaller number.", self.attempts)

        self.finished = True
        return GuessResult(
            "correct",
            f"Correct! You found {self.secret} in {self.attempts} attempts.",
            self.attempts,
            True,
        )
'''

    @staticmethod
    def _main_module(with_music: bool) -> str:
        music_imports = '''import threading
import time

try:
    import winsound
except ImportError:
    winsound = None
'''
        music_class = '''

class SoundController:
    MELODY = ((392, 150), (494, 150), (587, 220), (494, 150))

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._music_loop, daemon=True)
        self.thread.start()

    def _music_loop(self) -> None:
        while not self.stop_event.is_set():
            if winsound is None:
                self.stop_event.wait(1.4)
                continue
            for frequency, duration in self.MELODY:
                if self.stop_event.is_set():
                    return
                winsound.Beep(frequency, duration)
                time.sleep(0.04)
            self.stop_event.wait(1.2)

    def effect(self, success: bool) -> None:
        if winsound is None:
            self.root.bell()
            return
        alias = winsound.MB_ICONASTERISK if success else winsound.MB_ICONEXCLAMATION
        winsound.MessageBeep(alias)

    def stop(self) -> None:
        self.stop_event.set()
'''
        sound_init = "        self.sound = SoundController(root)\n        self.sound.start()\n" if with_music else ""
        sound_result = "        self.sound.effect(result.finished)\n" if with_music else ""
        sound_close = "        self.sound.stop()\n" if with_music else ""
        imports = "import tkinter as tk\nfrom tkinter import ttk\n"
        if with_music:
            imports += music_imports
        return f'''"""Graphical entry point for the number-guessing game."""

from __future__ import annotations

{imports}
from game import GuessingGame
{music_class if with_music else ""}

class GuessingGameWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.game = GuessingGame()
{sound_init}        self.root.title("Number Quest")
        self.root.geometry("560x390")
        self.root.minsize(500, 350)
        self.root.configure(bg="#101820")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("Game.TFrame", background="#101820")
        style.configure("Title.TLabel", background="#101820", foreground="#f2aa4c", font=("Segoe UI", 24, "bold"))
        style.configure("Body.TLabel", background="#101820", foreground="#f7f7f7", font=("Segoe UI", 12))
        style.configure("Game.TButton", font=("Segoe UI", 11, "bold"), padding=9)

        frame = ttk.Frame(root, padding=28, style="Game.TFrame")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="NUMBER QUEST", style="Title.TLabel").pack(pady=(8, 12))
        ttk.Label(frame, text="Find the hidden number from 1 to 100", style="Body.TLabel").pack()

        self.guess_var = tk.StringVar()
        self.entry = ttk.Entry(frame, textvariable=self.guess_var, justify="center", font=("Segoe UI", 18), width=12)
        self.entry.pack(pady=24)
        self.entry.bind("<Return>", self.check_guess)

        controls = ttk.Frame(frame, style="Game.TFrame")
        controls.pack()
        ttk.Button(controls, text="Guess", command=self.check_guess, style="Game.TButton").grid(row=0, column=0, padx=6)
        ttk.Button(controls, text="New Game", command=self.new_game, style="Game.TButton").grid(row=0, column=1, padx=6)

        self.status_var = tk.StringVar(value="Enter your first guess.")
        ttk.Label(frame, textvariable=self.status_var, style="Body.TLabel", wraplength=460, justify="center").pack(pady=(24, 8))
        self.attempts_var = tk.StringVar(value="Attempts: 0")
        ttk.Label(frame, textvariable=self.attempts_var, style="Body.TLabel").pack()
        self.entry.focus_set()

    def check_guess(self, _event: object | None = None) -> None:
        raw = self.guess_var.get().strip()
        try:
            guess = int(raw)
        except ValueError:
            self.status_var.set("Please enter a whole number.")
            self.entry.selection_range(0, tk.END)
            return

        result = self.game.submit_guess(guess)
        self.status_var.set(result.message)
        self.attempts_var.set(f"Attempts: {{result.attempts}}")
        self.guess_var.set("")
{sound_result}        if result.finished:
            self.entry.configure(state="disabled")
        else:
            self.entry.focus_set()

    def new_game(self) -> None:
        self.game.reset()
        self.entry.configure(state="normal")
        self.guess_var.set("")
        self.status_var.set("A new number is ready.")
        self.attempts_var.set("Attempts: 0")
        self.entry.focus_set()

    def close(self) -> None:
{sound_close}        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    GuessingGameWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
'''

    def build(
        self,
        text: str,
        report: dict[str, Any] | None,
        existing_files: Any,
        creative_guidance: dict[str, Any] | None = None,
        continuation_context: bool = False,
    ) -> dict[str, Any]:
        report = report if isinstance(report, dict) else {}
        files = self._normalize_files(existing_files)
        if not files or not (self._continuation_requested(report) or continuation_context):
            return {}

        evidence = self._request_evidence(text, report)
        if not self._is_guessing_game(files, evidence) or not self._requests_graphics(evidence):
            return {}

        with_music = self._requests_music(evidence)
        updated = dict(files)
        updated["game.py"] = self._game_module()
        updated["main.py"] = self._main_module(with_music)
        changed = [path for path, content in updated.items() if files.get(path) != content]
        requirements = [
            "preserve the existing project",
            "replace terminal interaction with a Tkinter window",
            "keep game logic separate from the graphical entry point",
            "handle invalid guesses without closing the application",
        ]
        if with_music:
            requirements.append("play background music and answer feedback sounds")
        return {
            "handler": "graphical_number_guessing_game",
            "project_files": updated,
            "changed_paths": changed,
            "preserved_paths": sorted(path for path in files if path not in changed),
            "entrypoint": "main.py",
            "with_music": with_music,
            "creative_guidance_used": bool(creative_guidance),
            "requirements_implemented": requirements,
        }


project_editor = ExistingProjectEditor()
