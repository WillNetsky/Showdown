# main.py
import tkinter as tk
import os

# Assuming BaseballApp will be moved to gui/app_controller.py
# If you name your file differently (e.g., main_app.py), adjust the import.
try:
    from gui.app_controller import BaseballApp
except ImportError as e:
    print(f"Error importing BaseballApp: {e}")
    print("Make sure BaseballApp is in a 'gui' subfolder, in a file like 'app_controller.py',")
    print("and that the 'gui' folder has an '__init__.py' file to be recognized as a package.")
    exit()

# Define paths for directories that should exist.
# These might also be defined in a central constants.py or config.py file.
# For startup checks, defining them here is fine.
# The application itself (BaseballApp and other modules) will get TEAMS_DIR
# from tournament.py as it currently does.
TEAMS_DIR_FOR_MAIN_CHECK = "teams"  # Relative to where main.py is
BENCHMARK_ARCHETYPES_DIR_FOR_MAIN_CHECK = os.path.join(TEAMS_DIR_FOR_MAIN_CHECK, "benchmark_archetypes")


def ensure_directories_exist():
    """Creates necessary directories if they don't exist."""
    dirs_to_check = [TEAMS_DIR_FOR_MAIN_CHECK, BENCHMARK_ARCHETYPES_DIR_FOR_MAIN_CHECK]
    for dir_path in dirs_to_check:
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
                print(f"Created directory: {dir_path}")
            except OSError as e:
                print(f"Error creating directory {dir_path}: {e}")
                # Depending on severity, you might want to exit or show a GUI error
        elif not os.path.isdir(dir_path):
            print(f"Error: {dir_path} exists but is not a directory.")
            # Handle error appropriately


if __name__ == "__main__":
    # Perform pre-flight checks, like ensuring necessary directories exist
    ensure_directories_exist()

    # Create the main Tkinter window
    root = tk.Tk()

    # Instantiate and run the application
    app = BaseballApp(root)

    # Start the Tkinter event loop
    root.mainloop()