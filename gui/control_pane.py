# gui/control_pane.py
import tkinter as tk
from tkinter import ttk, scrolledtext
import time  # For timestamping logs


class ControlPane(ttk.Frame):
    def __init__(self, parent, app_controller):
        """
        Initializes the Control Pane which includes Tournament Controls and Simulation Log.

        Args:
            parent (tk.Widget): The parent widget (typically self.left_pane_frame from BaseballApp).
            app_controller (BaseballApp): The main application controller instance.
        """
        super().__init__(parent)
        self.app_controller = app_controller

        # This frame will fill its parent (the left_pane_frame from BaseballApp)
        self.pack(fill=tk.BOTH, expand=True)

        self._setup_widgets()

    def _setup_widgets(self):
        # --- Tournament Controls ---
        controls_frame = ttk.LabelFrame(self, text="Tournament Controls")
        # Pack this frame into self (which is the ControlPane frame)
        controls_frame.pack(padx=10, pady=(0, 10), fill="x", side=tk.TOP)

        ttk.Label(controls_frame, text="Number of Teams:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        # Use the num_teams_var from the app_controller
        self.num_teams_entry = ttk.Entry(controls_frame, textvariable=self.app_controller.num_teams_var, width=5)
        self.num_teams_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.init_button = ttk.Button(controls_frame, text="Initialize/Load Teams",
                                      command=self.app_controller.initialize_tournament_threaded)
        self.init_button.grid(row=1, column=0, columnspan=2, padx=5, pady=(5, 2), sticky="ew")

        self.run_season_button = ttk.Button(controls_frame, text="Run Season",
                                            command=self.app_controller.run_season_threaded)
        self.run_season_button.grid(row=2, column=0, columnspan=2, padx=5, pady=2, sticky="ew")

        self.run_postseason_button = ttk.Button(controls_frame, text="Run Postseason & Prepare Next",
                                                command=self.app_controller.run_postseason_and_prepare_threaded)
        self.run_postseason_button.grid(row=3, column=0, columnspan=2, padx=5, pady=2, sticky="ew")

        self.clear_tournament_button = ttk.Button(controls_frame, text="Clear Tournament Data",
                                                  command=self.app_controller.prompt_clear_tournament_data)
        self.clear_tournament_button.grid(row=4, column=0, columnspan=2, padx=5, pady=(10, 2), sticky="ew")

        # --- Simulation Log ---
        log_frame = ttk.LabelFrame(self, text="Simulation Log")
        # Pack this frame into self (the ControlPane frame)
        log_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True, side=tk.BOTTOM)

        self.log_text_widget = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD, relief=tk.SOLID,
                                                         borderwidth=1)
        self.log_text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text_widget.config(state=tk.DISABLED)

    def log_to_widget(self, message):
        """Appends a timestamped message to the log widget."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text_widget.config(state=tk.NORMAL)
        self.log_text_widget.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text_widget.see(tk.END)  # Scroll to the end
        self.log_text_widget.config(state=tk.DISABLED)

    def update_control_buttons_state(self, app_state, players_loaded, teams_exist, ga_is_running):
        """
        Updates the state of the tournament control buttons based on application state.
        This method will be called by the main app_controller.
        """
        # Clear tournament button
        can_clear = players_loaded and not ga_is_running and \
                    app_state not in ["LOADING_PLAYERS", "INITIALIZING_TOURNAMENT",
                                      "SEASON_IN_PROGRESS", "POSTSEASON_IN_PROGRESS", "GA_RUNNING"]
        self.clear_tournament_button.config(state=tk.NORMAL if can_clear else tk.DISABLED)

        # Other tournament buttons
        if ga_is_running or app_state == "GA_RUNNING":
            for btn in [self.init_button, self.run_season_button, self.run_postseason_button]:
                btn.config(state=tk.DISABLED)
        elif app_state in ["LOADING_PLAYERS", "INITIALIZING_TOURNAMENT",
                           "SEASON_IN_PROGRESS", "POSTSEASON_IN_PROGRESS"]:
            for btn in [self.init_button, self.run_season_button, self.run_postseason_button]:
                btn.config(state=tk.DISABLED)
        elif app_state == "IDLE":
            self.init_button.config(state=tk.NORMAL if players_loaded else tk.DISABLED)
            self.run_season_button.config(state=tk.NORMAL if teams_exist else tk.DISABLED)
            self.run_postseason_button.config(state=tk.DISABLED)
        elif app_state == "SEASON_CONCLUDED":
            self.init_button.config(state=tk.DISABLED)
            self.run_season_button.config(state=tk.DISABLED)
            self.run_postseason_button.config(state=tk.NORMAL if teams_exist else tk.DISABLED)
        else:  # Default to disabled if state is unknown
            for btn in [self.init_button, self.run_season_button, self.run_postseason_button]:
                btn.config(state=tk.DISABLED)