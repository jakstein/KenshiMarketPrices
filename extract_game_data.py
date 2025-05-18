import re
import struct
import json
import os 
import glob
import matplotlib.pyplot as plt # for debug
import matplotlib.colors as mcolors # for debug
import matplotlib.patches as mpatches  # for debug

def plot_city_segments(city_occurrences, total_file_length, output_filename="city_segments_visualization.png"): # AI generated code for debugging
    """
    Generates and saves a bar chart visualizing city segments in the file.
    """
    if not city_occurrences:
        print("No city occurrences to plot.")
        return

    fig, ax = plt.subplots(figsize=(15, 3.5))  # Increased figure height

    # Sort cities by position to ensure correct plotting order
    sorted_cities = sorted(city_occurrences, key=lambda x: x['position'])
    
    # Get a list of unique city names for consistent coloring
    unique_city_names = sorted(list(set(c['name'] for c in sorted_cities)))
    # Corrected way to get a colormap
    cmap = plt.colormaps.get_cmap('tab20') 
    colors = [cmap(i/len(unique_city_names)) for i in range(len(unique_city_names))]  # Get colors from cmap
    city_color_map = {name: colors[i] for i, name in enumerate(unique_city_names)}

    for i, city_info in enumerate(sorted_cities):
        start_pos = city_info['position']
        # Determine end_pos: if it's the last city, it extends to the end of the file segment it's in.
        # For visualization, we'll make each city segment distinct up to the next city's start.
        if i + 1 < len(sorted_cities):
            end_pos = sorted_cities[i+1]['position']
        else:
            end_pos = total_file_length 

        segment_length = end_pos - start_pos
        if segment_length <= 0 and i + 1 < len(sorted_cities): 
            print(f"Warning: City '{city_info['name']}' at {start_pos} has zero or negative length before next city '{sorted_cities[i+1]['name']}' at {end_pos}. Adjusting to a minimal visible length.")
            segment_length = total_file_length * 0.001 
            end_pos = start_pos + segment_length

        ax.barh(y=0, width=segment_length, left=start_pos, height=0.5,
                label=f"{city_info['name']} ({start_pos}-{end_pos})",
                color=city_color_map[city_info['name']],
                edgecolor='black')

    ax.set_yticks([])
    ax.set_xlabel("File Offset (Bytes)")
    ax.set_title("City Segments in Game File")
    
    # Create a legend with unique city names and their colors
    handles = [mpatches.Rectangle((0,0),1,1, color=city_color_map[name]) for name in unique_city_names]
    # Place legend below the plot, with multiple columns and smaller font
    ax.legend(handles, unique_city_names, title="Cities",
              loc='upper center',  # Anchor point of the legend box
              bbox_to_anchor=(0.5, -0.20),  # Position: x=center of axes, y=below axes
              ncol=min(len(unique_city_names), 6),  # 1 to 6 columns
              fontsize='small')

    fig.tight_layout() # Adjust layout to make space for the legend
    
    try:
        plt.savefig(output_filename)
        print(f"City segments visualization saved to {output_filename}")
    except Exception as e:
        print(f"Error saving plot: {e}")
    plt.close(fig)


