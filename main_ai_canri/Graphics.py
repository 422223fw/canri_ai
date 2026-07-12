import queue
import shutil
import threading
import wave
import json
import time
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

import tkinter as tk


DATA_DIR = Path(__file__).parent / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
RECORDING_DIR = UPLOAD_DIR / "recordings"
CHAT_FILE = DATA_DIR / "Canri_chats.json"
CHAT_BACKUP_FILE = DATA_DIR / "Canri_chats.backup.json"
CHAT_TEMP_FILE = DATA_DIR / "Canri_chats.tmp.json"


class CanriGraphics:

    def __init__(self, message_handler=None):

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
        self.is_recording = False
        self.recording_thread = None
        self.recording_frames = []
        self.recording_queue = queue.Queue()
        self.sample_rate = 44100
        self.thinking_traces = {}
        self.thinking_windows = {}
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
            y=164
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
        self.chats["chats"] = valid_chats[-500:]

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
        self.save_chats()

        return chat

    def make_chat_title(self, message):

        words = str(message).strip().split()
        if not words:
            return datetime.now().strftime("Chat %H:%M")

        return " ".join(words[:6])[:48]

    def append_chat_record(self, role, text, trace_id=None, chat_id=None, attachments=None):

        chat = self.chat_by_id(chat_id) if chat_id else None
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
        chat.setdefault("messages", []).append(record)
        chat["updated_utc"] = datetime.now().isoformat()
        self.save_chats()

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
        self.save_chats()

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
            else:
                text = str(result)
                thinking_trace = None

            self.root.after(
                0,
                lambda: self.show_canri_response(text, thinking_trace, trace_id, chat_id)
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

    def show_canri_response(self, text, thinking_trace=None, trace_id=None, chat_id=None):

        if thinking_trace and trace_id:
            self.finish_live_thinking_trace(trace_id, thinking_trace)

        if not chat_id or chat_id == self.current_chat_id:
            self.add_chat_message("Canri", text, thinking_trace, trace_id)
        self.append_chat_record("CANRI", text, trace_id, chat_id=chat_id)
        self.refresh_chat_list_titles()
        self.stop_thinking_timer()

        elapsed = self.current_thinking_elapsed()
        if elapsed is not None:
            self.header_status.configure(
                text=f"Ready - thought for {self.format_elapsed(elapsed)}"
            )
        else:
            self.header_status.configure(text="Ready")

    def add_chat_message(self, sender, text, thinking_trace=None, trace_id=None):

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

        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

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


def start_graphics(message_handler=None):

    app = CanriGraphics(message_handler=message_handler)
    app.run()
