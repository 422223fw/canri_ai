import queue
import shutil
import threading
import wave
import json
import os
import time
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from tkinter import simpledialog
from tkinter.scrolledtext import ScrolledText

import tkinter as tk

from Agent_settings import load_agent_settings, save_agent_settings
from Canri_identity import release_version
from Movie_settings import load_movie_settings, save_movie_settings


DATA_DIR = Path(__file__).parent / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
RECORDING_DIR = UPLOAD_DIR / "recordings"
CHAT_FILE = DATA_DIR / "Canri_chats.json"
CHAT_BACKUP_FILE = DATA_DIR / "Canri_chats.backup.json"
CHAT_TEMP_FILE = DATA_DIR / "Canri_chats.tmp.json"
MEMORY_STATS_FILE = DATA_DIR / "Cognitive_memory_statistics.json"


class CanriGraphics:

    def __init__(self, message_handler=None, memory_handler=None):

        self.root = tk.Tk()
        self.root.title("Canri AI")
        self.root.geometry("1240x780")
        self.root.minsize(980, 620)

        self.colors = {
            "app": "#0f1115",
            "sidebar": "#151922",
            "sidebar_border": "#252b36",
            "panel": "#171b23",
            "panel_2": "#1d2330",
            "input": "#10141c",
            "input_border": "#303846",
            "text": "#eef2f7",
            "muted": "#9aa4b2",
            "accent": "#2f81f7",
            "accent_hover": "#1f6feb",
            "danger": "#e5534b",
            "success": "#33b074"
        }

        self.attached_files = []
        self.message_handler = message_handler
        self.memory_handler = memory_handler
        self.is_recording = False
        self.recording_thread = None
        self.recording_frames = []
        self.recording_queue = queue.Queue()
        self.sample_rate = 44100
        self.thinking_traces = {}
        self.thinking_windows = {}
        self.movie_settings = load_movie_settings()
        self.agent_settings = load_agent_settings()
        self.trace_counter = 0
        self.latest_trace_id = None
        self.thinking_started_at = None
        self.thinking_timer_job = None
        self.chats = {
            "chats": []
        }
        self.current_chat_id = None

        self.setup_root()
        self.build_sidebar()
        self.build_main()
        self.load_chats()

    # ---------- base UI ----------

    def setup_root(self):

        self.root.configure(
            bg=self.colors["app"]
        )

        self.root.grid_columnconfigure(
            1,
            weight=1
        )

        self.root.grid_rowconfigure(
            0,
            weight=1
        )

    def build_sidebar(self):

        self.sidebar = tk.Frame(
            self.root,
            bg=self.colors["sidebar"],
            width=280,
            highlightthickness=1,
            highlightbackground=self.colors["sidebar_border"]
        )
        self.sidebar.grid(
            row=0,
            column=0,
            sticky="ns"
        )
        self.sidebar.grid_propagate(False)

        brand = tk.Label(
            self.sidebar,
            text="CANRI AI",
            bg=self.colors["sidebar"],
            fg=self.colors["text"],
            font=("Segoe UI", 19, "bold"),
            anchor="w"
        )
        brand.pack(
            fill="x",
            padx=18,
            pady=(22, 4)
        )

        subtitle = tk.Label(
            self.sidebar,
            text="Workspace",
            bg=self.colors["sidebar"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            anchor="w"
        )
        subtitle.pack(
            fill="x",
            padx=18,
            pady=(0, 18)
        )

        self.new_chat_button = self.create_button(
            self.sidebar,
            text="New chat",
            command=self.new_chat,
            bg=self.colors["panel_2"]
        )
        self.new_chat_button.pack(
            fill="x",
            padx=14,
            pady=(0, 10),
            ipady=8
        )

        chat_actions = tk.Frame(
            self.sidebar,
            bg=self.colors["sidebar"]
        )
        chat_actions.pack(
            fill="x",
            padx=14,
            pady=(0, 8)
        )

        self.rename_chat_button = self.create_button(
            chat_actions,
            text="Rename",
            command=self.rename_current_chat,
            bg=self.colors["panel_2"]
        )
        self.rename_chat_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 4)
        )

        self.delete_chat_button = self.create_button(
            chat_actions,
            text="Delete",
            command=self.delete_current_chat,
            bg=self.colors["danger"]
        )
        self.delete_chat_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(4, 0)
        )

        self.clear_chats_button = self.create_button(
            self.sidebar,
            text="Clear all chats",
            command=self.clear_all_chats,
            bg=self.colors["panel_2"]
        )
        self.clear_chats_button.pack(
            fill="x",
            padx=14,
            pady=(0, 4)
        )

        history_label = tk.Label(
            self.sidebar,
            text="Chats",
            bg=self.colors["sidebar"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10, "bold"),
            anchor="w"
        )
        history_label.pack(
            fill="x",
            padx=18,
            pady=(12, 8)
        )

        self.chat_list = tk.Listbox(
            self.sidebar,
            bg=self.colors["sidebar"],
            fg=self.colors["text"],
            selectbackground=self.colors["panel_2"],
            selectforeground=self.colors["text"],
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            font=("Segoe UI", 10)
        )
        self.chat_list.pack(
            fill="both",
            expand=True,
            padx=14,
            pady=(0, 12)
        )
        self.chat_list.bind(
            "<<ListboxSelect>>",
            self.on_chat_selected
        )
        self.chat_list.bind("<Double-Button-1>", self.rename_current_chat)
        self.chat_list.bind("<Delete>", self.delete_current_chat)

        self.empty_history = tk.Label(
            self.sidebar,
            text="No chats yet",
            bg=self.colors["sidebar"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            anchor="w"
        )
        self.empty_history.place(
            x=20,
            y=250
        )

        status_frame = tk.Frame(
            self.sidebar,
            bg=self.colors["sidebar"]
        )
        status_frame.pack(
            fill="x",
            padx=14,
            pady=(0, 14)
        )

        self.status_dot = tk.Label(
            status_frame,
            text="ONLINE",
            bg=self.colors["sidebar"],
            fg=self.colors["success"],
            font=("Segoe UI", 9, "bold")
        )
        self.status_dot.pack(
            side="left"
        )

        status = tk.Label(
            status_frame,
            text="Local session",
            bg=self.colors["sidebar"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10)
        )
        status.pack(
            side="left",
            padx=(6, 0)
        )

    def build_main(self):

        self.main = tk.Frame(
            self.root,
            bg=self.colors["app"]
        )
        self.main.grid(
            row=0,
            column=1,
            sticky="nsew"
        )
        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        self.build_header()
        self.build_chat_area()
        self.build_attachment_bar()
        self.build_composer()

    def build_header(self):

        header = tk.Frame(
            self.main,
            bg=self.colors["app"],
            height=76
        )
        header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=24,
            pady=(18, 6)
        )
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        title = tk.Label(
            header,
            text="Canri AI",
            bg=self.colors["app"],
            fg=self.colors["text"],
            font=("Segoe UI", 21, "bold"),
            anchor="w"
        )
        title.grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.header_status = tk.Label(
            header,
            text="Ready",
            bg=self.colors["app"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            anchor="w"
        )
        self.header_status.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(4, 0)
        )

        self.thinking_button = self.create_button(
            header,
            text="Thinking details",
            command=self.show_latest_thinking_trace,
            bg=self.colors["panel_2"]
        )
        self.thinking_button.grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="e",
            padx=(12, 0)
        )
        self.thinking_button.configure(
            state="disabled",
            fg=self.colors["muted"]
        )

        self.memory_stats_button = self.create_button(
            header,
            text="Memory statistics",
            command=self.show_memory_statistics,
            bg=self.colors["panel_2"]
        )
        self.memory_stats_button.grid(
            row=0,
            column=2,
            rowspan=2,
            sticky="e",
            padx=(8, 0)
        )

        self.knowledge_stats_button = self.create_button(
            header,
            text="Knowledge statistics",
            command=self.show_knowledge_statistics,
            bg=self.colors["panel_2"]
        )
        self.knowledge_stats_button.grid(
            row=0,
            column=3,
            rowspan=2,
            sticky="e",
            padx=(8, 0)
        )

        self.settings_button = self.create_button(
            header,
            text="Settings",
            command=self.show_settings,
            bg=self.colors["panel_2"]
        )
        self.settings_button.grid(
            row=0,
            column=4,
            rowspan=2,
            sticky="e",
            padx=(8, 0)
        )

    def show_settings(self):
        window = tk.Toplevel(self.root)
        window.title(f"Canri settings - v{release_version()}")
        window.geometry("680x720")
        window.resizable(False, False)
        window.configure(bg=self.colors["app"])

        body = tk.Frame(window, bg=self.colors["app"])
        body.pack(fill="both", expand=True, padx=24, pady=22)
        body.grid_columnconfigure(1, weight=1)

        tk.Label(
            body,
            text=f"Canri AI v{release_version()} - Movie video provider",
            bg=self.colors["app"],
            fg=self.colors["text"],
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        tk.Label(body, text="Provider", bg=self.colors["app"], fg=self.colors["muted"]).grid(
            row=1, column=0, sticky="w", pady=7
        )
        provider = tk.StringVar(value=str(self.movie_settings.get("provider", "runway")))
        tk.Entry(body, textvariable=provider, bg=self.colors["input"], fg=self.colors["text"], insertbackground=self.colors["text"]).grid(
            row=1, column=1, sticky="ew", pady=7
        )

        tk.Label(body, text="Model", bg=self.colors["app"], fg=self.colors["muted"]).grid(
            row=2, column=0, sticky="w", pady=7
        )
        model = tk.StringVar(value=str(self.movie_settings.get("model", "gen4.5")))
        tk.Entry(body, textvariable=model, bg=self.colors["input"], fg=self.colors["text"], insertbackground=self.colors["text"]).grid(
            row=2, column=1, sticky="ew", pady=7
        )

        tk.Label(body, text="API key", bg=self.colors["app"], fg=self.colors["muted"]).grid(
            row=3, column=0, sticky="w", pady=7
        )
        api_key = tk.StringVar(value=os.getenv("RUNWAYML_API_SECRET", ""))
        tk.Entry(body, textvariable=api_key, show="*", bg=self.colors["input"], fg=self.colors["text"], insertbackground=self.colors["text"]).grid(
            row=3, column=1, sticky="ew", pady=7
        )

        tk.Label(body, text="Budget (USD)", bg=self.colors["app"], fg=self.colors["muted"]).grid(
            row=4, column=0, sticky="w", pady=7
        )
        budget = tk.StringVar(value=str(self.movie_settings.get("budget_usd", 25.0)))
        tk.Entry(body, textvariable=budget, bg=self.colors["input"], fg=self.colors["text"], insertbackground=self.colors["text"]).grid(
            row=4, column=1, sticky="ew", pady=7
        )

        paid = tk.BooleanVar(value=bool(self.movie_settings.get("allow_paid_render", False)))
        tk.Checkbutton(
            body,
            text="Allow paid movie rendering",
            variable=paid,
            bg=self.colors["app"],
            fg=self.colors["text"],
            activebackground=self.colors["app"],
            activeforeground=self.colors["text"],
            selectcolor=self.colors["panel_2"]
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(14, 4))

        tk.Label(
            body,
            text="The API key is used for this running session only. For persistence, set RUNWAYML_API_SECRET in PowerShell.\nCanri will show a cost estimate and will not render while paid rendering is disabled.",
            bg=self.colors["app"],
            fg=self.colors["muted"],
            justify="left",
            anchor="w",
            wraplength=500
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(14, 18))

        tk.Frame(body, bg=self.colors["input_border"], height=1).grid(
            row=7, column=0, columnspan=2, sticky="ew", pady=(2, 16)
        )
        tk.Label(
            body,
            text="Project Agent",
            bg=self.colors["app"],
            fg=self.colors["text"],
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(0, 10))

        mode_labels = {
            "No Agent": "off",
            "Agent - Autonomous": "autonomous",
            "Agent - Restricted": "restricted",
            "Agent - Ask Before Changes": "approval",
        }
        current_mode = str(self.agent_settings.get("mode", "off"))
        current_label = next(
            (label for label, value in mode_labels.items() if value == current_mode),
            "No Agent"
        )
        agent_mode = tk.StringVar(value=current_label)
        tk.Label(body, text="Mode", bg=self.colors["app"], fg=self.colors["muted"]).grid(
            row=9, column=0, sticky="w", pady=7
        )
        mode_menu = tk.OptionMenu(body, agent_mode, *mode_labels.keys())
        mode_menu.configure(
            bg=self.colors["input"],
            fg=self.colors["text"],
            activebackground=self.colors["panel_2"],
            activeforeground=self.colors["text"],
            highlightthickness=1,
            highlightbackground=self.colors["input_border"],
            relief="flat"
        )
        mode_menu["menu"].configure(bg=self.colors["panel_2"], fg=self.colors["text"])
        mode_menu.grid(row=9, column=1, sticky="ew", pady=7)

        tk.Label(body, text="Project path", bg=self.colors["app"], fg=self.colors["muted"]).grid(
            row=10, column=0, sticky="w", pady=7
        )
        agent_path = tk.StringVar(value=str(self.agent_settings.get("workspace_path", "")))
        path_row = tk.Frame(body, bg=self.colors["app"])
        path_row.grid(row=10, column=1, sticky="ew", pady=7)
        path_row.grid_columnconfigure(0, weight=1)
        tk.Entry(
            path_row,
            textvariable=agent_path,
            bg=self.colors["input"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"]
        ).grid(row=0, column=0, sticky="ew")

        def choose_agent_path():
            selected = filedialog.askdirectory(
                parent=window,
                title="Select the project Agent may work on",
                initialdir=agent_path.get().strip() or str(Path.cwd())
            )
            if selected:
                agent_path.set(selected)

        self.create_button(
            path_row,
            text="Browse",
            command=choose_agent_path,
            bg=self.colors["panel_2"]
        ).grid(row=0, column=1, padx=(8, 0))

        agent_writes = tk.BooleanVar(value=bool(self.agent_settings.get("allow_file_writes", True)))
        agent_terminal = tk.BooleanVar(value=bool(self.agent_settings.get("allow_terminal", True)))
        tk.Checkbutton(
            body,
            text="Allow file writes inside the selected project",
            variable=agent_writes,
            bg=self.colors["app"],
            fg=self.colors["text"],
            activebackground=self.colors["app"],
            activeforeground=self.colors["text"],
            selectcolor=self.colors["panel_2"]
        ).grid(row=11, column=0, columnspan=2, sticky="w", pady=(10, 2))
        tk.Checkbutton(
            body,
            text="Allow approved terminal tools inside the selected project",
            variable=agent_terminal,
            bg=self.colors["app"],
            fg=self.colors["text"],
            activebackground=self.colors["app"],
            activeforeground=self.colors["text"],
            selectcolor=self.colors["panel_2"]
        ).grid(row=12, column=0, columnspan=2, sticky="w", pady=2)

        tk.Label(
            body,
            text=(
                "Autonomous works without asking; Restricted uses a smaller tool set; "
                "Ask Before Changes reads context but requests approval before writes or commands. "
                "Canri's own file actions stay inside this path. Programs launched by the Agent still "
                "run with the current Windows account's permissions, so use Autonomous only on trusted projects."
            ),
            bg=self.colors["app"],
            fg=self.colors["muted"],
            justify="left",
            anchor="w",
            wraplength=610
        ).grid(row=13, column=0, columnspan=2, sticky="w", pady=(10, 14))

        status = tk.Label(body, text="", bg=self.colors["app"], fg=self.colors["muted"], anchor="w")
        status.grid(row=14, column=0, columnspan=2, sticky="w", pady=(0, 10))

        def save():
            try:
                budget_value = max(0.0, float(budget.get().strip()))
            except ValueError:
                status.configure(text="Budget must be a number.", fg=self.colors["danger"])
                return
            selected_mode = mode_labels.get(agent_mode.get(), "off")
            selected_path = agent_path.get().strip()
            if selected_mode != "off":
                candidate = Path(selected_path).expanduser()
                if not selected_path or not candidate.exists() or not candidate.is_dir():
                    status.configure(text="Select an existing project directory for Agent mode.", fg=self.colors["danger"])
                    return
            if api_key.get().strip():
                os.environ["RUNWAYML_API_SECRET"] = api_key.get().strip()
            else:
                os.environ.pop("RUNWAYML_API_SECRET", None)
            self.movie_settings = save_movie_settings({
                "provider": provider.get().strip() or "runway",
                "model": model.get().strip() or "gen4.5",
                "budget_usd": budget_value,
                "allow_paid_render": paid.get(),
            })
            self.agent_settings = save_agent_settings({
                **self.agent_settings,
                "mode": selected_mode,
                "workspace_path": selected_path,
                "allow_file_writes": agent_writes.get(),
                "allow_terminal": agent_terminal.get(),
            })
            status.configure(text="Movie and Agent settings saved.", fg=self.colors["success"])
            self.header_status.configure(text=f"Settings updated - Agent: {selected_mode}")

        actions = tk.Frame(body, bg=self.colors["app"])
        actions.grid(row=15, column=0, columnspan=2, sticky="e")
        self.create_button(actions, text="Save", command=save, bg=self.colors["accent"]).pack(side="left", padx=5)
        self.create_button(actions, text="Close", command=window.destroy, bg=self.colors["panel_2"]).pack(side="left", padx=5)

    def build_chat_area(self):

        chat_frame = tk.Frame(
            self.main,
            bg=self.colors["panel"],
            highlightthickness=1,
            highlightbackground=self.colors["input_border"]
        )
        chat_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=24,
            pady=8
        )
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)

        self.chat_area = ScrolledText(
            chat_frame,
            bg=self.colors["panel"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            borderwidth=0,
            wrap="word",
            font=("Segoe UI", 11),
            padx=18,
            pady=16
        )
        self.chat_area.grid(
            row=0,
            column=0,
            sticky="nsew"
        )
        self.chat_area.configure(
            state="disabled"
        )
        self.bind_chat_shortcuts()

        self.empty_state = tk.Label(
            chat_frame,
            text="Start a conversation or attach a file.",
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=("Segoe UI", 13)
        )
        self.empty_state.place(
            relx=0.5,
            rely=0.48,
            anchor="center"
        )

    def build_attachment_bar(self):

        self.attachment_frame = tk.Frame(
            self.main,
            bg=self.colors["app"]
        )
        self.attachment_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 6)
        )
        self.attachment_frame.grid_columnconfigure(0, weight=1)

        self.attachment_label = tk.Label(
            self.attachment_frame,
            text="No files attached",
            bg=self.colors["app"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            anchor="w"
        )
        self.attachment_label.grid(
            row=0,
            column=0,
            sticky="ew"
        )

        self.clear_files_button = self.create_button(
            self.attachment_frame,
            text="Clear",
            command=self.clear_attachments,
            bg=self.colors["panel_2"]
        )
        self.clear_files_button.grid(
            row=0,
            column=1,
            padx=(10, 0)
        )

    def build_composer(self):

        composer = tk.Frame(
            self.main,
            bg=self.colors["app"]
        )
        composer.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 22)
        )
        composer.grid_columnconfigure(1, weight=1)

        attach_button = self.create_button(
            composer,
            text="Attach",
            command=self.attach_files,
            bg=self.colors["panel_2"]
        )
        attach_button.grid(
            row=0,
            column=0,
            sticky="ns",
            padx=(0, 8),
            ipady=8
        )

        self.message_entry = tk.Text(
            composer,
            bg=self.colors["input"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            borderwidth=0,
            height=3,
            wrap="word",
            font=("Segoe UI", 11),
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground=self.colors["input_border"],
            highlightcolor=self.colors["accent"]
        )
        self.message_entry.grid(
            row=0,
            column=1,
            sticky="ew"
        )
        self.message_entry.bind(
            "<Control-Return>",
            lambda event: self.send_message()
        )
        self.bind_text_shortcuts()

        self.record_button = self.create_button(
            composer,
            text="Record",
            command=self.toggle_recording,
            bg=self.colors["panel_2"]
        )
        self.record_button.grid(
            row=0,
            column=2,
            sticky="ns",
            padx=8,
            ipady=8
        )

        send_button = self.create_button(
            composer,
            text="Send",
            command=self.send_message,
            bg=self.colors["accent"]
        )
        send_button.grid(
            row=0,
            column=3,
            sticky="ns",
            ipady=8
        )

    def bind_text_shortcuts(self):

        self.message_menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=self.colors["panel_2"],
            fg=self.colors["text"],
            activebackground=self.colors["accent"],
            activeforeground=self.colors["text"]
        )
        self.message_menu.add_command(
            label="Cut",
            command=self.cut_message_text
        )
        self.message_menu.add_command(
            label="Copy",
            command=self.copy_message_text
        )
        self.message_menu.add_command(
            label="Paste",
            command=self.paste_message_text
        )
        self.message_menu.add_separator()
        self.message_menu.add_command(
            label="Select all",
            command=self.select_all_message_text
        )

        shortcuts = {
            "<Control-v>": self.paste_message_text,
            "<Control-V>": self.paste_message_text,
            "<Shift-Insert>": self.paste_message_text,
            "<Control-c>": self.copy_message_text,
            "<Control-C>": self.copy_message_text,
            "<Control-x>": self.cut_message_text,
            "<Control-X>": self.cut_message_text,
            "<Control-a>": self.select_all_message_text,
            "<Control-A>": self.select_all_message_text
        }

        for shortcut, command in shortcuts.items():
            self.message_entry.bind(
                shortcut,
                lambda event, handler=command: self.run_text_shortcut(handler)
            )

        self.message_entry.bind(
            "<Button-3>",
            self.show_message_menu
        )

    def bind_chat_shortcuts(self):

        self.chat_menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=self.colors["panel_2"],
            fg=self.colors["text"],
            activebackground=self.colors["accent"],
            activeforeground=self.colors["text"]
        )
        self.chat_menu.add_command(
            label="Copy",
            command=self.copy_chat_text
        )
        self.chat_menu.add_command(
            label="Copy all",
            command=self.copy_all_chat_text
        )
        self.chat_menu.add_separator()
        self.chat_menu.add_command(
            label="Select all",
            command=self.select_all_chat_text
        )

        self.chat_area.bind(
            "<Control-c>",
            lambda event: self.run_text_shortcut(self.copy_chat_text)
        )
        self.chat_area.bind(
            "<Control-C>",
            lambda event: self.run_text_shortcut(self.copy_chat_text)
        )
        self.chat_area.bind(
            "<Control-a>",
            lambda event: self.run_text_shortcut(self.select_all_chat_text)
        )
        self.chat_area.bind(
            "<Control-A>",
            lambda event: self.run_text_shortcut(self.select_all_chat_text)
        )
        self.chat_area.bind(
            "<Button-3>",
            self.show_chat_menu
        )

    def run_text_shortcut(self, handler):

        handler()
        return "break"

    def paste_message_text(self):

        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return

        try:
            self.message_entry.delete("sel.first", "sel.last")
        except tk.TclError:
            pass

        self.message_entry.insert("insert", text)
        self.message_entry.focus_set()

    def copy_message_text(self):

        try:
            text = self.message_entry.get("sel.first", "sel.last")
        except tk.TclError:
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.message_entry.focus_set()

    def cut_message_text(self):

        try:
            text = self.message_entry.get("sel.first", "sel.last")
        except tk.TclError:
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.message_entry.delete("sel.first", "sel.last")
        self.message_entry.focus_set()

    def select_all_message_text(self):

        self.message_entry.tag_add("sel", "1.0", "end-1c")
        self.message_entry.mark_set("insert", "end-1c")
        self.message_entry.see("insert")
        self.message_entry.focus_set()

    def show_message_menu(self, event):

        self.message_entry.focus_set()
        self.message_menu.tk_popup(
            event.x_root,
            event.y_root
        )

    def copy_chat_text(self):

        try:
            text = self.chat_area.get("sel.first", "sel.last")
        except tk.TclError:
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.chat_area.focus_set()

    def copy_all_chat_text(self):

        text = self.chat_area.get("1.0", "end-1c")

        if not text:
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.chat_area.focus_set()

    def select_all_chat_text(self):

        self.chat_area.configure(state="normal")
        self.chat_area.tag_add("sel", "1.0", "end-1c")
        self.chat_area.mark_set("insert", "end-1c")
        self.chat_area.see("insert")
        self.chat_area.configure(state="disabled")
        self.chat_area.focus_set()

    def show_chat_menu(self, event):

        self.chat_area.focus_set()
        self.chat_menu.tk_popup(
            event.x_root,
            event.y_root
        )

    def create_button(self, parent, text, command, bg):

        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=self.colors["text"],
            activebackground=self.colors["accent_hover"],
            activeforeground=self.colors["text"],
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            padx=14,
            pady=6
        )

        return button

    # ---------- actions ----------

    def load_chats(self):

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        for candidate in [CHAT_FILE, CHAT_BACKUP_FILE]:
            if not candidate.exists():
                continue
            try:
                with candidate.open("r", encoding="utf-8") as file:
                    loaded = json.load(file)
                if isinstance(loaded, dict) and isinstance(loaded.get("chats"), list):
                    self.chats = loaded
                    break
            except (OSError, json.JSONDecodeError):
                continue

        valid_chats = []
        seen_ids = set()
        for chat in self.chats.get("chats", []):
            if not isinstance(chat, dict):
                continue
            chat_id = str(chat.get("id") or self.make_chat_id())
            if chat_id in seen_ids:
                continue
            seen_ids.add(chat_id)
            chat["id"] = chat_id
            chat["title"] = str(chat.get("title") or "Untitled chat")[:80]
            chat["messages"] = [item for item in chat.get("messages", []) if isinstance(item, dict)]
            valid_chats.append(chat)
        self.chats["chats"] = valid_chats[-2000:]

        self.chat_list.delete(0, "end")

        for chat in self.chats.get("chats", []):
            self.chat_list.insert(
                "end",
                chat.get("title", "Untitled chat")
            )

        if self.chats.get("chats"):
            self.empty_history.place_forget()
            self.current_chat_id = self.chats["chats"][-1].get("id")
            self.chat_list.selection_clear(0, "end")
            self.chat_list.selection_set(len(self.chats["chats"]) - 1)
            self.render_current_chat()
        else:
            self.current_chat_id = None

    def save_chats(self):

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        self.chats["updated_utc"] = datetime.now().isoformat()

        with CHAT_TEMP_FILE.open("w", encoding="utf-8") as file:
            json.dump(
                self.chats,
                file,
                ensure_ascii=False,
                indent=2
            )
            file.write("\n")
            file.flush()

        if CHAT_FILE.exists():
            try:
                shutil.copy2(CHAT_FILE, CHAT_BACKUP_FILE)
            except OSError:
                pass
        CHAT_TEMP_FILE.replace(CHAT_FILE)

    def make_chat_id(self):

        return "chat_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    def current_chat(self):

        for chat in self.chats.get("chats", []):
            if chat.get("id") == self.current_chat_id:
                return chat

        return None

    def chat_by_id(self, chat_id):

        for chat in self.chats.get("chats", []):
            if chat.get("id") == chat_id:
                return chat
        return None

    def ensure_current_chat(self, first_message=None):

        chat = self.current_chat()

        if chat:
            return chat

        title = "New chat"
        if first_message:
            title = self.make_chat_title(first_message)

        chat = {
            "id": self.make_chat_id(),
            "title": title,
            "created_utc": datetime.now().isoformat(),
            "updated_utc": datetime.now().isoformat(),
            "messages": []
        }

        self.chats.setdefault("chats", []).append(chat)
        self.current_chat_id = chat["id"]
        self.chat_list.insert("end", title)
        self.chat_list.selection_clear(0, "end")
        self.chat_list.selection_set(self.chat_list.size() - 1)
        self.empty_history.place_forget()
        self.notify_memory_handler("create", chat.get("id"), title)
        self.save_chats()

        return chat

    def make_chat_title(self, message):

        words = str(message).strip().split()
        if not words:
            return datetime.now().strftime("Chat %H:%M")

        return " ".join(words[:6])[:48]

    def append_chat_record(
        self,
        role,
        text,
        trace_id=None,
        chat_id=None,
        attachments=None,
        agent_changes=None,
        memory_usage=None,
    ):

        chat = self.chat_by_id(chat_id) if chat_id else None
        if chat_id and chat is None:
            return None
        if chat is None:
            chat = self.ensure_current_chat(text if role == "USER" else None)

        if role == "USER" and chat.get("title") in ["New chat", "Untitled chat"]:
            chat["title"] = self.make_chat_title(text)
            self.refresh_chat_list_titles()

        record = {
            role: text,
            "created_utc": datetime.now().isoformat(),
            "trace_id": trace_id
        }
        if attachments:
            record["attachments"] = [
                {
                    "path": str(path),
                    "name": Path(path).name,
                    "exists": Path(path).exists()
                }
                for path in attachments[:20]
            ]
        if isinstance(agent_changes, dict):
            record["agent_changes"] = agent_changes
        if isinstance(memory_usage, dict):
            record["memory_usage"] = memory_usage
        chat.setdefault("messages", []).append(record)
        chat["updated_utc"] = datetime.now().isoformat()
        self.save_chats()

        return record

    def refresh_chat_list_titles(self):

        self.chat_list.delete(0, "end")

        selected_index = 0
        for index, chat in enumerate(self.chats.get("chats", [])):
            if chat.get("id") == self.current_chat_id:
                selected_index = index
            self.chat_list.insert(
                "end",
                chat.get("title", "Untitled chat")
            )

        if self.chat_list.size():
            self.chat_list.selection_set(selected_index)

    def render_current_chat(self):

        chat = self.current_chat()

        self.chat_area.configure(state="normal")
        self.chat_area.delete("1.0", "end")

        if not chat or not chat.get("messages"):
            self.chat_area.configure(state="disabled")
            self.empty_state.place(relx=0.5, rely=0.48, anchor="center")
            return

        self.empty_state.place_forget()

        for message in chat.get("messages", []):
            if "USER" in message:
                self.insert_chat_message("You", message.get("USER", ""))
                attachments = message.get("attachments", [])
                if attachments:
                    self.insert_chat_message(
                        "Files",
                        "\n".join(f"- {item.get('name', 'file')}" for item in attachments)
                    )
            if "CANRI" in message:
                self.insert_chat_message("Canri", message.get("CANRI", ""))
                memory_usage = message.get("memory_usage")
                if isinstance(memory_usage, dict):
                    self.insert_memory_button(memory_usage, message.get("trace_id"))
                agent_changes = message.get("agent_changes")
                if isinstance(agent_changes, dict):
                    self.insert_agent_change_card(agent_changes)

        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def on_chat_selected(self, event=None):

        selection = self.chat_list.curselection()
        if not selection:
            return

        index = selection[0]
        chats = self.chats.get("chats", [])
        if index >= len(chats):
            return

        self.current_chat_id = chats[index].get("id")
        self.render_current_chat()

    def new_chat(self):

        self.chat_area.configure(state="normal")
        self.chat_area.delete("1.0", "end")
        self.chat_area.configure(state="disabled")

        self.attached_files = []
        self.update_attachment_label()
        self.empty_state.place(relx=0.5, rely=0.48, anchor="center")
        self.header_status.configure(text="New chat ready")

        chat = {
            "id": self.make_chat_id(),
            "title": datetime.now().strftime("Chat %H:%M"),
            "created_utc": datetime.now().isoformat(),
            "updated_utc": datetime.now().isoformat(),
            "messages": []
        }
        self.chats.setdefault("chats", []).append(chat)
        self.current_chat_id = chat["id"]
        self.refresh_chat_list_titles()
        self.empty_history.place_forget()
        self.notify_memory_handler("create", chat.get("id"), chat.get("title"))
        self.save_chats()

    def notify_memory_handler(self, action, chat_id=None, title=None):

        if not self.memory_handler:
            return None

        try:
            return self.memory_handler(
                action=action,
                chat_id=chat_id,
                title=title
            )
        except TypeError:
            return self.memory_handler(action, chat_id, title)
        except Exception as error:
            messagebox.showwarning(
                "Canri memory",
                f"The chat list was updated, but memory synchronization failed: {error}",
                parent=self.root
            )
            return None

    def rename_current_chat(self, event=None):

        chat = self.current_chat()
        if not chat:
            return

        title = simpledialog.askstring(
            "Rename chat",
            "Chat name:",
            initialvalue=chat.get("title", "Untitled chat"),
            parent=self.root
        )
        if title is None:
            return

        title = title.strip()[:80]
        if not title:
            messagebox.showinfo(
                "Rename chat",
                "The chat name cannot be empty.",
                parent=self.root
            )
            return

        chat["title"] = title
        chat["updated_utc"] = datetime.now().isoformat()
        self.notify_memory_handler("rename", chat.get("id"), title)
        self.refresh_chat_list_titles()
        self.save_chats()
        self.header_status.configure(text="Chat renamed")

    def delete_current_chat(self, event=None):

        chat = self.current_chat()
        if not chat:
            return

        if not messagebox.askyesno(
            "Delete chat",
            f"Delete '{chat.get('title', 'Untitled chat')}' and its conversation memory?",
            parent=self.root
        ):
            return

        chat_id = chat.get("id")
        chats = self.chats.get("chats", [])
        old_index = next(
            (index for index, item in enumerate(chats) if item.get("id") == chat_id),
            0
        )
        self.chats["chats"] = [
            item for item in chats if item.get("id") != chat_id
        ]
        self.notify_memory_handler("delete", chat_id)

        remaining = self.chats.get("chats", [])
        if remaining:
            new_index = min(old_index, len(remaining) - 1)
            self.current_chat_id = remaining[new_index].get("id")
            self.empty_history.place_forget()
        else:
            self.current_chat_id = None
            self.empty_history.place(x=20, y=250)

        self.refresh_chat_list_titles()
        self.render_current_chat()
        self.save_chats()
        self.header_status.configure(text="Chat deleted")

    def clear_all_chats(self):

        if not self.chats.get("chats"):
            return
        if not messagebox.askyesno(
            "Clear all chats",
            "Delete every chat and all conversation memory?",
            parent=self.root
        ):
            return

        self.chats = {"chats": []}
        self.current_chat_id = None
        self.thinking_traces.clear()
        self.latest_trace_id = None
        self.notify_memory_handler("clear_all")
        self.refresh_chat_list_titles()
        self.render_current_chat()
        self.empty_history.place(x=20, y=250)
        self.save_chats()
        self.header_status.configure(text="All chats cleared")

    def insert_chat_message(self, sender, text):

        tag_name = f"tag_{sender.lower()}"
        color = self.colors["accent"] if sender == "You" else self.colors["muted"]

        self.chat_area.tag_configure(
            tag_name,
            foreground=color,
            font=("Segoe UI", 10, "bold")
        )

        self.chat_area.insert("end", f"{sender}\n", tag_name)
        self.chat_area.insert("end", f"{text}\n\n")

    def attach_files(self):

        paths = filedialog.askopenfilenames(
            title="Attach files to Canri",
            filetypes=[
                ("Supported files", "*.png *.jpg *.jpeg *.gif *.webp *.mp4 *.mov *.mp3 *.wav *.pdf *.txt *.md *.json *.py *.js *.zip *.exe"),
                ("Images", "*.png *.jpg *.jpeg *.gif *.webp *.bmp *.svg"),
                ("Video", "*.mp4 *.mov *.avi *.mkv *.webm"),
                ("Audio", "*.mp3 *.wav *.ogg *.flac *.m4a"),
                ("Documents", "*.pdf *.txt *.md *.docx *.pptx"),
                ("Code and data", "*.py *.js *.json *.yaml *.yml *.csv *.html *.css"),
                ("All files", "*.*")
            ]
        )

        if not paths:
            return

        for path in paths:
            if path not in self.attached_files:
                self.attached_files.append(path)

        self.update_attachment_label()
        self.header_status.configure(text=f"{len(paths)} file(s) attached")

    def clear_attachments(self):

        self.attached_files = []
        self.update_attachment_label()
        self.header_status.configure(text="Attachments cleared")

    def update_attachment_label(self):

        if not self.attached_files:
            self.attachment_label.configure(text="No files attached")
            return

        names = [
            Path(path).name
            for path in self.attached_files[:4]
        ]

        extra = ""
        if len(self.attached_files) > 4:
            extra = f" +{len(self.attached_files) - 4} more"

        self.attachment_label.configure(
            text="Attached: " + ", ".join(names) + extra
        )

    def send_message(self):

        message = self.message_entry.get("1.0", "end").strip()

        if not message and not self.attached_files:
            return

        self.empty_state.place_forget()

        if message:
            self.add_chat_message("You", message)

        chat = self.ensure_current_chat(message)
        attached_files = list(self.attached_files)
        chat_id = chat.get("id")
        self.append_chat_record(
            "USER",
            message,
            chat_id=chat_id,
            attachments=attached_files
        )

        if attached_files:
            file_lines = "\n".join(
                f"- {Path(path).name}"
                for path in attached_files
            )
            self.add_chat_message("Files", file_lines)

        self.message_entry.delete("1.0", "end")
        self.attached_files = []
        self.update_attachment_label()

        if not self.message_handler:
            self.header_status.configure(text="No brain pipeline connected")
            self.add_chat_message("Canri", "המסך מוכן, אבל עדיין לא חובר pipeline של מוחות.")
            return

        self.header_status.configure(text="Canri is thinking...")
        self.start_thinking_timer()
        trace_id = self.start_live_thinking_trace(message, attached_files)
        self.show_thinking_trace(trace_id)

        threading.Thread(
            target=self.process_message_in_background,
            args=(message, attached_files, trace_id, chat_id),
            daemon=True
        ).start()

    def process_message_in_background(self, message, attached_files, trace_id, chat_id):

        def progress_callback(event):
            self.root.after(
                0,
                lambda event=event: self.update_live_thinking_trace(trace_id, event)
            )

        try:
            try:
                result = self.message_handler(
                    message,
                    attached_files,
                    progress_callback,
                    chat_id
                )
            except TypeError:
                result = self.message_handler(
                    message,
                    attached_files
                )

            if isinstance(result, dict):
                text = (
                    result.get("display_text")
                    or result.get("answer")
                    or str(result)
                )
                thinking_trace = (
                    result.get("thinking_trace")
                    or result.get("debug_trace")
                    or result.get("trace")
                )
                agent_changes = result.get("agent_changes")
                memory_usage = result.get("memory_usage")
            else:
                text = str(result)
                thinking_trace = None
                agent_changes = None
                memory_usage = None

            self.root.after(
                0,
                lambda: self.show_canri_response(
                    text,
                    thinking_trace,
                    trace_id,
                    chat_id,
                    agent_changes,
                    memory_usage,
                )
            )

        except Exception as error:
            self.root.after(
                0,
                lambda: self.update_live_thinking_trace(
                    trace_id,
                    {
                        "stage": "error",
                        "detail": str(error),
                        "data": {}
                    }
                )
            )
            self.root.after(
                0,
                lambda error=error, chat_id=chat_id: self.show_canri_response(
                    f"שגיאה בהרצת המוחות: {error}",
                    chat_id=chat_id
                )
            )

    def show_canri_response(
        self,
        text,
        thinking_trace=None,
        trace_id=None,
        chat_id=None,
        agent_changes=None,
        memory_usage=None,
    ):

        if thinking_trace and trace_id:
            self.finish_live_thinking_trace(trace_id, thinking_trace)

        if not chat_id or chat_id == self.current_chat_id:
            self.add_chat_message(
                "Canri",
                text,
                thinking_trace,
                trace_id,
                agent_changes,
                memory_usage,
            )
        self.append_chat_record(
            "CANRI",
            text,
            trace_id,
            chat_id=chat_id,
            agent_changes=agent_changes,
            memory_usage=memory_usage,
        )
        self.refresh_chat_list_titles()
        self.stop_thinking_timer()

        elapsed = self.current_thinking_elapsed()
        if elapsed is not None:
            self.header_status.configure(
                text=f"Ready - thought for {self.format_elapsed(elapsed)}"
            )
        else:
            self.header_status.configure(text="Ready")

    def add_chat_message(
        self,
        sender,
        text,
        thinking_trace=None,
        trace_id=None,
        agent_changes=None,
        memory_usage=None,
    ):

        self.chat_area.configure(state="normal")

        tag_name = f"tag_{sender.lower()}"
        color = self.colors["accent"] if sender == "You" else self.colors["muted"]

        self.chat_area.tag_configure(
            tag_name,
            foreground=color,
            font=("Segoe UI", 10, "bold")
        )

        self.chat_area.insert("end", f"{sender}\n", tag_name)
        self.chat_area.insert("end", f"{text}\n\n")

        if sender == "Canri" and (thinking_trace or trace_id):
            if not trace_id:
                trace_id = self.store_thinking_trace(thinking_trace)
            self.insert_thinking_button(trace_id)

        if sender == "Canri" and isinstance(thinking_trace, dict):
            self.insert_information_button(thinking_trace)

        if sender == "Canri" and isinstance(memory_usage, dict):
            self.insert_memory_button(memory_usage, trace_id)

        if sender == "Canri" and isinstance(agent_changes, dict):
            self.insert_agent_change_card(agent_changes)

        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    @staticmethod
    def _agent_write_changes(agent_changes):
        if not isinstance(agent_changes, dict):
            return []
        results = agent_changes.get("action_results", [])
        return [
            item for item in results
            if isinstance(item, dict) and item.get("type") == "write_file" and item.get("path")
        ]

    def insert_agent_change_card(self, agent_changes):
        if agent_changes.get("status") == "approval_required":
            self.insert_agent_approval_card(agent_changes)
            return

        changes = self._agent_write_changes(agent_changes)
        if not changes:
            return

        unique_paths = {str(change.get("path")) for change in changes}
        added = sum(int(change.get("added_lines", 0) or 0) for change in changes)
        removed = sum(int(change.get("removed_lines", 0) or 0) for change in changes)

        card = tk.Frame(
            self.chat_area,
            bg=self.colors["panel_2"],
            highlightthickness=1,
            highlightbackground=self.colors["sidebar_border"],
            padx=14,
            pady=12,
        )
        card.grid_columnconfigure(0, weight=1)

        title = tk.Label(
            card,
            text=f"Agent edited {len(unique_paths)} file(s)",
            bg=self.colors["panel_2"],
            fg=self.colors["text"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="w")
        totals = tk.Label(
            card,
            text=f"+{added}  -{removed}",
            bg=self.colors["panel_2"],
            fg=self.colors["success"] if added else self.colors["muted"],
            font=("Consolas", 10, "bold"),
            anchor="e",
        )
        totals.grid(row=0, column=1, sticky="e", padx=(18, 0))

        for row, change in enumerate(changes[:8], start=1):
            path = str(change.get("path"))
            details = (
                f"+{int(change.get('added_lines', 0) or 0)} "
                f"-{int(change.get('removed_lines', 0) or 0)}  "
                f"{int(change.get('after_line_count', 0) or 0)} lines"
            )
            file_button = tk.Button(
                card,
                text=path,
                command=lambda change=change, changes=agent_changes: self.show_agent_file_change(change, changes),
                bg=self.colors["panel_2"],
                fg=self.colors["text"],
                activebackground=self.colors["accent_hover"],
                activeforeground=self.colors["text"],
                relief="flat",
                borderwidth=0,
                anchor="w",
                cursor="hand2",
                font=("Segoe UI", 10),
                padx=0,
                pady=4,
            )
            file_button.grid(row=row, column=0, sticky="w")
            metric = tk.Label(
                card,
                text=details,
                bg=self.colors["panel_2"],
                fg=self.colors["muted"],
                font=("Consolas", 9),
                anchor="e",
            )
            metric.grid(row=row, column=1, sticky="e", padx=(18, 0))

        if len(changes) > 8:
            extra = tk.Label(
                card,
                text=f"And {len(changes) - 8} more file(s)",
                bg=self.colors["panel_2"],
                fg=self.colors["muted"],
                font=("Segoe UI", 9),
                anchor="w",
            )
            extra.grid(row=9, column=0, columnspan=2, sticky="w", pady=(5, 0))

        self.chat_area.window_create("end", window=card, padx=4, pady=4)
        self.chat_area.insert("end", "\n\n")

    def submit_agent_approval(self, approval_id, approved, approve_button, deny_button):
        """Submit the Agent's existing approval command through the normal chat path."""
        if not approval_id:
            return
        approve_button.configure(state="disabled")
        deny_button.configure(state="disabled")
        command = "approve" if approved else "reject"
        self.message_entry.delete("1.0", "end")
        self.message_entry.insert("1.0", f"/agent {command} {approval_id}")
        self.send_message()

    def insert_agent_approval_card(self, agent_changes):
        approval_id = str(agent_changes.get("approval_id", "")).strip()
        actions = [
            item for item in agent_changes.get("planned_actions", [])
            if isinstance(item, dict)
        ]
        if not approval_id:
            return

        file_actions = [
            item for item in actions
            if item.get("type") in {"write_file", "create_file"}
        ]
        command_actions = [
            item for item in actions if item.get("type") == "run_command"
        ]
        card = tk.Frame(
            self.chat_area,
            bg=self.colors["panel_2"],
            highlightthickness=1,
            highlightbackground=self.colors["accent"],
            padx=14,
            pady=12,
        )
        card.grid_columnconfigure(0, weight=1)
        tk.Label(
            card,
            text="Agent approval required",
            bg=self.colors["panel_2"],
            fg=self.colors["text"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(
            card,
            text="No file has been changed. Review the planned actions, then approve or deny them.",
            bg=self.colors["panel_2"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=620,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 8))

        row = 2
        for action in file_actions[:10]:
            target = str(action.get("path", "file"))
            characters = int(action.get("content_characters", 0) or 0)
            tk.Label(
                card,
                text=f"File: {target}",
                bg=self.colors["panel_2"],
                fg=self.colors["text"],
                font=("Consolas", 9),
                anchor="w",
            ).grid(row=row, column=0, sticky="w")
            tk.Label(
                card,
                text=f"{characters} characters planned",
                bg=self.colors["panel_2"],
                fg=self.colors["muted"],
                font=("Consolas", 9),
                anchor="e",
            ).grid(row=row, column=1, sticky="e", padx=(18, 0))
            row += 1
        for action in command_actions[:5]:
            command = action.get("command", "command")
            if isinstance(command, list):
                command = " ".join(str(part) for part in command)
            tk.Label(
                card,
                text=f"Command: {command}",
                bg=self.colors["panel_2"],
                fg=self.colors["accent"],
                font=("Consolas", 9),
                anchor="w",
            ).grid(row=row, column=0, columnspan=2, sticky="w")
            row += 1

        controls = tk.Frame(card, bg=self.colors["panel_2"])
        controls.grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 0))
        approve_button = tk.Button(
            controls,
            text="Approve",
            bg=self.colors["success"],
            fg=self.colors["app"],
            activebackground=self.colors["accent_hover"],
            activeforeground=self.colors["text"],
            relief="flat",
            cursor="hand2",
            padx=14,
            pady=5,
        )
        deny_button = tk.Button(
            controls,
            text="Deny",
            bg=self.colors["danger"],
            fg=self.colors["text"],
            activebackground=self.colors["danger"],
            activeforeground=self.colors["text"],
            relief="flat",
            cursor="hand2",
            padx=14,
            pady=5,
        )
        approve_button.configure(
            command=lambda: self.submit_agent_approval(
                approval_id, True, approve_button, deny_button
            )
        )
        deny_button.configure(
            command=lambda: self.submit_agent_approval(
                approval_id, False, approve_button, deny_button
            )
        )
        approve_button.pack(side="left")
        deny_button.pack(side="left", padx=(8, 0))

        self.chat_area.window_create("end", window=card, padx=4, pady=4)
        self.chat_area.insert("end", "\n\n")

    def show_agent_file_change(self, change, agent_changes):
        path = str(change.get("path", "Edited file"))
        window = tk.Toplevel(self.root)
        window.title(f"Agent change - {path}")
        window.geometry("1120x720")
        window.minsize(760, 480)
        window.configure(bg=self.colors["app"])
        window.grid_columnconfigure(0, weight=1)
        window.grid_columnconfigure(1, weight=1)
        window.grid_rowconfigure(2, weight=1)

        heading = tk.Label(
            window,
            text=path,
            bg=self.colors["app"],
            fg=self.colors["text"],
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        )
        heading.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(16, 3))
        summary = tk.Label(
            window,
            text=(
                f"+{int(change.get('added_lines', 0) or 0)} lines added   "
                f"-{int(change.get('removed_lines', 0) or 0)} lines removed   "
                f"{int(change.get('before_line_count', 0) or 0)} -> "
                f"{int(change.get('after_line_count', 0) or 0)} total lines"
            ),
            bg=self.colors["app"],
            fg=self.colors["muted"],
            font=("Consolas", 10),
            anchor="w",
        )
        summary.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 12))

        code_label = tk.Label(window, text="Current code", bg=self.colors["app"], fg=self.colors["text"], font=("Segoe UI", 10, "bold"), anchor="w")
        code_label.grid(row=2, column=0, sticky="new", padx=(18, 8))
        diff_label = tk.Label(window, text="Change details", bg=self.colors["app"], fg=self.colors["text"], font=("Segoe UI", 10, "bold"), anchor="w")
        diff_label.grid(row=2, column=1, sticky="new", padx=(8, 18))

        code_box = ScrolledText(window, bg=self.colors["panel"], fg=self.colors["text"], insertbackground=self.colors["text"], relief="flat", wrap="none", font=("Consolas", 10), padx=12, pady=10)
        diff_box = ScrolledText(window, bg=self.colors["panel"], fg=self.colors["text"], insertbackground=self.colors["text"], relief="flat", wrap="none", font=("Consolas", 10), padx=12, pady=10)
        code_box.grid(row=3, column=0, sticky="nsew", padx=(18, 8), pady=(0, 18))
        diff_box.grid(row=3, column=1, sticky="nsew", padx=(8, 18), pady=(0, 18))
        window.grid_rowconfigure(3, weight=1)

        content = str(change.get("after_content", ""))
        if change.get("after_content_truncated"):
            content += "\n\n[Preview truncated because the file is large.]"
        diff = str(change.get("diff_preview", "No text difference was recorded."))
        if change.get("diff_truncated"):
            diff += "\n\n[Diff preview truncated because the change is large.]"
        code_box.insert("1.0", content)
        diff_box.insert("1.0", diff)
        code_box.configure(state="disabled")
        diff_box.configure(state="disabled")
        self.bind_thinking_text_shortcuts(code_box)
        self.bind_thinking_text_shortcuts(diff_box)

    def start_live_thinking_trace(self, message, attached_files):

        self.trace_counter += 1
        trace_id = f"trace_{self.trace_counter}"
        self.latest_trace_id = trace_id

        self.thinking_traces[trace_id] = {
            "title": "Canri live thinking",
            "status": "running",
            "input": {
                "message": message,
                "attached_files": [
                    Path(path).name
                    for path in attached_files
                ]
            },
            "current_stage": "queued",
            "current_detail": "Message received",
            "events": [
                {
                    "stage": "queued",
                    "detail": "Message received and queued for processing",
                    "data": {}
                }
            ]
        }

        self.thinking_button.configure(
            state="normal",
            fg=self.colors["text"]
        )

        return trace_id

    def update_live_thinking_trace(self, trace_id, event):

        trace = self.thinking_traces.setdefault(
            trace_id,
            {
                "title": "Canri live thinking",
                "status": "running",
                "events": []
            }
        )

        if not isinstance(event, dict):
            event = {
                "stage": "update",
                "detail": str(event),
                "data": {}
            }

        trace["status"] = "complete" if event.get("stage") == "complete" else "running"
        trace["current_stage"] = event.get("stage")
        trace["current_detail"] = event.get("detail")
        trace.setdefault("events", []).append(event)

        self.refresh_thinking_window(trace_id)

    def finish_live_thinking_trace(self, trace_id, final_trace):

        trace = self.thinking_traces.setdefault(
            trace_id,
            {
                "title": "Canri live thinking",
                "events": []
            }
        )

        trace["status"] = "complete"
        trace["elapsed_seconds"] = self.current_thinking_elapsed()
        trace["elapsed"] = self.format_elapsed(trace["elapsed_seconds"] or 0)
        trace["current_stage"] = "response_ready"
        trace["current_detail"] = "Final answer is ready"
        trace["final_trace"] = final_trace
        trace.setdefault("events", []).append({
            "stage": "response_ready",
            "detail": "Final answer is ready",
            "data": {}
        })

        self.refresh_thinking_window(trace_id)

    def start_thinking_timer(self):

        self.thinking_started_at = time.perf_counter()
        self.update_thinking_timer()

    def current_thinking_elapsed(self):

        if self.thinking_started_at is None:
            return None

        return time.perf_counter() - self.thinking_started_at

    def format_elapsed(self, seconds):

        seconds = max(float(seconds or 0), 0)
        minutes = int(seconds // 60)
        remaining = seconds % 60

        if minutes:
            return f"{minutes}m {remaining:04.1f}s"

        return f"{remaining:.1f}s"

    def update_thinking_timer(self):

        elapsed = self.current_thinking_elapsed()
        if elapsed is None:
            return

        self.header_status.configure(
            text=f"Canri is thinking... {self.format_elapsed(elapsed)}"
        )

        if self.latest_trace_id:
            trace = self.thinking_traces.get(self.latest_trace_id)
            if isinstance(trace, dict) and trace.get("status") == "running":
                trace["elapsed_seconds"] = round(elapsed, 2)
                trace["elapsed"] = self.format_elapsed(elapsed)
                self.refresh_thinking_window(self.latest_trace_id)

        self.thinking_timer_job = self.root.after(
            250,
            self.update_thinking_timer
        )

    def stop_thinking_timer(self):

        if self.thinking_timer_job is not None:
            try:
                self.root.after_cancel(self.thinking_timer_job)
            except tk.TclError:
                pass
            self.thinking_timer_job = None

    def store_thinking_trace(self, thinking_trace):

        self.trace_counter += 1
        trace_id = f"trace_{self.trace_counter}"
        self.thinking_traces[trace_id] = thinking_trace
        self.latest_trace_id = trace_id
        self.thinking_button.configure(
            state="normal",
            fg=self.colors["text"]
        )
        return trace_id

    def insert_thinking_button(self, trace_id):

        button = tk.Button(
            self.chat_area,
            text="Thinking details",
            command=lambda: self.show_thinking_trace(trace_id),
            bg=self.colors["panel_2"],
            fg=self.colors["text"],
            activebackground=self.colors["accent_hover"],
            activeforeground=self.colors["text"],
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            padx=10,
            pady=4
        )

        self.chat_area.window_create("end", window=button)
        self.chat_area.insert("end", "\n\n")

    @staticmethod
    def format_memory_size(value):
        size = max(0, int(value or 0))
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"
        if size >= 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"

    def insert_memory_button(self, memory_usage, trace_id=None):
        if not isinstance(memory_usage, dict):
            return
        text = (
            f"Memory {self.format_memory_size(memory_usage.get('total_bytes'))}  |  "
            f"LFM {self.format_memory_size(memory_usage.get('lfm_bytes'))}  |  "
            f"LLM {self.format_memory_size(memory_usage.get('llm_bytes'))}"
        )
        button = tk.Button(
            self.chat_area,
            text=text,
            command=lambda: self.show_memory_usage(memory_usage, trace_id),
            bg=self.colors["panel_2"],
            fg=self.colors["success"],
            activebackground=self.colors["accent_hover"],
            activeforeground=self.colors["text"],
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            padx=10,
            pady=4,
        )
        self.chat_area.window_create("end", window=button)
        self.chat_area.insert("end", "\n\n")

    @staticmethod
    def information_size(value):
        """Return the serialized size of context that was actually available to a request."""
        if value in (None, "", [], {}):
            return 0
        try:
            return len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"))
        except (TypeError, ValueError):
            return len(str(value).encode("utf-8", errors="replace"))

    @staticmethod
    def information_item_count(value):
        if isinstance(value, dict):
            return len(value)
        if isinstance(value, (list, tuple, set)):
            return len(value)
        return 1 if value not in (None, "") else 0

    def information_usage_from_trace(self, thinking_trace):
        """Explain retrieved request context by source, not just brain-to-brain traffic."""
        trace = thinking_trace if isinstance(thinking_trace, dict) else {}
        if isinstance(trace.get("final_trace"), dict):
            trace = trace["final_trace"]
        manager = trace.get("manager", {}) if isinstance(trace.get("manager"), dict) else {}
        memory = trace.get("memory", {}) if isinstance(trace.get("memory"), dict) else {}
        understanding = trace.get("understanding", {}) if isinstance(trace.get("understanding"), dict) else {}
        brain_results = trace.get("brain_results", {}) if isinstance(trace.get("brain_results"), dict) else {}

        sources = [
            ("Conversation memory", memory),
            ("Dictionary context", manager.get("dictionary_context")),
            ("Local data context", manager.get("local_data_context")),
            ("Knowledge and scanner context", manager.get("knowledge_context")),
            ("Understanding report", understanding),
            ("Specialist brain results", brain_results),
        ]
        rows = [
            {
                "source": name,
                "bytes": self.information_size(value),
                "items": self.information_item_count(value),
                "used": value not in (None, "", [], {}),
            }
            for name, value in sources
        ]
        return {
            "sources": rows,
            "total_bytes": sum(row["bytes"] for row in rows),
        }

    def insert_information_button(self, thinking_trace):
        usage = self.information_usage_from_trace(thinking_trace)
        text = f"Information used {self.format_memory_size(usage['total_bytes'])}"
        button = tk.Button(
            self.chat_area,
            text=text,
            command=lambda: self.show_information_usage(usage),
            bg=self.colors["panel_2"],
            fg=self.colors["accent"],
            activebackground=self.colors["accent_hover"],
            activeforeground=self.colors["text"],
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            padx=10,
            pady=4,
        )
        self.chat_area.window_create("end", window=button)
        self.chat_area.insert("end", "\n")

    def show_information_usage(self, usage):
        window = tk.Toplevel(self.root)
        window.title("CANRI Information Used")
        window.geometry("820x560")
        window.configure(bg=self.colors["app"])
        tk.Label(
            window,
            text=(
                f"Information used for this answer: "
                f"{self.format_memory_size(usage.get('total_bytes'))}"
            ),
            bg=self.colors["app"],
            fg=self.colors["text"],
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 8))
        tk.Label(
            window,
            text=(
                "This shows the request context supplied from each source. "
                "It is separate from the Memory button, which measures all internal "
                "read/write transfers between brains."
            ),
            bg=self.colors["app"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=770,
        ).pack(fill="x", padx=18, pady=(0, 10))
        details = ScrolledText(
            window,
            bg=self.colors["panel"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            wrap="word",
            font=("Consolas", 10),
            padx=14,
            pady=12,
        )
        details.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        for row in usage.get("sources", []):
            state = "used" if row.get("used") else "not used"
            details.insert(
                "end",
                f"{row.get('source')}: {state} | "
                f"{self.format_memory_size(row.get('bytes'))} | "
                f"{row.get('items')} top-level items\n"
            )
        details.configure(state="disabled")
        self.bind_thinking_text_shortcuts(details)

    def memory_usage_text(self, memory_usage):
        lines = [
            "CANRI information-memory usage",
            "",
            "This measures UTF-8 context and report bytes read, written, and transferred. "
            "It is not operating-system RAM.",
            "",
            f"Request: {memory_usage.get('request_id', '')}",
            f"Total: {self.format_memory_size(memory_usage.get('total_bytes'))}",
            f"LFM: {self.format_memory_size(memory_usage.get('lfm_bytes'))}",
            f"LLM: {self.format_memory_size(memory_usage.get('llm_bytes'))}",
            f"Events: {memory_usage.get('events', 0)}",
            "",
            "Per brain",
        ]
        for item in memory_usage.get("brains", []):
            if not isinstance(item, dict):
                continue
            lines.append(
                f"{item.get('brain', 'brain')}: "
                f"read {self.format_memory_size(item.get('input_bytes'))}, "
                f"wrote {self.format_memory_size(item.get('output_bytes'))}, "
                f"total {self.format_memory_size(item.get('transfer_bytes'))}, "
                f"calls {item.get('calls', 0)}"
            )
        lines.extend(["", "Transfers"])
        for item in memory_usage.get("transfers", [])[:100]:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"{item.get('from')} -> {item.get('to')}: "
                f"{self.format_memory_size(item.get('bytes'))} "
                f"({item.get('transfers', 0)} transfers, {item.get('direction')})"
            )
        return "\n".join(lines)

    def show_memory_usage(self, memory_usage, trace_id=None):
        window = tk.Toplevel(self.root)
        window.title("CANRI Memory Details")
        window.geometry("920x680")
        window.configure(bg=self.colors["app"])
        header = tk.Frame(window, bg=self.colors["app"])
        header.pack(fill="x", padx=18, pady=(16, 8))
        tk.Label(
            header,
            text="Memory details",
            bg=self.colors["app"],
            fg=self.colors["text"],
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")
        text_box = ScrolledText(
            window,
            bg=self.colors["panel"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            wrap="word",
            font=("Consolas", 10),
            padx=14,
            pady=12,
        )
        text_box.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        text_box.insert("1.0", self.memory_usage_text(memory_usage))
        text_box.configure(state="disabled")
        self.bind_thinking_text_shortcuts(text_box)

    def show_memory_statistics(self):
        try:
            payload = json.loads(MEMORY_STATS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {"requests": [], "totals": {}}
        requests = [item for item in payload.get("requests", []) if isinstance(item, dict)]
        window = tk.Toplevel(self.root)
        window.title("CANRI Memory Statistics")
        window.geometry("1040x760")
        window.configure(bg=self.colors["app"])

        totals = payload.get("totals", {}) if isinstance(payload, dict) else {}
        tk.Label(
            window,
            text=(
                f"Memory statistics  |  Requests {totals.get('requests', len(requests))}  |  "
                f"Total {self.format_memory_size(totals.get('total_bytes'))}  |  "
                f"LFM {self.format_memory_size(totals.get('lfm_bytes'))}  |  "
                f"LLM {self.format_memory_size(totals.get('llm_bytes'))}"
            ),
            bg=self.colors["app"],
            fg=self.colors["text"],
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 8))

        canvas = tk.Canvas(
            window,
            height=220,
            bg=self.colors["panel"],
            highlightthickness=1,
            highlightbackground=self.colors["input_border"],
        )
        canvas.pack(fill="x", padx=18, pady=(0, 10))
        recent = requests[-30:]
        maximum = max([int(item.get("total_bytes", 0) or 0) for item in recent] or [1])

        def draw_graph(event=None):
            canvas.delete("all")
            width = max(canvas.winfo_width(), 200)
            height = max(canvas.winfo_height(), 160)
            if not recent:
                canvas.create_text(
                    width / 2,
                    height / 2,
                    text="No completed request statistics yet",
                    fill=self.colors["muted"],
                )
                return
            bar_width = max(3, (width - 40) / len(recent))
            for index, item in enumerate(recent):
                x0 = 20 + index * bar_width
                x1 = x0 + max(2, bar_width - 2)
                lfm = int(item.get("lfm_bytes", 0) or 0)
                llm = int(item.get("llm_bytes", 0) or 0)
                lfm_height = (height - 30) * lfm / maximum
                llm_height = (height - 30) * llm / maximum
                canvas.create_rectangle(
                    x0,
                    height - 20 - lfm_height,
                    x1,
                    height - 20,
                    fill=self.colors["accent"],
                    outline="",
                )
                canvas.create_rectangle(
                    x0,
                    height - 20 - lfm_height - llm_height,
                    x1,
                    height - 20 - lfm_height,
                    fill=self.colors["success"],
                    outline="",
                )
            canvas.create_text(24, 12, text="LFM", fill=self.colors["accent"], anchor="w")
            canvas.create_text(74, 12, text="LLM", fill=self.colors["success"], anchor="w")

        canvas.bind("<Configure>", draw_graph)
        draw_graph()

        details = ScrolledText(
            window,
            bg=self.colors["panel"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            wrap="word",
            font=("Consolas", 10),
            padx=14,
            pady=12,
        )
        details.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        for index, item in enumerate(reversed(recent), start=1):
            details.insert(
                "end",
                f"{index}. {item.get('user_preview', '')}\n"
                f"   Total {self.format_memory_size(item.get('total_bytes'))} | "
                f"LFM {self.format_memory_size(item.get('lfm_bytes'))} | "
                f"LLM {self.format_memory_size(item.get('llm_bytes'))}\n\n",
            )
        details.configure(state="disabled")
        self.bind_thinking_text_shortcuts(details)

    def knowledge_storage_inventory(self):
        """Summarize available CANRI data without loading large JSON or model files."""
        project_dir = Path(__file__).parent
        dictionary_dir = project_dir / "UnderstandingDk" / "data"
        llm_dir = project_dir / "domain_packages" / "local_llm"
        media_dirs = {
            project_dir / "generated_images",
            project_dir / "generated_movies",
        }
        groups = {
            "Knowledge and scanners": {"files": [], "bytes": 0},
            "Dictionaries and language data": {"files": [], "bytes": 0},
            "Local LLM models and training": {"files": [], "bytes": 0},
            "Generated media": {"files": [], "bytes": 0},
            "Other CANRI data": {"files": [], "bytes": 0},
        }

        for path in project_dir.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue

            lowered_name = path.name.casefold()
            if dictionary_dir in path.parents or "dictionary" in lowered_name:
                group = "Dictionaries and language data"
            elif llm_dir in path.parents or path.suffix.casefold() in {".pt", ".pth", ".safetensors"}:
                group = "Local LLM models and training"
            elif any(media_dir == path.parent or media_dir in path.parents for media_dir in media_dirs):
                group = "Generated media"
            elif any(marker in lowered_name for marker in ("knowledge", "scanner", "scan_", "article", "source")):
                group = "Knowledge and scanners"
            elif path.suffix.casefold() in {".json", ".jsonl", ".csv", ".txt"}:
                group = "Other CANRI data"
            else:
                continue

            groups[group]["files"].append((path, size))
            groups[group]["bytes"] += size

        return groups

    def show_knowledge_statistics(self):
        inventory = self.knowledge_storage_inventory()
        total_files = sum(len(group["files"]) for group in inventory.values())
        total_bytes = sum(group["bytes"] for group in inventory.values())

        window = tk.Toplevel(self.root)
        window.title("CANRI Knowledge Statistics")
        window.geometry("980x720")
        window.configure(bg=self.colors["app"])

        tk.Label(
            window,
            text=(
                f"Knowledge available to CANRI  |  Files {total_files}  |  "
                f"Stored data {self.format_memory_size(total_bytes)}"
            ),
            bg=self.colors["app"],
            fg=self.colors["text"],
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 8))

        note = (
            "This is available project knowledge on disk, not per-request memory. "
            "CANRI searches relevant excerpts instead of loading all of it for every answer."
        )
        tk.Label(
            window,
            text=note,
            bg=self.colors["app"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=920,
        ).pack(fill="x", padx=18, pady=(0, 10))

        details = ScrolledText(
            window,
            bg=self.colors["panel"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            wrap="word",
            font=("Consolas", 10),
            padx=14,
            pady=12,
        )
        details.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        for name, group in inventory.items():
            files = sorted(group["files"], key=lambda item: item[1], reverse=True)
            details.insert(
                "end",
                f"{name}\n"
                f"  Files: {len(files)} | Size: {self.format_memory_size(group['bytes'])}\n"
            )
            for path, size in files[:12]:
                relative = path.relative_to(Path(__file__).parent)
                details.insert(
                    "end",
                    f"  - {relative} ({self.format_memory_size(size)})\n"
                )
            if len(files) > 12:
                details.insert("end", f"  ... and {len(files) - 12} more files\n")
            details.insert("end", "\n")
        details.configure(state="disabled")
        self.bind_thinking_text_shortcuts(details)

    def format_thinking_trace(self, trace):

        try:
            return json.dumps(
                trace,
                indent=2,
                ensure_ascii=False
            )
        except TypeError:
            return str(trace)

    def show_thinking_trace(self, trace_id):

        trace = self.thinking_traces.get(trace_id, {})

        window = tk.Toplevel(self.root)
        window.title("Canri Thinking Details")
        window.geometry("900x640")
        window.configure(bg=self.colors["app"])

        header_row = tk.Frame(
            window,
            bg=self.colors["app"]
        )
        header_row.pack(
            fill="x",
            padx=18,
            pady=(16, 4)
        )
        header_row.grid_columnconfigure(0, weight=1)

        header = tk.Label(
            header_row,
            text="Thinking details",
            bg=self.colors["app"],
            fg=self.colors["text"],
            font=("Segoe UI", 16, "bold"),
            anchor="w"
        )
        header.grid(
            row=0,
            column=0,
            sticky="w"
        )

        copy_button = self.create_button(
            header_row,
            text="Copy all",
            command=lambda: self.copy_thinking_text(text_box),
            bg=self.colors["panel_2"]
        )
        copy_button.grid(
            row=0,
            column=1,
            sticky="e"
        )

        note = tk.Label(
            window,
            text=(
                "Visible brain trace: understanding, routing, selected brains, "
                "confidence, and simulation summaries."
            ),
            bg=self.colors["app"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
            anchor="w"
        )
        note.pack(
            fill="x",
            padx=18,
            pady=(0, 10)
        )

        text_box = ScrolledText(
            window,
            bg=self.colors["panel"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            borderwidth=0,
            wrap="word",
            font=("Consolas", 10),
            padx=14,
            pady=12
        )
        text_box.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=(0, 18)
        )
        text_box.insert("1.0", self.format_thinking_trace(trace))
        text_box.configure(state="disabled")
        self.bind_thinking_text_shortcuts(text_box)
        self.thinking_windows[trace_id] = text_box

        window.protocol(
            "WM_DELETE_WINDOW",
            lambda: self.close_thinking_window(trace_id, window)
        )

    def refresh_thinking_window(self, trace_id):

        text_box = self.thinking_windows.get(trace_id)
        if not text_box:
            return

        try:
            text_box.configure(state="normal")
            text_box.delete("1.0", "end")
            text_box.insert(
                "1.0",
                self.format_thinking_trace(
                    self.thinking_traces.get(trace_id, {})
                )
            )
            text_box.configure(state="disabled")
            text_box.see("end")
        except tk.TclError:
            self.thinking_windows.pop(trace_id, None)

    def bind_thinking_text_shortcuts(self, text_box):

        menu = tk.Menu(
            text_box,
            tearoff=0,
            bg=self.colors["panel_2"],
            fg=self.colors["text"],
            activebackground=self.colors["accent"],
            activeforeground=self.colors["text"]
        )
        menu.add_command(
            label="Copy",
            command=lambda: self.copy_thinking_text(text_box, selected_only=True)
        )
        menu.add_command(
            label="Copy all",
            command=lambda: self.copy_thinking_text(text_box)
        )
        menu.add_command(
            label="Select all",
            command=lambda: self.select_all_thinking_text(text_box)
        )

        text_box.bind(
            "<Control-c>",
            lambda event: self.copy_thinking_text(text_box, selected_only=True)
        )
        text_box.bind(
            "<Control-C>",
            lambda event: self.copy_thinking_text(text_box, selected_only=True)
        )
        text_box.bind(
            "<Control-a>",
            lambda event: self.select_all_thinking_text(text_box)
        )
        text_box.bind(
            "<Control-A>",
            lambda event: self.select_all_thinking_text(text_box)
        )
        text_box.bind(
            "<Button-3>",
            lambda event: self.show_text_menu(menu, event)
        )

    def show_text_menu(self, menu, event):

        try:
            menu.tk_popup(
                event.x_root,
                event.y_root
            )
        finally:
            menu.grab_release()

        return "break"

    def copy_thinking_text(self, text_box, selected_only=False):

        try:
            if selected_only:
                try:
                    text = text_box.get("sel.first", "sel.last")
                except tk.TclError:
                    text = text_box.get("1.0", "end-1c")
            else:
                text = text_box.get("1.0", "end-1c")

            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            self.header_status.configure(text="Thinking details copied")
        except tk.TclError:
            pass

        return "break"

    def select_all_thinking_text(self, text_box):

        try:
            text_box.tag_add("sel", "1.0", "end-1c")
            text_box.mark_set("insert", "1.0")
            text_box.see("1.0")
            text_box.focus_set()
        except tk.TclError:
            pass

        return "break"

    def close_thinking_window(self, trace_id, window):

        self.thinking_windows.pop(trace_id, None)
        window.destroy()

    def show_latest_thinking_trace(self):

        if not self.latest_trace_id:
            return

        self.show_thinking_trace(self.latest_trace_id)

    # ---------- recording ----------

    def toggle_recording(self):

        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):

        try:
            import sounddevice  # noqa: F401
        except ImportError:
            messagebox.showinfo(
                "Recording unavailable",
                "Audio recording needs the optional package 'sounddevice'. The UI is ready, but recording is not installed yet."
            )
            self.header_status.configure(text="Recording package missing")
            return

        self.is_recording = True
        self.recording_frames = []
        self.record_button.configure(
            text="Stop",
            bg=self.colors["danger"]
        )
        self.header_status.configure(text="Recording...")

        self.recording_thread = threading.Thread(
            target=self.record_audio,
            daemon=True
        )
        self.recording_thread.start()

    def record_audio(self):

        import sounddevice as sd

        def callback(indata, frames, time_info, status):
            self.recording_queue.put(indata.copy())

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                callback=callback
            ):
                while self.is_recording:
                    try:
                        frame = self.recording_queue.get(timeout=0.2)
                        self.recording_frames.append(frame)
                    except queue.Empty:
                        pass
        except Exception as error:
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Recording error",
                    str(error)
                )
            )
            self.root.after(
                0,
                self.reset_record_button
            )

    def stop_recording(self):

        self.is_recording = False
        self.reset_record_button()

        if self.recording_thread:
            self.recording_thread.join(timeout=1)

        if not self.recording_frames:
            self.header_status.configure(text="No audio captured")
            return

        path = self.save_recording()
        self.attached_files.append(str(path))
        self.update_attachment_label()
        self.header_status.configure(text=f"Recording saved: {path.name}")

    def reset_record_button(self):

        self.is_recording = False
        self.record_button.configure(
            text="Record",
            bg=self.colors["panel_2"]
        )

    def save_recording(self):

        RECORDING_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        path = RECORDING_DIR / f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"

        with wave.open(str(path), "wb") as file:
            file.setnchannels(1)
            file.setsampwidth(2)
            file.setframerate(self.sample_rate)

            for frame in self.recording_frames:
                file.writeframes(frame.tobytes())

        return path

    # ---------- run ----------

    def run(self):

        self.root.mainloop()


def start_graphics(message_handler=None, memory_handler=None):

    app = CanriGraphics(
        message_handler=message_handler,
        memory_handler=memory_handler
    )
    app.run()
