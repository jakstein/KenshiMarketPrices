# Kenshi Market Prices Analyzer

## Overview

This project is a tool for a game Kenshi, to read save files and extract the current market markups for the given save. It also then translates the item IDs into a human readable version using game files. After this it converts the JSON files into CSV for easy viewing.

[![image.png](https://i.postimg.cc/zDxqXvKB/image.png)](https://postimg.cc/SjYBgyZF)

## Features

*   Extracts item price markups from Kenshi game save files.
*   Identifies item prices specific to different cities within the game.
*   Translates item IDs into understandable names using Kenshi's game data files.
*   Converts the extracted and translated data into a CSV format.
*   Filters data to remove potential false positives and outliers.
*   Attempts to automatically locate Kenshi installation and save location for necessary game files.

## Workflow

The project follows a three-step process, orchestrated by the `run_all.bat` script:

1.  **`extract_game_data.py`**:
    *   Scans a Kenshi save file (default: `quick.save`) located in a `save/` subdirectory (you may need to create that folder yourself).
    *   If a local save file is not found, looks for latest Kenshi save file (e.g., `quick.save`) in APPDATA directories.
    *   It looks for predefined city names and then searches for item patterns within the vicinity of those city mentions.
    *   Filters extracted markups based on a configurable percentage range (default: 1% to 175%).
    *   Applies a frequency filter, removing items that appear in less than 10% of cities with data.
    *   Outputs the raw extracted data (with item IDs) to `extracted_game_markups.json`.

2.  **`translate_item_ids.py`**:
    *   Takes `extracted_game_markups.json` as input.
    *   Collects all unique item IDs from this file.
    *   Searches for Kenshi's `.mod` and `.base` files, which act as dictionaries to translate item IDs (e.g., "1234-some_item_name.base") to human-readable names.
    *   It first looks in a local `datafiles/` directory. If empty or not found, it attempts to automatically find the Kenshi game installation path (Steam version) to locate these dictionary files.
    *   Outputs the translated data to `translated_game_markups.json`.

3.  **`json_to_csv_converter.py`**:
    *   Reads `translated_game_markups.json`.
    *   Converts the JSON data into a CSV file named `game_markups_spreadsheet.csv`.
    *   The CSV can be configured to have cities as columns and items as rows, or vice-versa. (via the `citiesHorizontal` variable, default is `True`).

## Prerequisites

*   **Python 3.x**: The scripts are written in Python.
*   **Kenshi Game Installation**: Required for the `.mod` and `.base` files used by `translate_item_ids.py` to map item IDs to names. The script attempts to find this automatically, but placing these files in the `datafiles/` directory is a more reliable alternative (if you know what files exactly to use).
*   **Kenshi Save File**: The `extract_game_data.py` script needs a Kenshi game file to process. It defaults to looking for `quicksave.save` in a `save/` subdirectory, then `zone.dat` or `platoon.dat` files. Alternatively it'll scan your APPDATA directories for the latest save file if none is found in the `save/` directory.

## Setup

1.  **Clone or download the project.**
2.  **Ensure Python 3.x is installed** and added to your system's PATH.
3.  **(Optional) Kenshi Data Files**:
    *   Create a directory named `datafiles` in the project root.
    *   Copy Kenshi's `.mod` and `.base` files into this `datafiles/` directory. These are typically found in your Kenshi installation folder (e.g., `SteamLibrary\steamapps\common\Kenshi\data` and `SteamLibrary\steamapps\common\Kenshi\mods`).
    *   Alternatively, the script `translate_item_ids.py` will attempt to locate your Kenshi installation path automatically if the `datafiles/` directory is empty or missing.
4.  **(Optional) Kenshi Save File**:
    *   Create a directory named `save` in the project root.
    *   Place your Kenshi save file (e.g., `quick.save`) or other relevant game data files into this `save/` directory. The script `extract_game_data.py` will look here first.
    *   If no save file is found in the `save/` directory, the script will search your APPDATA directories for the latest save file.

## How to Run

1.  **Configure Scripts (Optional)**:
    *   `extract_game_data.py`:
        *   You can modify the `cityNames` list if needed.
        *   Adjust `markupLowerBoundConfig` and `markupUpperBoundConfig` for price filtering.
    *   `translate_item_ids.py`:
        *   `MARKUPS_JSON_FILE`: Input JSON file (default: `extracted_game_markups.json`).
        *   `DATAFILES_DIR`: Local directory for dictionary files (default: `datafiles`).
        *   `OUTPUT_TRANSLATED_JSON_FILE`: Output JSON file (default: `translated_game_markups.json`).
    *   `json_to_csv_converter.py`:
        *   `inputJsonFile`: Input JSON file (default: `translated_game_markups.json`).
        *   `outputCsvFile`: Output CSV file (default: `game_markups_spreadsheet.csv`).
        *   `citiesHorizontal`: Set to `True` for items as columns and cities as rows, `False` for the opposite (default: `True`).

2.  **Execute the Batch File**:
    *   Simply run `run_all.bat`. This will execute the three Python scripts in the correct order.
    *   The console will display progress, debug messages, and any errors encountered.

3.  **Check Outputs**:
    *   After execution, you will find `extracted_game_markups.json`, `translated_game_markups.json`, and `game_markups_spreadsheet.csv` in the project directory.
