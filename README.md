Baseball Game Simulation
This project is a simple command-line baseball game simulator written in Python. It loads player data from CSV files, creates random teams based on player points and roster requirements, and simulates a baseball game inning by inning.

Project Structure
The project consists of the following Python files:

main.py: The main script to run the simulation. It handles finding and loading player data from CSVs, creating teams, running the game, and printing the results and player stats.

game_logic.py: Contains the core game simulation logic, including functions for rolling dice, determining at-bat results, handling baserunners, playing innings, and managing pitching changes.

entities.py: Defines the Batter and Pitcher classes, which hold player attributes and statistics.

team.py: Defines the Team class, which manages a team's roster (starters, bench, pitchers) and provides methods for getting the next batter or available pitchers.

constants.py: Stores various constants used throughout the project, such as position mappings and team point limits.

Setup and Running
Save the files: Ensure you have all the Python files (main.py, game_logic.py, entities.py, team.py, constants.py) saved in the same directory.

Add CSV files: Place your player data CSV files (all_batters.csv and all_pitchers.csv) in the same directory as the Python scripts.

Run the simulation: Open a terminal or command prompt, navigate to the project directory, and run the main.py script using a Python interpreter:

python main.py

The simulation will run, and the game log, final score, and player statistics will be printed to the console.

CSV File Format
The simulation expects player data in CSV files with specific columns. Based on the files used in development (all_batters.csv and all_pitchers.csv), the expected columns include:

Name: Player's name.

year: (Present in all_batters.csv, not currently used in simulation logic)

cardN: (Present in all_batters.csv, not currently used in simulation logic)

teal: (Present in all_batters.csv, not currently used in simulation logic)

onbase: Batter's On-Base number (used for determining pitch quality).

so: Strikeout range value.

fo (or FB): Flyball range value.

bb (or BB): Walk range value.

bi (or 1B): Single range value.

bip (or 1BP): Single with runner advance range value.

b2 (or 2B): Double range value.

b3 (or 3B): Triple range value.

han: (Present in all_batters.csv, not currently used in simulation logic)

hr (or HR): Home Run range value.

pts: Player's points value (used for team construction).

ip (or IP Limit): Pitcher's Innings Pitched limit.

hand: Pitcher's throwing hand (not currently used in simulation logic).

fld1, pos2, fld2, pos3, fld3, pos4, fld4: Fielding position and rating columns (position is used for roster construction, fielding rating is not currently used).

pos (or Position): Player's primary position (e.g., "Starter", "Reliever", "Closer" for pitchers, standard baseball positions for batters).

control: Pitcher's Control range value.

pu: Pitcher's PU range value.

Type: (Optional) Can be used to explicitly specify 'B' for Batter or 'P' for Pitcher if type inference is unreliable.

The load_players_from_csv function has some flexibility to handle variations in column casing and can infer player type if the 'Type' column is missing, based on the presence of key stats like 'onbase' (for batters) or 'control' (for pitchers).

Dependencies
This project uses standard Python libraries and does not require any external packages to be installed.

random: For dice rolls and random team selection.

csv: For reading player data from CSV files.

os: For file path operations.

glob: For finding CSV files in the directory.