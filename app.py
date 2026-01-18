"""
Local Code Review & Fix Agent - CustomTkinter Desktop Application

A privacy-first Python desktop app that reviews, explains, and iteratively
fixes Python code using a self-healing agent loop. Fully offline.

Run with: python app.py
"""

import customtkinter as ctk
import threading
import difflib
import sys
import urllib.request
import urllib.error
from tkinter import filedialog, messagebox

from config import get_config, update_config
from agents.graph import run_agent
from models.schemas import AgentState
from tools.executor import execute_code_safely
from utils.helpers import format_code, get_timestamp


# =============================================================================
# OLLAMA STARTUP CHECK
# =============================================================================

def check_ollama_running() -> tuple[bool, str]:
    """
    Check if Ollama is running and accessible.
    
    Returns:
        tuple: (is_running: bool, error_message: str)
    """
    config = get_config()
    ollama_url = config.ollama_base_url
    
    try:
        # Try to connect to Ollama's API endpoint
        req = urllib.request.Request(
            f"{ollama_url}/api/tags",
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return True, ""
    except urllib.error.URLError as e:
        return False, f"Connection failed: {e.reason}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP error: {e.code}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
    
    return False, "Unknown error"


def show_ollama_error_dialog():
    """
    Display a user-friendly error dialog when Ollama is not running.
    
    This creates a standalone dialog window that explains:
    - What Ollama is
    - How to install it
    - That it needs to be running before launching this app
    """
    import webbrowser
    
    # Create a simple root window for the dialog
    root = ctk.CTk()
    root.withdraw()  # Hide the main window
    
    # Create error dialog
    dialog = ctk.CTkToplevel(root)
    dialog.title("Ollama Not Detected")
    dialog.geometry("520x420")
    dialog.resizable(False, False)
    
    # Center the dialog on screen
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - 520) // 2
    y = (dialog.winfo_screenheight() - 420) // 2
    dialog.geometry(f"520x420+{x}+{y}")
    
    # Make it modal and stay on top
    dialog.transient(root)
    dialog.grab_set()
    dialog.lift()
    dialog.attributes('-topmost', True)
    
    # Configure appearance
    dialog.configure(fg_color="#1a1a2e")
    
    # Icon/Title
    title_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    title_frame.pack(pady=(30, 20))
    
    icon_label = ctk.CTkLabel(
        title_frame,
        text="⚠️",
        font=ctk.CTkFont(size=48)
    )
    icon_label.pack()
    
    title_label = ctk.CTkLabel(
        title_frame,
        text="Ollama Not Running",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color="#f0f0f0"
    )
    title_label.pack(pady=(10, 0))
    
    # Message
    message_frame = ctk.CTkFrame(dialog, fg_color="#252542", corner_radius=12)
    message_frame.pack(fill="x", padx=30, pady=10)
    
    message_text = (
        "This application requires Ollama to run local AI models.\n\n"
        "Ollama is a free, open-source tool that runs large language\n"
        "models locally on your machine — no cloud required.\n\n"
        "To use this app:\n"
        "  1. Download and install Ollama\n"
        "  2. Open a terminal and run: ollama pull qwen3:14b\n"
        "  3. Ensure Ollama is running (it starts automatically)\n"
        "  4. Launch this app again"
    )
    
    message_label = ctk.CTkLabel(
        message_frame,
        text=message_text,
        font=ctk.CTkFont(size=13),
        text_color="#c0c0c0",
        justify="left",
        anchor="w"
    )
    message_label.pack(padx=20, pady=20)
    
    # Buttons frame
    button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    button_frame.pack(pady=20)
    
    def open_ollama_website():
        webbrowser.open("https://ollama.com")
    
    def close_app():
        dialog.destroy()
        root.destroy()
        sys.exit(0)
    
    download_btn = ctk.CTkButton(
        button_frame,
        text="Download Ollama",
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color="#4a90d9",
        hover_color="#3a7bc8",
        width=180,
        height=42,
        corner_radius=8,
        command=open_ollama_website
    )
    download_btn.pack(side="left", padx=(0, 15))
    
    exit_btn = ctk.CTkButton(
        button_frame,
        text="Exit",
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color="#4a4a5a",
        hover_color="#5a5a6a",
        width=120,
        height=42,
        corner_radius=8,
        command=close_app
    )
    exit_btn.pack(side="left")
    
    # URL label
    url_label = ctk.CTkLabel(
        dialog,
        text="https://ollama.com",
        font=ctk.CTkFont(size=12, underline=True),
        text_color="#4a90d9",
        cursor="hand2"
    )
    url_label.pack(pady=(5, 20))
    url_label.bind("<Button-1>", lambda e: open_ollama_website())
    
    # Handle window close
    dialog.protocol("WM_DELETE_WINDOW", close_app)
    
    # Run the dialog
    dialog.mainloop()


