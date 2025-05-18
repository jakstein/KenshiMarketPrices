import json
import csv
import os

def convertJsonToCsv(jsonFilePath, csvFilePath, citiesHorizontal=False): # this entire file is AI written based on the other files I wrote myself
    print(f"Starting JSON to CSV conversion")
    print(f"Cities horizontal: {citiesHorizontal}")
    print(f"Attempting to load JSON data from: {jsonFilePath}")
    try:
        with open(jsonFilePath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Successfully loaded JSON data.")
    except FileNotFoundError:
        print(f"Error: JSON file not found at {jsonFilePath}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {jsonFilePath}")
        return
    except Exception as e:
        print(f"Error reading {jsonFilePath}: {e}")
        return

    if not data:
        print("JSON data is empty. CSV will not be generated.")
        return

    # Collect all unique item names (row headers) and city names (column headers)
    print("Collecting city names and item names...")
    allItemNames = set()
    cityNamesOrdered = [] # Keep order of cities as they appear in JSON for consistency, or sort if preferred

    # Determine city names (column headers) - assuming first city entry has all/most items to get a good list
    # Or, iterate through all to be sure, then sort them.
    tempCityNames = list(data.keys())
    if not tempCityNames:
        print("No city data found in JSON. CSV will not be generated.")
        return
    
    # Sort city names for consistent column order
    cityNamesOrdered = sorted(tempCityNames)
    print(f"Found {len(cityNamesOrdered)} cities: {cityNamesOrdered}")

    for city, items in data.items():
        for itemName in items.keys():
            allItemNames.add(itemName)
    
    sortedItemNames = sorted(list(allItemNames))
    if not sortedItemNames:
        print("No item names found in JSON data. CSV will not be generated.")
        return
    print(f"Found {len(sortedItemNames)} unique item names.")

    print(f"Attempting to write data to CSV file: {csvFilePath}")
    try:
        with open(csvFilePath, 'w', newline='', encoding='utf-8') as csvfile:
            csvWriter = csv.writer(csvfile)

            if citiesHorizontal:
                # Items as columns, Cities as rows
                headerRow = [''] + sortedItemNames
                print(f"Writing header row (items horizontal): {headerRow}")
                csvWriter.writerow(headerRow)

                for cityName in cityNamesOrdered:
                    rowToWrite = [cityName]
                    for itemName in sortedItemNames:
                        markup = data.get(cityName, {}).get(itemName, '')
                        rowToWrite.append(markup)
                    csvWriter.writerow(rowToWrite)
            else:
                # Cities as columns, Items as rows (original logic)
                headerRow = [''] + cityNamesOrdered
                print(f"Writing header row (cities horizontal): {headerRow}")
                csvWriter.writerow(headerRow)

                # Write data rows (item name, then markups for each city)
                for itemName in sortedItemNames:
                    rowToWrite = [itemName]
                    for cityName in cityNamesOrdered:
                        # Get the markup for the item in the current city
                        # data[cityName] gives the dictionary of items for that city
                        # .get(itemName, '') retrieves the markup, or empty string if item not in city
                        markup = data.get(cityName, {}).get(itemName, '') # Default to empty if city or item missing
                        rowToWrite.append(markup)
                    # print(f"Writing data row for '{itemName}': {rowToWrite[:5]}...") # Log a snippet
                    csvWriter.writerow(rowToWrite)
            
        print(f"Successfully wrote data to {csvFilePath}")

    except IOError:
        print(f"Error: Could not write to CSV file at {csvFilePath}. Check permissions or path.")
    except Exception as e:
        print(f"An unexpected error occurred during CSV writing: {e}")
    
    print(f"--- JSON to CSV conversion finished ---")

if __name__ == "__main__":
    # --- USER CONFIGURATION ---
    inputJsonFile = "translated_game_markups.json" 
    outputCsvFile = "game_markups_spreadsheet.csv"
    citiesHorizontal = True # Set to True to have items as columns and cities as rows
    # --- END USER CONFIGURATION ---

    print(f"Input JSON: {os.path.abspath(inputJsonFile)}")
    print(f"Output CSV: {os.path.abspath(outputCsvFile)}")

    if not os.path.exists(inputJsonFile):
        print(f"Error: The input JSON file '{inputJsonFile}' was not found.")
        print("Please ensure the file from the previous script exists or update the inputJsonFile path.")
    else:
        convertJsonToCsv(inputJsonFile, outputCsvFile, citiesHorizontal)
