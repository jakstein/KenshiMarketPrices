import re
import struct
import json
import os 
import glob

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

    # build regex for item names to match patterns smth like "1234-some_item_name.base" or "5678-another_item.mod"
    # This regex looks for:
    # - One or more digits followed by a hyphen (e.g., "1234-")
    # - Any characters (non-greedy) for the item name part (e.g., "some_item_name")
    # - Followed by a literal dot "."
    # - Ending with either "base" or "mod"
    # The name part itself ([^.\x00]+) now explicitly excludes null bytes in addition to dots.
    # the regex is AI generated and may not be perfect, but it should work for most cases.
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

    # step 1: find all unique item names in the entire file
    uniqueItemNamesSet = set()
    for match in genericItemNameRegex.finditer(fileContent):
        try:
            # group(1) is the full captured item name string "XXXX-suffix"
            uniqueItemNamesSet.add(match.group(1).decode('utf-8'))
        except UnicodeDecodeError:
            print(f"Warning: Could not decode an item name at raw offset {match.start()}. Skipping this potential item.")
    
    if not uniqueItemNamesSet:
        print(f"Warning: No item patterns matching the .base or .mod suffix found in the file. Cannot extract data.")
        return {} 

    sortedUniqueItemNames = sorted(list(uniqueItemNamesSet))
    print(f"Found {len(sortedUniqueItemNames)} unique item types.")

    # step 2: find all occurrences of city names and their positions
    cityOccurrences = []
    if not cityNamesList:
        print("Warning: City names list is empty. No cities to search for.")
        return {}
        
    try:
        byteCityNames = [city.encode('utf-8') for city in cityNamesList]
    except UnicodeEncodeError:
        print("Error: Could not encode city names to UTF-8.")
        return None 
    
    # re.escape is used in case city names have special regex characters. | AI generated block
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

    # step 3: For each city, search for each unique item within its bounds | AI written bit
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
        return extractedData # return the empty dict as is

    # step 4: Filter items appearing in less than 10% of cities
    print("\n--- Applying city appearance frequency filter ---")
    itemCityCounts = {}
    for cityName, items in extractedData.items():
        for itemName in items.keys():
            itemCityCounts[itemName] = itemCityCounts.get(itemName, 0) + 1

    # consider only cities that had at least one item extracted
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
        if filteredItemsForCity: # only add city if it still has items
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

    if os.path.isdir(saveFolderPath): # try looking in the local 'save' folder first
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

    if not foundInLocalSave: # we do some broad search in the AppData directory if no local save was found
        print(f"Attempting to find save file in %LOCALAPPDATA%\\kenshi...")
        localAppData = os.getenv('LOCALAPPDATA')
        if localAppData:
            kenshiAppDataPath = os.path.join(localAppData, 'kenshi')
            # check both kenshi/save and kenshi/ for save files
            searchPaths = [os.path.join(kenshiAppDataPath, 'save'), kenshiAppDataPath]
            appdataSaveFiles = []

            for pathToSearch in searchPaths:
                if os.path.isdir(pathToSearch):
                    print(f"Searching in: {pathToSearch}")
                    # recursive search for *.save files
                    for filepath in glob.glob(os.path.join(pathToSearch, '**', '*.save'), recursive=True):
                        appdataSaveFiles.append(filepath)
                else:
                    print(f"Directory not found: {pathToSearch}")
            
            if appdataSaveFiles:
                # find the most recently modified file
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
    gameFilePath = gameFileToProcess # assign the detected file path

    # provide list of cities | it may not be complete but that's what I was able to come up with lol
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

    # 3. define the acceptable range for markup percentages.
    # we discard stuff below 1% and above 175% as they are likely false positives or outliers
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

        if results is not None: # Check for None in case of early returns due to errors | AI generated block
            if results: # If results is not empty
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
            else: # results is empty, but not None (meaning extraction ran but found nothing)
                print("\n--- EXTRACTION COMPLETE ---")
                print("No data was extracted. This could be due to no items/cities matching the criteria or other logic paths.")

        else: # results is None, indicating a critical error during setup (e.g., file not found, encoding error)
            print("\n--- EXTRACTION FAILED ---")
            print("Extraction failed due to a critical error. Please check messages above.")