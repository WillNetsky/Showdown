# gui/dialogs.py
import tkinter as tk
from tkinter import ttk, messagebox # messagebox is used in _on_confirm
import os
import glob
import json

# TEAMS_DIR is used in _populate_team_list.
# You'll need to import it from where it's defined (likely tournament.py)
# Assuming tournament.py is in the parent directory of 'gui'
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Add parent dir to sys.path
try:
    from tournament import TEAMS_DIR
except ImportError:
    # Fallback or error if TEAMS_DIR cannot be found.
    # For a robust solution, TEAMS_DIR should ideally come from a central config/constants accessible project-wide.
    # For now, this relative import assumes a specific structure.
    # If tournament.py is at the same level as main.py, this should work.
    print("ERROR in dialogs.py: Could not import TEAMS_DIR from tournament.py. Path issues may exist.")
    TEAMS_DIR = "teams" # Fallback, but not ideal


class TeamSelectionDialog(tk.Toplevel):
    def __init__(self, parent, teams_needed_or_allowed, dialog_title="Select Teams"):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title(dialog_title)
        self.parent = parent
        self.teams_needed_or_allowed = teams_needed_or_allowed
        self.selected_team_filepaths = None

        self.geometry("550x450")

        list_frame = ttk.Frame(self)
        list_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        instruction_text = f"Select up to {self.teams_needed_or_allowed} teams."
        if "Benchmark" in dialog_title:
            instruction_text += "\nSelected teams will be used as benchmarks. Remaining slots (if any, up to 'Num Benchmark Teams') will be filled by randomly generated teams."
        elif "Tournament" in dialog_title:
            instruction_text += "\nRemaining slots for the tournament will be auto-generated if fewer are selected."

        ttk.Label(list_frame, text=instruction_text, wraplength=500, justify=tk.LEFT).pack(pady=(0, 5))

        self.listbox_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.team_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, yscrollcommand=self.listbox_scrollbar.set,
                                       exportselection=False)
        self.listbox_scrollbar.config(command=self.team_listbox.yview)
        self.listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.team_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.available_teams_data = []
        self._populate_team_list()

        button_frame = ttk.Frame(self)
        button_frame.pack(padx=10, pady=(0, 10), fill=tk.X)
        self.confirm_button = ttk.Button(button_frame, text="Confirm Selections", command=self._on_confirm)
        self.confirm_button.pack(side=tk.LEFT, padx=5, expand=True)
        self.select_all_button = ttk.Button(button_frame, text="Select All Visible", command=self._select_all_visible)
        self.select_all_button.pack(side=tk.LEFT, padx=5, expand=True)
        self.deselect_all_button = ttk.Button(button_frame, text="Deselect All", command=self._deselect_all)
        self.deselect_all_button.pack(side=tk.LEFT, padx=5, expand=True)
        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        self.cancel_button.pack(side=tk.LEFT, padx=5, expand=True)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window(self)

    def _populate_team_list(self):
        self.team_listbox.delete(0, tk.END)
        self.available_teams_data = []  # This will store (display_string, filepath) in sorted order

        temporary_team_info_list = []  # To store (elo, display_name_base, filepath) for sorting

        if not TEAMS_DIR or not os.path.exists(TEAMS_DIR) or not os.path.isdir(TEAMS_DIR):
            self.team_listbox.insert(tk.END, f"Teams directory '{TEAMS_DIR or 'Not Defined'}' not found.")
            return

        search_pattern = os.path.join(TEAMS_DIR, '**', '*.json')
        team_files = glob.glob(search_pattern, recursive=True)  # Already sorted by path initially

        if not team_files:
            self.team_listbox.insert(tk.END,
                                     f"No saved teams (.json files) found in '{TEAMS_DIR}' or its subdirectories.")
            return

        for filepath in team_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                team_name_from_json = data.get("name", os.path.splitext(os.path.basename(filepath))[0])

                elo = 1500.0  # Default ELO
                if "team_stats_data" in data and data["team_stats_data"] is not None:
                    elo = data["team_stats_data"].get("elo_rating", 1500.0)

                # Prepare display name base (without ELO part yet)
                relative_path = os.path.relpath(filepath, TEAMS_DIR)
                display_name_base = ""
                if relative_path != os.path.basename(filepath) and os.path.dirname(relative_path) != '.':
                    display_name_base = f"({os.path.dirname(relative_path)}) {team_name_from_json}"
                else:
                    display_name_base = team_name_from_json

                temporary_team_info_list.append({
                    "elo": elo,
                    "display_base": display_name_base,
                    "filepath": filepath
                })

            except json.JSONDecodeError:
                log_msg = f"Error decoding JSON from file: {filepath} in dialog."
                if hasattr(self.parent, 'log_message') and callable(self.parent.log_message):
                    self.parent.log_message(log_msg)
                else:
                    print(log_msg)
                # Still add a placeholder to the listbox for problematic files if desired, or skip
                # For now, let's skip adding it to the sortable list, but you could add an error entry directly to listbox
            except Exception as e:
                log_msg = f"Error reading team file {filepath} for dialog: {e}"
                if hasattr(self.parent, 'log_message') and callable(self.parent.log_message):
                    self.parent.log_message(log_msg)
                else:
                    print(log_msg)

        # Sort the temporary list by ELO (descending, so higher ELO is first)
        temporary_team_info_list.sort(key=lambda x: x["elo"], reverse=True)

        # Now populate the listbox and self.available_teams_data in the sorted order
        if not temporary_team_info_list and not team_files:  # If glob found files but all failed parsing
            self.team_listbox.insert(tk.END, "No valid team files found or all failed to load.")

        for team_info in temporary_team_info_list:
            display_string = f"{team_info['display_base']} (ELO: {team_info['elo']:.0f})"
            self.available_teams_data.append(
                (display_string, team_info['filepath']))  # For mapping selection back to filepath
            self.team_listbox.insert(tk.END, display_string)

    def _select_all_visible(self):
        self.team_listbox.select_set(0, tk.END)

    def _deselect_all(self):
        self.team_listbox.selection_clear(0, tk.END)

    def _on_confirm(self):
        selected_indices = self.team_listbox.curselection()
        if len(selected_indices) > self.teams_needed_or_allowed:
            messagebox.showwarning("Too Many Teams", f"Select no more than {self.teams_needed_or_allowed} teams.",
                                   parent=self)
            return
        self.selected_team_filepaths = [self.available_teams_data[i][1] for i in selected_indices]
        self.destroy()

    def _on_cancel(self):
        self.selected_team_filepaths = None
        self.destroy()