# =============================================================================
# THEME CONFIGURATION
# =============================================================================

# Professional dark theme with cyan accents
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Custom color palette
COLORS = {
    "bg_dark": "#0d1117",
    "bg_secondary": "#161b22",
    "bg_tertiary": "#21262d",
    "border": "#30363d",
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_muted": "#6e7681",
    "accent_cyan": "#58a6ff",
    "accent_green": "#3fb950",
    "accent_red": "#f85149",
    "accent_yellow": "#d29922",
    "accent_purple": "#a371f7",
}


# =============================================================================
# CUSTOM WIDGETS
# =============================================================================

class LoadingSpinner(ctk.CTkFrame):
    """Animated loading indicator with pulsing effect."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.dots = []
        self.current_dot = 0
        self.is_animating = False
        
        # Create dots
        for i in range(3):
            dot = ctk.CTkLabel(
                self,
                text="●",
                font=ctk.CTkFont(size=16),
                text_color=COLORS["text_muted"]
            )
            dot.pack(side="left", padx=2)
            self.dots.append(dot)
    
    def start(self):
        """Start the animation."""
        self.is_animating = True
        self._animate()
    
    def stop(self):
        """Stop the animation."""
        self.is_animating = False
        for dot in self.dots:
            dot.configure(text_color=COLORS["text_muted"])
    
    def _animate(self):
        """Animate the dots."""
        if not self.is_animating:
            return
        
        # Reset all dots
        for dot in self.dots:
            dot.configure(text_color=COLORS["text_muted"])
        
        # Highlight current dot
        self.dots[self.current_dot].configure(text_color=COLORS["accent_cyan"])
        self.current_dot = (self.current_dot + 1) % 3
        
        # Schedule next animation
        self.after(300, self._animate)


class StatusBadge(ctk.CTkFrame):
    """Status indicator badge with icon and text."""
    
    STATUS_CONFIG = {
        "success": {"icon": "✓", "color": COLORS["accent_green"], "text": "Success"},
        "failed": {"icon": "✗", "color": COLORS["accent_red"], "text": "Failed"},
        "reviewing": {"icon": "◉", "color": COLORS["accent_cyan"], "text": "Reviewing"},
        "fixing": {"icon": "⟳", "color": COLORS["accent_yellow"], "text": "Fixing"},
        "executing": {"icon": "▶", "color": COLORS["accent_purple"], "text": "Executing"},
        "idle": {"icon": "○", "color": COLORS["text_muted"], "text": "Ready"},
    }
    
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.icon_label = ctk.CTkLabel(
            self,
            text="○",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_muted"]
        )
        self.icon_label.pack(side="left", padx=(0, 5))
        
        self.text_label = ctk.CTkLabel(
            self,
            text="Ready",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        self.text_label.pack(side="left")
    
    def set_status(self, status: str):
        """Update the badge status."""
        config = self.STATUS_CONFIG.get(status, self.STATUS_CONFIG["idle"])
        self.icon_label.configure(text=config["icon"], text_color=config["color"])
        self.text_label.configure(text=config["text"])


# =============================================================================
# MAIN APPLICATION CLASS
# =============================================================================

class CodeReviewApp(ctk.CTk):
    """
    Main application window for the Code Review Agent.
    
    Features:
    - Dark mode professional UI
    - Sidebar with configurable settings
    - Code input via text area or file upload
    - Tabbed results view (Review, Fixed Code, Execution, Diff)
    - Background agent execution with loading indicator
    - Ollama connection error handling
    """
    
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("Code Review Agent")
        self.geometry("1400x900")
        self.minsize(1100, 700)
        
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Application state
        self.agent_state: AgentState | None = None
        self.original_code: str = ""
        self.is_processing: bool = False
        self.history: list = []
        
        # Build UI components
        self._create_sidebar()
        self._create_main_area()
        
        # Set dark background
        self.configure(fg_color=COLORS["bg_dark"])
    
    # =========================================================================
    # SIDEBAR
    # =========================================================================
    
    def _create_sidebar(self):
        """Create the left sidebar with settings."""
        self.sidebar = ctk.CTkFrame(
            self,
            width=280,
            corner_radius=0,
            fg_color=COLORS["bg_secondary"]
        )
        self.sidebar.grid(row=0, column=0, sticky="nswe")
        self.sidebar.grid_propagate(False)
        
        # Sidebar title
        title_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(25, 20))
        
        title_icon = ctk.CTkLabel(
            title_frame,
            text="⚙",
            font=ctk.CTkFont(size=24),
            text_color=COLORS["accent_cyan"]
        )
        title_icon.pack(side="left")
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="Settings",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title_label.pack(side="left", padx=(10, 0))
        
        # Scrollable content
        self.sidebar_scroll = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            scrollbar_button_color=COLORS["bg_tertiary"],
            scrollbar_button_hover_color=COLORS["border"]
        )
        self.sidebar_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # LLM Settings Section
        self._create_section_header("🤖  LLM Settings", self.sidebar_scroll)
        
        config = get_config()
        
        # Model name input
        self._create_input_field(
            "Ollama Model",
            "model_entry",
            config.model_name,
            "e.g., qwen3:14b, codellama",
            self.sidebar_scroll
        )
        
        # Ollama URL input
        self._create_input_field(
            "Ollama Base URL",
            "url_entry",
            config.ollama_base_url,
            "e.g., http://localhost:11434",
            self.sidebar_scroll
        )
        
        # Temperature slider
        self._create_slider_field(
            "Temperature",
            "temp_slider",
            0.0, 1.0, config.temperature, 0.1,
            self.sidebar_scroll
        )
        
        # Execution Settings Section
        self._create_section_header("🔒  Execution Settings", self.sidebar_scroll)
        
        # Max retries
        self._create_spinbox_field(
            "Max Retry Attempts",
            "retries_spinbox",
            1, 10, config.max_retries,
            self.sidebar_scroll
        )
        
        # Timeout
        self._create_spinbox_field(
            "Timeout (seconds)",
            "timeout_spinbox",
            1, 60, config.execution_timeout,
            self.sidebar_scroll
        )
        
        # Apply settings button
        self.apply_btn = ctk.CTkButton(
            self.sidebar_scroll,
            text="Apply Settings",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent_cyan"],
            hover_color="#4A90D9",
            height=40,
            corner_radius=8,
            command=self._apply_settings
        )
        self.apply_btn.pack(fill="x", padx=10, pady=(20, 10))
        
        # Session Section
        self._create_section_header("📁  Session", self.sidebar_scroll)
        
        # Clear history button
        self.clear_btn = ctk.CTkButton(
            self.sidebar_scroll,
            text="Clear History",
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            height=36,
            corner_radius=8,
            command=self._clear_history
        )
        self.clear_btn.pack(fill="x", padx=10, pady=(5, 15))
        
        # About Section
        self._create_section_header("ℹ️  About", self.sidebar_scroll)
        
        about_text = ctk.CTkLabel(
            self.sidebar_scroll,
            text=(
                "Local Code Review Agent\n\n"
                "A privacy-first tool that:\n"
                "• 🔍 Reviews your Python code\n"
                "• 🔧 Suggests and applies fixes\n"
                "• 🚀 Tests in a sandbox\n"
                "• 🔄 Retries until it works\n\n"
                "All processing happens locally.\n"
                "No data leaves your machine."
            ),
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            justify="left",
            anchor="w",
            wraplength=230
        )
        about_text.pack(fill="x", padx=15, pady=(5, 20))
    
    def _create_section_header(self, text: str, parent):
        """Create a styled section header."""
        header = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        header.pack(fill="x", padx=10, pady=(20, 10))
    
    def _create_input_field(self, label: str, attr_name: str, default: str, 
                           placeholder: str, parent):
        """Create a labeled text input field."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=5)
        
        lbl = ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        lbl.pack(fill="x")
        
        entry = ctk.CTkEntry(
            frame,
            height=36,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=6,
            placeholder_text=placeholder
        )
        entry.insert(0, default)
        entry.pack(fill="x", pady=(3, 0))
        
        setattr(self, attr_name, entry)
    
    def _create_slider_field(self, label: str, attr_name: str,
                            min_val: float, max_val: float, default: float,
                            step: float, parent):
        """Create a labeled slider field."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=5)
        
        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.pack(fill="x")
        
        lbl = ctk.CTkLabel(
            header_frame,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        lbl.pack(side="left")
        
        value_label = ctk.CTkLabel(
            header_frame,
            text=f"{default:.1f}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["accent_cyan"]
        )
        value_label.pack(side="right")
        
        def on_slider_change(value):
            value_label.configure(text=f"{value:.1f}")
        
        slider = ctk.CTkSlider(
            frame,
            from_=min_val,
            to=max_val,
            number_of_steps=int((max_val - min_val) / step),
            fg_color=COLORS["bg_tertiary"],
            progress_color=COLORS["accent_cyan"],
            button_color=COLORS["accent_cyan"],
            button_hover_color="#4A90D9",
            height=16,
            command=on_slider_change
        )
        slider.set(default)
        slider.pack(fill="x", pady=(8, 0))
        
        setattr(self, attr_name, slider)
        setattr(self, f"{attr_name}_label", value_label)
    
    def _create_spinbox_field(self, label: str, attr_name: str,
                             min_val: int, max_val: int, default: int, parent):
        """Create a labeled numeric spinbox field."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=5)
        
        lbl = ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        lbl.pack(fill="x")
        
        spinbox_frame = ctk.CTkFrame(frame, fg_color="transparent")
        spinbox_frame.pack(fill="x", pady=(3, 0))
        
        # Using entry with +/- buttons for spinbox effect
        entry = ctk.CTkEntry(
            spinbox_frame,
            width=80,
            height=36,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=6,
            justify="center"
        )
        entry.insert(0, str(default))
        entry.pack(side="left")
        
        btn_frame = ctk.CTkFrame(spinbox_frame, fg_color="transparent")
        btn_frame.pack(side="left", padx=(10, 0))
        
        def increment():
            try:
                val = int(entry.get()) + 1
                if val <= max_val:
                    entry.delete(0, "end")
                    entry.insert(0, str(val))
            except ValueError:
                pass
        
        def decrement():
            try:
                val = int(entry.get()) - 1
                if val >= min_val:
                    entry.delete(0, "end")
                    entry.insert(0, str(val))
            except ValueError:
                pass
        
        minus_btn = ctk.CTkButton(
            btn_frame,
            text="−",
            width=32,
            height=32,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            corner_radius=6,
            command=decrement
        )
        minus_btn.pack(side="left", padx=(0, 4))
        
        plus_btn = ctk.CTkButton(
            btn_frame,
            text="+",
            width=32,
            height=32,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            corner_radius=6,
            command=increment
        )
        plus_btn.pack(side="left")
        
        setattr(self, attr_name, entry)
    
    # =========================================================================
    # MAIN AREA
    # =========================================================================
    
    def _create_main_area(self):
        """Create the main content area."""
        self.main_frame = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=COLORS["bg_dark"]
        )
        self.main_frame.grid(row=0, column=1, sticky="nswe", padx=0, pady=0)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)
        
        # Header
        self._create_header()
        
        # Code input section
        self._create_code_input()
        
        # Results section
        self._create_results_area()
        
        # Footer
        self._create_footer()
    
    def _create_header(self):
        """Create the header with title and description."""
        header_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(25, 15))
        
        # Title row
        title_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_row.pack(fill="x")
        
        title_icon = ctk.CTkLabel(
            title_row,
            text="🔍",
            font=ctk.CTkFont(size=32)
        )
        title_icon.pack(side="left")
        
        title_text = ctk.CTkLabel(
            title_row,
            text="Local Code Review & Fix Agent",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title_text.pack(side="left", padx=(12, 0))
        
        # Status badge
        self.status_badge = StatusBadge(title_row)
        self.status_badge.pack(side="right", padx=(0, 10))
        
        # Subtitle
        subtitle = ctk.CTkLabel(
            header_frame,
            text="Privacy-first Python code review, powered by local LLMs",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"]
        )
        subtitle.pack(anchor="w", pady=(8, 0))
    
    def _create_code_input(self):
        """Create the code input section."""
        input_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        input_frame.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 15))
        input_frame.grid_columnconfigure(0, weight=1)
        
        # Input header with file upload
        input_header = ctk.CTkFrame(input_frame, fg_color="transparent")
        input_header.pack(fill="x", padx=20, pady=(15, 10))
        
        input_label = ctk.CTkLabel(
            input_header,
            text="📝 Code Input",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        input_label.pack(side="left")
        
        # File upload button
        upload_btn = ctk.CTkButton(
            input_header,
            text="📂 Upload File",
            width=120,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=6,
            command=self._upload_file
        )
        upload_btn.pack(side="right")
        
        # Code text area
        self.code_input = ctk.CTkTextbox(
            input_frame,
            height=280,
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            text_color=COLORS["text_primary"],
            scrollbar_button_color=COLORS["bg_secondary"],
            scrollbar_button_hover_color=COLORS["border"]
        )
        self.code_input.pack(fill="x", padx=20, pady=(0, 15))
        
        # Placeholder text
        placeholder = '''# Enter your Python code here
# Example:
def greet(name):
    print(f"Hello, {name}!")

greet("World")'''
        self.code_input.insert("0.0", placeholder)
        
        # Action buttons row
        buttons_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        # Review & Fix button
        self.review_btn = ctk.CTkButton(
            buttons_frame,
            text="🔍  Review & Fix",
            width=160,
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent_cyan"],
            hover_color="#4A90D9",
            corner_radius=8,
            command=self._start_review
        )
        self.review_btn.pack(side="left", padx=(0, 10))
        
        # Execute Only button
        self.execute_btn = ctk.CTkButton(
            buttons_frame,
            text="🚀  Execute Only",
            width=140,
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=8,
            command=self._execute_only
        )
        self.execute_btn.pack(side="left")
        
        # Loading indicator
        self.loading_frame = ctk.CTkFrame(buttons_frame, fg_color="transparent")
        self.loading_frame.pack(side="left", padx=(20, 0))
        
        self.loading_spinner = LoadingSpinner(self.loading_frame)
        self.loading_spinner.pack(side="left")
        
        self.loading_label = ctk.CTkLabel(
            self.loading_frame,
            text="Processing...",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"]
        )
        self.loading_label.pack(side="left", padx=(10, 0))
        
        # Hide loading initially
        self.loading_frame.pack_forget()
    
    def _create_results_area(self):
        """Create the results tabview."""
        results_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        results_frame.grid(row=2, column=0, sticky="nsew", padx=30, pady=(0, 15))
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)
        
        # TabView
        self.tabview = ctk.CTkTabview(
            results_frame,
            fg_color="transparent",
            segmented_button_fg_color=COLORS["bg_tertiary"],
            segmented_button_selected_color=COLORS["accent_cyan"],
            segmented_button_selected_hover_color="#4A90D9",
            segmented_button_unselected_color=COLORS["bg_tertiary"],
            segmented_button_unselected_hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=8
        )
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        
        # Create tabs
        self.review_tab = self.tabview.add("📋 Review")
        self.fixed_tab = self.tabview.add("🔧 Fixed Code")
        self.exec_tab = self.tabview.add("🚀 Execution")
        self.diff_tab = self.tabview.add("📊 Diff View")
        
        # Configure tab grids
        for tab in [self.review_tab, self.fixed_tab, self.exec_tab, self.diff_tab]:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
        
        # Create tab contents
        self._create_review_tab()
        self._create_fixed_tab()
        self._create_exec_tab()
        self._create_diff_tab()
    
    def _create_review_tab(self):
        """Create the Review tab content."""
        scroll = ctk.CTkScrollableFrame(
            self.review_tab,
            fg_color="transparent",
            scrollbar_button_color=COLORS["bg_tertiary"]
        )
        scroll.grid(row=0, column=0, sticky="nsew")
        
        self.review_content = ctk.CTkLabel(
            scroll,
            text="No review yet. Enter code and click 'Review & Fix' to start.",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
            wraplength=800,
            justify="left",
            anchor="nw"
        )
        self.review_content.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _create_fixed_tab(self):
        """Create the Fixed Code tab content."""
        self.fixed_code_text = ctk.CTkTextbox(
            self.fixed_tab,
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            text_color=COLORS["text_primary"],
            state="disabled"
        )
        self.fixed_code_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    
    def _create_exec_tab(self):
        """Create the Execution tab content."""
        scroll = ctk.CTkScrollableFrame(
            self.exec_tab,
            fg_color="transparent",
            scrollbar_button_color=COLORS["bg_tertiary"]
        )
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        
        # Execution result section
        self.exec_result_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.exec_result_frame.pack(fill="x", padx=10, pady=10)
        
        self.exec_status_label = ctk.CTkLabel(
            self.exec_result_frame,
            text="No execution yet.",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.exec_status_label.pack(fill="x")
        
        # Output area
        output_label = ctk.CTkLabel(
            self.exec_result_frame,
            text="Output:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        output_label.pack(fill="x", pady=(15, 5))
        
        self.exec_output_text = ctk.CTkTextbox(
            self.exec_result_frame,
            height=150,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=6,
            text_color=COLORS["text_primary"],
            state="disabled"
        )
        self.exec_output_text.pack(fill="x")
        
        # Attempt info
        self.attempt_label = ctk.CTkLabel(
            self.exec_result_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.attempt_label.pack(fill="x", pady=(15, 5))
        
        # Error history section
        self.error_history_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.error_history_frame.pack(fill="x", padx=10, pady=(0, 10))
    
    def _create_diff_tab(self):
        """Create the Diff View tab content."""
        self.diff_text = ctk.CTkTextbox(
            self.diff_tab,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            text_color=COLORS["text_primary"],
            state="disabled"
        )
        self.diff_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    
    def _create_footer(self):
        """Create the footer."""
        footer = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent",
            height=40
        )
        footer.grid(row=3, column=0, sticky="ew", padx=30, pady=(0, 15))
        
        footer_text = ctk.CTkLabel(
            footer,
            text="🔒 All processing happens locally. Your code never leaves your machine. Powered by Ollama and LangGraph.",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        footer_text.pack(side="left")
    
    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================
    
    def _upload_file(self):
        """Handle file upload."""
        filepath = filedialog.askopenfilename(
            title="Select Python File",
            filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
        )
        
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                self.code_input.delete("0.0", "end")
                self.code_input.insert("0.0", content)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read file: {str(e)}")
    
    def _apply_settings(self):
        """Apply settings from the sidebar."""
        try:
            update_config(
                model_name=self.model_entry.get(),
                ollama_base_url=self.url_entry.get(),
                temperature=self.temp_slider.get(),
                max_retries=int(self.retries_spinbox.get()),
                execution_timeout=int(self.timeout_spinbox.get())
            )
            
            # Show success feedback
            self.apply_btn.configure(text="✓ Applied!")
            self.after(1500, lambda: self.apply_btn.configure(text="Apply Settings"))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply settings: {str(e)}")
    
    def _clear_history(self):
        """Clear all history and reset state."""
        self.agent_state = None
        self.original_code = ""
        self.history = []
        
        # Reset UI
        self.status_badge.set_status("idle")
        self.review_content.configure(
            text="No review yet. Enter code and click 'Review & Fix' to start."
        )
        
        self.fixed_code_text.configure(state="normal")
        self.fixed_code_text.delete("0.0", "end")
        self.fixed_code_text.configure(state="disabled")
        
        self.exec_status_label.configure(text="No execution yet.")
        self.exec_output_text.configure(state="normal")
        self.exec_output_text.delete("0.0", "end")
        self.exec_output_text.configure(state="disabled")
        self.attempt_label.configure(text="")
        
        # Clear error history
        for widget in self.error_history_frame.winfo_children():
            widget.destroy()
        
        self.diff_text.configure(state="normal")
        self.diff_text.delete("0.0", "end")
        self.diff_text.configure(state="disabled")
        
        # Show confirmation
        self.clear_btn.configure(text="✓ Cleared!")
        self.after(1500, lambda: self.clear_btn.configure(text="Clear History"))
    
    def _start_review(self):
        """Start the code review process."""
        code = self.code_input.get("0.0", "end").strip()
        
        if not code:
            messagebox.showwarning("Warning", "Please enter some code to review.")
            return
        
        if self.is_processing:
            return
        
        # Format code and save original
        code = format_code(code)
        self.original_code = code
        
        # Start processing
        self._set_processing(True, "Reviewing code...")
        
        # Run in background thread
        thread = threading.Thread(target=self._run_agent_thread, args=(code,))
        thread.daemon = True
        thread.start()
    
    def _execute_only(self):
        """Execute code without review."""
        code = self.code_input.get("0.0", "end").strip()
        
        if not code:
            messagebox.showwarning("Warning", "Please enter some code to execute.")
            return
        
        if self.is_processing:
            return
        
        code = format_code(code)
        self._set_processing(True, "Executing code...")
        
        # Run in background thread
        thread = threading.Thread(target=self._execute_only_thread, args=(code,))
        thread.daemon = True
        thread.start()
    
    def _set_processing(self, processing: bool, message: str = "Processing..."):
        """Update UI processing state."""
        self.is_processing = processing
        
        if processing:
            self.review_btn.configure(state="disabled")
            self.execute_btn.configure(state="disabled")
            self.loading_label.configure(text=message)
            self.loading_frame.pack(side="left", padx=(20, 0))
            self.loading_spinner.start()
            self.status_badge.set_status("reviewing")
        else:
            self.review_btn.configure(state="normal")
            self.execute_btn.configure(state="normal")
            self.loading_frame.pack_forget()
            self.loading_spinner.stop()
    
    # =========================================================================
    # BACKGROUND THREAD METHODS
    # =========================================================================
    
    def _run_agent_thread(self, code: str):
        """Run the agent in a background thread."""
        try:
            # Update status
            self.after(0, lambda: self.status_badge.set_status("reviewing"))
            self.after(0, lambda: self.loading_label.configure(text="Reviewing code..."))
            
            # Run the agent
            final_state = run_agent(code)
            
            # Store result
            self.agent_state = final_state
            
            # Add to history
            self.history.append({
                "timestamp": get_timestamp(),
                "original_code": code,
                "final_state": final_state,
            })
            
            # Update UI on main thread
            self.after(0, lambda: self._update_results(final_state))
            
        except Exception as e:
            error_msg = str(e)
            
            # Check for Ollama connection errors
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                error_msg = (
                    "Could not connect to Ollama.\n\n"
                    "Please ensure:\n"
                    "• Ollama is installed and running\n"
                    "• The model is available (try: ollama pull qwen3:14b)\n"
                    "• The URL is correct in settings\n\n"
                    f"Technical error: {error_msg}"
                )
            
            self.after(0, lambda: self._show_error(error_msg))
        
        finally:
            self.after(0, lambda: self._set_processing(False))
    
    def _execute_only_thread(self, code: str):
        """Execute code in a background thread."""
        try:
            self.after(0, lambda: self.status_badge.set_status("executing"))
            
            result = execute_code_safely(code)
            
            # Update UI on main thread
            self.after(0, lambda: self._update_execution_only(result))
            
        except Exception as e:
            self.after(0, lambda: self._show_error(str(e)))
        
        finally:
            self.after(0, lambda: self._set_processing(False))
    
    # =========================================================================
    # UI UPDATE METHODS
    # =========================================================================
    
    def _update_results(self, state: AgentState):
        """Update all result tabs with agent state."""
        status = state.get("status", "unknown")
        self.status_badge.set_status(status)
        
        # Update Review tab
        self._update_review_tab(state)
        
        # Update Fixed Code tab
        self._update_fixed_code_tab(state)
        
        # Update Execution tab
        self._update_execution_tab(state)
        
        # Update Diff tab
        self._update_diff_tab(state)
    
    def _update_review_tab(self, state: AgentState):
        """Update the Review tab content."""
        review = state.get("review")
        
        if not review:
            self.review_content.configure(text="No review available.")
            return
        
        # Build review text
        lines = []
        
        # Summary
        if review.summary:
            lines.append(f"📝 Summary\n{review.summary}\n")
        
        # Severity
        severity_icons = {"low": "🟢", "medium": "🟡", "high": "🔴"}
        icon = severity_icons.get(review.severity, "⚪")
        lines.append(f"⚠️ Severity: {icon} {review.severity.upper()}\n")
        
        # Issues
        if review.issues:
            lines.append("🔍 Issues Found:")
            for i, issue in enumerate(review.issues, 1):
                lines.append(f"  {i}. {issue}")
            lines.append("")
        
        # Suggestions
        if review.suggestions:
            lines.append("💡 Suggestions:")
            for i, suggestion in enumerate(review.suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
        
        self.review_content.configure(text="\n".join(lines))
    
    def _update_fixed_code_tab(self, state: AgentState):
        """Update the Fixed Code tab content."""
        fixed = state.get("fixed_code")
        current_code = state.get("current_code", "")
        
        self.fixed_code_text.configure(state="normal")
        self.fixed_code_text.delete("0.0", "end")
        
        if fixed:
            # Show explanation
            text = ""
            if fixed.explanation:
                text += f"# Explanation: {fixed.explanation}\n"
            if fixed.changes_made:
                text += "# Changes made:\n"
                for change in fixed.changes_made:
                    text += f"#   • {change}\n"
            text += "\n"
            text += fixed.code
            
            self.fixed_code_text.insert("0.0", text)
        elif current_code:
            self.fixed_code_text.insert("0.0", current_code)
        else:
            self.fixed_code_text.insert("0.0", "No fixed code available.")
        
        self.fixed_code_text.configure(state="disabled")
    
    def _update_execution_tab(self, state: AgentState):
        """Update the Execution tab content."""
        result = state.get("execution_result")
        attempt = state.get("attempt", 0)
        config = get_config()
        error_history = state.get("error_history", [])
        
        if result:
            if result.success:
                self.exec_status_label.configure(
                    text="✅ Code executed successfully!",
                    text_color=COLORS["accent_green"]
                )
            else:
                self.exec_status_label.configure(
                    text="❌ Execution failed",
                    text_color=COLORS["accent_red"]
                )
            
            # Update output
            self.exec_output_text.configure(state="normal")
            self.exec_output_text.delete("0.0", "end")
            
            output_text = ""
            if result.output:
                output_text = result.output
            elif result.error:
                output_text = f"Error: {result.error}"
            else:
                output_text = "(no output)"
            
            output_text += f"\n\n⏱️ Execution time: {result.execution_time:.3f}s"
            self.exec_output_text.insert("0.0", output_text)
            self.exec_output_text.configure(state="disabled")
        
        # Update attempt info
        if attempt > 0:
            self.attempt_label.configure(
                text=f"🔄 Completed after {attempt} attempt(s) (max: {config.max_retries})"
            )
        
        # Update error history
        for widget in self.error_history_frame.winfo_children():
            widget.destroy()
        
        if error_history:
            history_label = ctk.CTkLabel(
                self.error_history_frame,
                text="📜 Error History:",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["text_primary"],
                anchor="w"
            )
            history_label.pack(fill="x", pady=(10, 5))
            
            for i, error in enumerate(error_history, 1):
                error_label = ctk.CTkLabel(
                    self.error_history_frame,
                    text=f"Attempt {i}: {error[:150]}{'...' if len(error) > 150 else ''}",
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS["text_secondary"],
                    anchor="w",
                    wraplength=700
                )
                error_label.pack(fill="x", pady=2)
    
    def _update_diff_tab(self, state: AgentState):
        """Update the Diff tab with code comparison."""
        original = self.original_code
        current = state.get("current_code", "")
        
        self.diff_text.configure(state="normal")
        self.diff_text.delete("0.0", "end")
        
        if not original or not current:
            self.diff_text.insert("0.0", "No diff available. Both original and fixed code are needed.")
            self.diff_text.configure(state="disabled")
            return
        
        # Generate diff
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            current.splitlines(keepends=True),
            fromfile="Original",
            tofile="Fixed",
            lineterm=""
        )
        
        diff_text = "".join(diff)
        
        if diff_text:
            self.diff_text.insert("0.0", diff_text)
        else:
            self.diff_text.insert("0.0", "No changes detected between original and fixed code.")
        
        self.diff_text.configure(state="disabled")
    
    def _update_execution_only(self, result):
        """Update UI after execute-only operation."""
        if result.success:
            self.status_badge.set_status("success")
            self.exec_status_label.configure(
                text="✅ Code executed successfully!",
                text_color=COLORS["accent_green"]
            )
        else:
            self.status_badge.set_status("failed")
            self.exec_status_label.configure(
                text="❌ Execution failed",
                text_color=COLORS["accent_red"]
            )
        
        # Update output
        self.exec_output_text.configure(state="normal")
        self.exec_output_text.delete("0.0", "end")
        
        output_text = ""
        if result.output:
            output_text = result.output
        elif result.error:
            output_text = f"Error: {result.error}"
        else:
            output_text = "(no output)"
        
        output_text += f"\n\n⏱️ Execution time: {result.execution_time:.3f}s"
        self.exec_output_text.insert("0.0", output_text)
        self.exec_output_text.configure(state="disabled")
        
        # Switch to Execution tab
        self.tabview.set("🚀 Execution")
    
    def _show_error(self, error_message: str):
        """Display an error message to the user."""
        self.status_badge.set_status("failed")
        messagebox.showerror("Error", error_message)


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

def main():
    """
    Main entry point for the application.
    
    Checks for Ollama availability before launching the UI.
    Shows a user-friendly error dialog if Ollama is not running.
    """
    # Check if Ollama is running
    is_running, error_msg = check_ollama_running()
    
    if not is_running:
        # Show error dialog and exit
        show_ollama_error_dialog()
        return
    
    # Ollama is running, launch the main application
    app = CodeReviewApp()
    app.mainloop()


if __name__ == "__main__":
    main()
