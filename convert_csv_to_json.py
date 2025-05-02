import csv
import json
import os

def convert_player_csvs_to_json(batters_filepath, pitchers_filepath, output_filepath):
    """
    reads player data from separate batters and pitchers CSVs,
    combines them into a single list of dictionaries with a 'type' field,
    and saves the list to a JSON file.

    Args:
        batters_filepath (str): Path to the batters CSV file.
        pitchers_filepath (str): Path to the pitchers CSV file.
        output_filepath (str): Path where the combined JSON file will be saved.
    """
    all_players_data = []

    # --- Read Batters CSV ---
    try:
        with open(batters_filepath, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                # Add a 'type' field and lowercase keys for consistency
                player_data = {k.lower(): v.strip() for k, v in row.items()}
                player_data['type'] = 'batter'
                all_players_data.append(player_data)
        print(f"Successfully read batters from {batters_filepath}")
    except FileNotFoundError:
        print(f"Error: Batters file not found at {batters_filepath}")
        return
    except Exception as e:
        print(f"Error reading batters CSV {batters_filepath}: {e}")
        return

    # --- Read Pitchers CSV ---
    try:
        with open(pitchers_filepath, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                # Add a 'type' field and lowercase keys for consistency
                player_data = {k.lower(): v.strip() for k, v in row.items()}
                player_data['type'] = 'pitcher'
                all_players_data.append(player_data)
        print(f"Successfully read pitchers from {pitchers_filepath}")
    except FileNotFoundError:
        print(f"Error: Pitchers file not found at {pitchers_filepath}")
        return
    except Exception as e:
        print(f"Error reading pitchers CSV {pitchers_filepath}: {e}")
        return

    # --- Save to JSON ---
    try:
        with open(output_filepath, mode='w', encoding='utf-8') as outfile:
            # Use json.dump to write the list of dictionaries to the file
            # indent=4 makes the JSON file human-readable
            json.dump(all_players_data, outfile, indent=4)
        print(f"Successfully saved combined player data to {output_filepath}")
    except Exception as e:
        print(f"Error saving JSON file {output_filepath}: {e}")


if __name__ == "__main__":
    # Define file paths
    data_dir = os.path.dirname(os.path.abspath(__file__))
    batters_csv = os.path.join(data_dir, 'all_batters.csv')
    pitchers_csv = os.path.join(data_dir, 'all_pitchers.csv')
    output_json = os.path.join(data_dir, 'all_players.json')

    # Run the conversion
    convert_player_csvs_to_json(batters_csv, pitchers_csv, output_json)
