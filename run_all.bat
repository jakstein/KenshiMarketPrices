@echo off
python extract_game_data.py
python translate_item_ids.py
python json_to_csv_converter.py
echo All scripts executed.
pause