def extractMarkupsFromGameFile(filePath, cityNamesList, markupLowerBound, markupUpperBound):
    """
    Extracts item price markups from a game file based on new logic:
    1. Find all unique item names (e.g., XXXX-name.base, YYYY-name.mod) in the file.
    2. Find all occurrences of specified city names and their positions.
    3. For each city, iterate through all unique item names:
       Search for the first occurrence of the item after the city's position.
       If this occurrence is before the next city's position, extract its markup.
    4. Filter out false positives.
    """
    extractedData = {}

    genericItemNameRegexStr = rb"(\d+-[^.\x00]+\.(?:base|mod))"
    genericItemNameRegex = re.compile(genericItemNameRegexStr)
    
    print(f"DEBUG: Compiled item regex: {genericItemNameRegex.pattern}")

    try:
        with open(filePath, "rb") as f:
            fileContent = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {filePath}")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

    uniqueItemNamesSet = set()
    for match in genericItemNameRegex.finditer(fileContent):
        try:
            uniqueItemNamesSet.add(match.group(1).decode('utf-8'))
        except UnicodeDecodeError:
            print(f"Warning: Could not decode an item name at raw offset {match.start()}. Skipping this potential item.")
    
    if not uniqueItemNamesSet:
        print(f"Warning: No item patterns matching the .base or .mod suffix found in the file. Cannot extract data.")
        return {} 

    sortedUniqueItemNames = sorted(list(uniqueItemNamesSet))
    print(f"Found {len(sortedUniqueItemNames)} unique item types.")

    cityOccurrences = []
    if not cityNamesList:
        print("Warning: City names list is empty. No cities to search for.")
        return {}
        
    try:
        byteCityNames = [city.encode('utf-8') for city in cityNamesList]
    except UnicodeEncodeError:
        print("Error: Could not encode city names to UTF-8.")
        return None 
    
    cityRegexPattern = b"|".join(re.escape(cn) for cn in byteCityNames)
    if not cityRegexPattern: 
        print("Warning: City names list resulted in an empty regex pattern. No cities to search for.")
        return {}

    cityRegex = re.compile(cityRegexPattern)
    for match in cityRegex.finditer(fileContent):
        try:
            cityNameFound = match.group(0).decode('utf-8')
            cityOccurrences.append({
                'name': cityNameFound,
                'position': match.start()
            })
        except UnicodeDecodeError:
            print(f"Warning: Could not decode a potential city name at raw offset {match.start()} using UTF-8.")

    if not cityOccurrences:
        print("Warning: No specified city names found in the file.")
        return {}

    cityOccurrences.sort(key=lambda x: x['position'])
    print(f"Found {len(cityOccurrences)} occurrences of specified cities.")

    if cityOccurrences:
        plot_city_segments(cityOccurrences, len(fileContent))

    numCities = len(cityOccurrences)
    for i, cityInfo in enumerate(cityOccurrences):
        currentCityName = cityInfo['name']
        currentCityPos = cityInfo['position']

        if currentCityName not in extractedData:
            extractedData[currentCityName] = {}
        
        print(f"Processing city: {currentCityName} (found at raw offset {currentCityPos})")

        nextCityStartPos = len(fileContent) 
        if i + 1 < numCities:
            nextCityStartPos = cityOccurrences[i+1]['position']

        for itemNameStr in sortedUniqueItemNames:
            try:
                itemNameBytes = itemNameStr.encode('utf-8')
                specificItemRegex = re.compile(re.escape(itemNameBytes))
            except UnicodeEncodeError:
                print(f"Warning: Could not encode item name '{itemNameStr}' for regex. Skipping this item for city '{currentCityName}'.")
                continue 

            itemMatch = specificItemRegex.search(fileContent, pos=currentCityPos)

            if itemMatch:
                itemFoundStartPos = itemMatch.start()
                
                if itemFoundStartPos < nextCityStartPos:
                    markupStartOffset = itemMatch.end() + 0 
                    markupEndOffset = markupStartOffset + 2

                    if markupEndOffset <= len(fileContent):
                        markupBytes = fileContent[markupStartOffset:markupEndOffset]
                        try:
                            markupRawValue = struct.unpack('<h', markupBytes)[0]
                            markupPercentage = markupRawValue / 100.0
                            if markupLowerBound <= markupPercentage <= markupUpperBound:
                                extractedData[currentCityName][itemNameStr] = markupPercentage
                        except struct.error:
                            pass 
                    else:
                        pass 
                else:
                    pass
            else:
                pass
                
    if not any(extractedData.values()):
        print("Extraction complete, but no items were successfully associated with any cities according to the logic.")
        return extractedData 

    print("\n--- Applying city appearance frequency filter ---")
    itemCityCounts = {}
    for cityName, items in extractedData.items():
        for itemName in items.keys():
            itemCityCounts[itemName] = itemCityCounts.get(itemName, 0) + 1

    citiesWithDataCount = len(extractedData)
    if citiesWithDataCount == 0:
        print("No data extracted for any city, skipping frequency filter.")
        return extractedData

    minAppearanceThreshold = 0.10 * citiesWithDataCount
    print(f"Total cities with data: {citiesWithDataCount}. Minimum appearance threshold (10%): {minAppearanceThreshold:.2f} cities.")

    itemsToRemove = {
        itemName for itemName, count in itemCityCounts.items()
        if count < minAppearanceThreshold
    }

    if itemsToRemove:
        print(f"Found {len(itemsToRemove)} items appearing in fewer than {minAppearanceThreshold:.2f} cities. These will be removed.")
        print(f"Items to remove: {itemsToRemove}")
    else:
        print("No items fall below the city appearance frequency threshold.")

    filteredExtractedData = {}
    for cityName, items in extractedData.items():
        filteredItemsForCity = {
            itemName: markup
            for itemName, markup in items.items()
            if itemName not in itemsToRemove
        }
        if filteredItemsForCity: 
            filteredExtractedData[cityName] = filteredItemsForCity
    
    if not any(filteredExtractedData.values()) and any(extractedData.values()):
        print("Warning: All items were filtered out by the city appearance frequency filter.")
    elif len(itemsToRemove) > 0:
        print("City appearance frequency filter applied.")

    return filteredExtractedData

if __name__ == "__main__":

    saveFolderPath = "save"
    gameFileToProcess = None
    foundInLocalSave = False

    if os.path.isdir(saveFolderPath): 
        potentialFiles = [f for f in os.listdir(saveFolderPath) if os.path.isfile(os.path.join(saveFolderPath, f)) and f.endswith(".save")]
        if potentialFiles:
            if len(potentialFiles) > 1:
                print(f"Warning: Multiple .save files found in '{saveFolderPath}'. Using the first one found: '{potentialFiles[0]}'")
            gameFileToProcess = os.path.join(saveFolderPath, potentialFiles[0])
            print(f"Using game file from local 'save' folder: {gameFileToProcess}")
            foundInLocalSave = True
        else:
            print(f"Local '{saveFolderPath}' directory is empty or contains no .save files.")
    else:
        print(f"Local '{saveFolderPath}' directory was not found.")

    if not foundInLocalSave: 
        print(f"Attempting to find save file in %LOCALAPPDATA%\\kenshi...")
        localAppData = os.getenv('LOCALAPPDATA')
        if localAppData:
            kenshiAppDataPath = os.path.join(localAppData, 'kenshi')
            searchPaths = [os.path.join(kenshiAppDataPath, 'save'), kenshiAppDataPath]
            appdataSaveFiles = []

            for pathToSearch in searchPaths:
                if os.path.isdir(pathToSearch):
                    print(f"Searching in: {pathToSearch}")
                    for filepath in glob.glob(os.path.join(pathToSearch, '**', '*.save'), recursive=True):
                        appdataSaveFiles.append(filepath)
                else:
                    print(f"Directory not found: {pathToSearch}")
            
            if appdataSaveFiles:
                latestFile = max(appdataSaveFiles, key=os.path.getmtime)
                gameFileToProcess = latestFile
                print(f"Found latest save file in AppData: {gameFileToProcess}")
            else:
                print(f"No .save files found in %LOCALAPPDATA%\\kenshi or its 'save' subdirectory.")
        else:
            print("Error: LOCALAPPDATA environment variable not found.")

    if not gameFileToProcess:
        print(f"\nError: No game save file could be automatically detected.")
        print(f"Please ensure a '.save' file exists in the '{saveFolderPath}' directory")
        print(f"or in your Kenshi AppData directory (usually %LOCALAPPDATA%\\kenshi or %LOCALAPPDATA%\\kenshi\\save).")
        exit()
    
    print(f"Using game file: {gameFileToProcess}")
    gameFilePath = gameFileToProcess 

    cityNames = [
        "Admag", "Bark", "Black Desert City", "Black Scratch", "Blister Hill",
        "Brink", "Catun", "Clownsteady", "Crab Town", "Drifter's Last",
        "Eyesocket", "Flats Lagoon", "Floodlands", "Free Settlement",
        "Grayflayer Village", "Heft", "Heng", "Hub",
        "Kral's Chosen", "Last Stand", "Mongrel", "Mourn", "Okran's Fist",
        "Okran's Gulf", "Okran's Pride", "Okran's Shield", "Rebirth", "Rot",
        "Shark", "Sho-Battai", "Squin", "Stack", "Stoat", "The Great Fortress",
        "The Hook", "Tinfist's Hideout", "Trader's Edge", "Treg's Tower",
        "Waystation", "World's End",
    ]

    markupLowerBoundConfig = 1.0 
    markupUpperBoundConfig = 175.0 

    print(f"Starting data extraction for file: {gameFilePath}")
    print(f"Searching for cities: {cityNames}")
    print(f"Acceptable markup range: {markupLowerBoundConfig} to {markupUpperBoundConfig}")

    if gameFilePath is None or not cityNames:
        print("\nCONFIGURATION NEEDED / FILE ISSUE")
        if gameFilePath is None:
            print("Error: No game file was identified to process.")
        if not cityNames:
            print("Please open the script and populate the cityNames list.")
    else:
        results = extractMarkupsFromGameFile(gameFilePath, cityNames, markupLowerBoundConfig, markupUpperBoundConfig)

        if results is not None: 
            if results: 
                print("\n--- EXTRACTION COMPLETE ---")
                jsonOutput = json.dumps(results, indent=2)
                print("\nFinal JSON Output:")
                print(jsonOutput)

                outputFilename = "extracted_game_markups.json"
                try:
                    with open(outputFilename, "w") as outfile:
                        json.dump(results, outfile, indent=2)
                    print(f"\nData also saved to: {outputFilename}")
                except IOError:
                    print(f"\nCould not write output to file: {outputFilename}")
            else: 
                print("\n--- EXTRACTION COMPLETE ---")
                print("No data was extracted. This could be due to no items/cities matching the criteria or other logic paths.")

        else: 
            print("\n--- EXTRACTION FAILED ---")
            print("Extraction failed due to a critical error. Please check messages above.")