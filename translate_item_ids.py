import json
import re
import os
import string 
import ctypes 

def getWindowsDrives(): # get all available drives on Windows using ctypes
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(letter + ":\\\\") # use double backslash for path compatibility
        bitmask >>= 1
    if not drives: # fall back
        print("ctypes.windll.kernel32.GetLogicalDrives() returned no drives. Falling back to checking C, D, E, F.")
        for letter in ['C', 'D', 'E', 'F']:
             drivePath = letter + ":\\\\"
             if os.path.exists(drivePath):
                 drives.append(drivePath)
    return drives

def findKenshiSteamPath(): # searches for kenshi instal path across the drives and only up to 3 levels deep
    drives = getWindowsDrives()
    if not drives:
        print("No drives found to scan for Kenshi installation.")
        return None
        
    print(f"Scanning drives: {', '.join(drives)} for Kenshi installation (looking for SteamLibrary)...")

    for drive in drives:
        print(f"  Scanning drive {drive}...")
        # level 1: drive:\\SteamLibrary
        steamLibPathL1 = os.path.join(drive, "SteamLibrary")
        kenshiPathL1 = os.path.join(steamLibPathL1, "steamapps", "common", "Kenshi")
        if os.path.isdir(kenshiPathL1):
            print(f"    Found Kenshi at: {kenshiPathL1}")
            return kenshiPathL1

        # level 2: drive:\\folder1\\SteamLibrary
        try:
            for item1 in os.listdir(drive):
                pathLevel1Dir = os.path.join(drive, item1)
                if os.path.isdir(pathLevel1Dir):
                    steamLibPathL2 = os.path.join(pathLevel1Dir, "SteamLibrary")
                    kenshiPathL2 = os.path.join(steamLibPathL2, "steamapps", "common", "Kenshi")
                    if os.path.isdir(kenshiPathL2):
                        print(f"    Found Kenshi at: {kenshiPathL2}")
                        return kenshiPathL2
                    
                    # level 3: drive:\\folder1\\folder2\\SteamLibrary
                    try:
                        for item2 in os.listdir(pathLevel1Dir):
                            pathLevel2Dir = os.path.join(pathLevel1Dir, item2)
                            if os.path.isdir(pathLevel2Dir):
                                steamLibPathL3 = os.path.join(pathLevel2Dir, "SteamLibrary")
                                kenshiPathL3 = os.path.join(steamLibPathL3, "steamapps", "common", "Kenshi")
                                if os.path.isdir(kenshiPathL3):
                                    print(f"    Found Kenshi at: {kenshiPathL3}")
                                    return kenshiPathL3
                    except PermissionError: # silently ignore permission errors for subfolders
                        pass 
                    except FileNotFoundError:
                        pass
        except PermissionError:
            print(f"Permission denied listing contents of {drive}. Skipping deeper scan on this drive.")
        except FileNotFoundError:
            print(f"Drive {drive} or its contents not accessible. Skipping.")
            
    print("Kenshi installation path not found via SteamLibrary search across all drives.")
    return None

def collectModAndBaseFiles(baseSearchPath): # look for .mod and .base files in the given path and its subdirectories
    foundFiles = []
    print(f"Searching for .mod and .base files in '{baseSearchPath}'...")
    if not os.path.isdir(baseSearchPath):
        print(f"Error: Provided path '{baseSearchPath}' is not a directory.")
        return foundFiles
        
    for root, _, files in os.walk(baseSearchPath):
        for file in files:
            if file.lower().endswith(".mod") or file.lower().endswith(".base"):
                fullPath = os.path.join(root, file)
                foundFiles.append(fullPath)
                print(f"Added dictionary file: {fullPath}")
    if not foundFiles:
        print(f"No .mod or .base files found in '{baseSearchPath}' or its subdirectories.")
    return foundFiles

def findItemNameInFile(itemIdBytes, fileContent):
    """
    Searches for the human-readable name of a given itemIdBytes in the fileContent.
    1. Find itemIdBytes.
    2. Check preceding bytes for separator (VAR_BYTE, 0x00, 0x00, 0x00).
    3. If separator found, extract name before it.
    4. If not, continue search for itemIdBytes.
    """
    itemIdStrForDebug = itemIdBytes.decode('utf-8', errors='ignore')
    print(f"Attempting to find name for ID: {itemIdStrForDebug}")
    currentPos = 0
    itemIdLen = len(itemIdBytes)
    separatorLen = 4  # 1 variable byte + 3 null bytes

    while currentPos < len(fileContent):
        print(f"Searching for ID '{itemIdStrForDebug}' occurrence starting from position {currentPos}...")
        try:
            itemIdStartPos = fileContent.find(itemIdBytes, currentPos)
        except Exception as e:
            print(f"Error during fileContent.find for '{itemIdStrForDebug}': {e}")
            return None

        if itemIdStartPos == -1:
            print(f"ID '{itemIdStrForDebug}' not found after position {currentPos}.")
            break  # exit while loop, will return None later

        print(f"Found potential ID '{itemIdStrForDebug}' at position {itemIdStartPos}.")

        if itemIdStartPos < separatorLen:
            print(f"Not enough space before ID at {itemIdStartPos} for a separator. Advancing search position.")
            currentPos = itemIdStartPos + itemIdLen
            continue

        separatorStartPos = itemIdStartPos - separatorLen
        potentialSeparator = fileContent[separatorStartPos : itemIdStartPos]

        print(f"Checking bytes from {separatorStartPos} to {itemIdStartPos-1} (hex: {potentialSeparator.hex()}) for separator pattern...")

        if (potentialSeparator[0] != 0x00 and
            potentialSeparator[1:4] == b'\x00\x00\x00'):
            print(f"Separator pattern MATCHED: {potentialSeparator.hex()}")

            nameEndPos = separatorStartPos
            nameStartPos = -1
            
            currentNameScanPos = nameEndPos - 1
            print(f"Scanning backwards from position {currentNameScanPos} for start of name string...")
            while currentNameScanPos >= 0:
                if fileContent[currentNameScanPos] == 0x00:
                    nameStartPos = currentNameScanPos + 1
                    print(f"Found null byte at {currentNameScanPos}, name starts at {nameStartPos}.")
                    break
                currentNameScanPos -= 1
            
            if currentNameScanPos < 0 and nameEndPos > 0: # reached beginning of file
                nameStartPos = 0
                print(f"Reached beginning of file, name starts at 0.")
            
            if nameStartPos != -1 and nameStartPos < nameEndPos:
                nameBytes = fileContent[nameStartPos : nameEndPos]
                print(f"Extracted potential name bytes (hex: {nameBytes.hex()}) from pos {nameStartPos} to {nameEndPos-1}")
                try:
                    humanName = nameBytes.decode('utf-8', errors='replace').strip()
                    if humanName:
                        print(f"Successfully decoded name: '{humanName}'")
                        return humanName
                    else:
                        print(f"Decoded name is empty after stripping. Discarding this match.")
                except Exception as e:
                    print(f"Error decoding name bytes: {e}. Discarding this match.")
            else:
                print(f"Could not determine valid name string before separator. Discarding this match.")
        else:
            print(f"Separator pattern MISMATCHED. Bytes were: {potentialSeparator.hex()}.")

        print(f"Advancing search for '{itemIdStrForDebug}' past current position {itemIdStartPos + itemIdLen -1}.")
        currentPos = itemIdStartPos + itemIdLen
        if currentPos >= len(fileContent):
             print(f"Reached end of file while advancing search for '{itemIdStrForDebug}'.")
             break

    print(f"Finished searching for ID '{itemIdStrForDebug}'. Name not found with this logic.")
    return None

def translateAllItemIds(markupsJsonPath, dictionaryFilePaths, outputJsonPath):
    print(f"Starting item ID translation process")
    print(f"Attempting to load markups from: {markupsJsonPath}")
    try:
        with open(markupsJsonPath, 'r', encoding='utf-8') as f:
            cityMarkups = json.load(f)
        print(f"Successfully loaded markups JSON.")
    except FileNotFoundError:
        print(f"Error: Markups JSON file not found at {markupsJsonPath}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {markupsJsonPath}")
        return
    except Exception as e:
        print(f"Error reading {markupsJsonPath}: {e}")
        return

    print("Collecting all unique item IDs from markups...")
    allItemIds = set()
    for cityData in cityMarkups.values():
        for itemId in cityData.keys():
            allItemIds.add(itemId)

    if not allItemIds:
        print("No item IDs found in the markups JSON. Nothing to translate.")
        try:
            with open(outputJsonPath, 'w', encoding='utf-8') as f:
                json.dump(cityMarkups, f, indent=2, ensure_ascii=False)
            print(f"Output (potentially unchanged) saved to {outputJsonPath}")
        except IOError:
            print(f"Could not write output to file: {outputJsonPath}")
        return

    print(f"Found {len(allItemIds)} unique item IDs to translate.")
    itemIdToNameMap = {}
    processedItemIds = set() 

    for dictFilePath in dictionaryFilePaths:
        if not os.path.exists(dictFilePath):
            print(f"Warning: Dictionary file not found at {dictFilePath}. Skipping.")
            continue
        
        print(f"\nProcessing dictionary file: {dictFilePath}...")
        try:
            print(f"Reading content of {dictFilePath}...")
            with open(dictFilePath, "rb") as f:
                dictContent = f.read()
            print(f"Successfully read {len(dictContent)} bytes from {dictFilePath}.")
        except Exception as e:
            print(f"Error reading dictionary file {dictFilePath}: {e}. Skipping.")
            continue

        itemsToSearchInThisFile = allItemIds - processedItemIds
        if not itemsToSearchInThisFile:
            print(f"All item IDs already mapped. No new items to search in {dictFilePath}.")
            continue
        
        print(f"Attempting to find names for {len(itemsToSearchInThisFile)} item ID(s) in this file...")
        foundInThisFileCount = 0
        for itemIdStr in itemsToSearchInThisFile:
            print(f"Searching for item ID: {itemIdStr}...")
            try:
                itemIdBytes = itemIdStr.encode('utf-8')
            except UnicodeEncodeError:
                print(f"Warning: Could not encode item ID '{itemIdStr}' to UTF-8. Skipping this ID for this file.")
                continue

            humanName = findItemNameInFile(itemIdBytes, dictContent)
            if humanName:
                print(f"Found mapping in {os.path.basename(dictFilePath)}: '{itemIdStr}' -> '{humanName}'")
                itemIdToNameMap[itemIdStr] = humanName
                processedItemIds.add(itemIdStr)
                foundInThisFileCount += 1
            else:
                print(f"No mapping found for item ID: {itemIdStr} in {os.path.basename(dictFilePath)}")
        print(f"Found {foundInThisFileCount} new mappings in {dictFilePath}.")

    print("\nTranslation of item IDs to names complete")
    print(f"Total items mapped: {len(itemIdToNameMap)} out of {len(allItemIds)} unique IDs.")

    print("Constructing final translated markups JSON...")
    translatedMarkups = {}
    for cityName, itemsData in cityMarkups.items():
        translatedMarkups[cityName] = {}
        for itemId, valueAndOffset in itemsData.items():
            itemName = itemIdToNameMap.get(itemId, itemId) # use original ID if no translation
            translatedMarkups[cityName][itemName] = valueAndOffset
    
    untranslatedIds = allItemIds - set(itemIdToNameMap.keys())
    if untranslatedIds:
        print(f"\nWarning: {len(untranslatedIds)} item ID(s) could not be translated from any dictionary file:")
        for itemId in sorted(list(untranslatedIds)):
            print(f"  - {itemId}")
    else:
        print("\nAll item IDs were successfully translated!")

    try:
        print(f"\nAttempting to save translated markups to: {outputJsonPath}")
        with open(outputJsonPath, 'w', encoding='utf-8') as f:
            json.dump(translatedMarkups, f, indent=2, ensure_ascii=False)
        print(f"Translated markups successfully saved to: {outputJsonPath}")
    except IOError:
        print(f"\nCould not write translated output to file: {outputJsonPath}")
    except Exception as e:
        print(f"\nError writing translated JSON: {e}")
    print(f"--- Item ID translation process finished ---")

if __name__ == "__main__":
    # --- USER CONFIGURATION ---
    MARKUPS_JSON_FILE = "extracted_game_markups.json"
    DATAFILES_DIR = "datafiles"  # local dir to look in first 
    OUTPUT_TRANSLATED_JSON_FILE = "translated_game_markups.json"
    # --- END USER CONFIGURATION ---

    dictionaryFiles = []

    # 1. attempt to load from local DATAFILES_DIR
    print(f"--- Locating dictionary files ---")
    if os.path.exists(DATAFILES_DIR) and os.path.isdir(DATAFILES_DIR):
        print(f"Checking for dictionary files in local '{DATAFILES_DIR}' directory...")
        localFiles = [os.path.join(DATAFILES_DIR, f) for f in os.listdir(DATAFILES_DIR) if os.path.isfile(os.path.join(DATAFILES_DIR, f))]
        if localFiles:
            dictionaryFiles.extend(localFiles)
            print(f"Found {len(localFiles)} file(s) in '{DATAFILES_DIR}'.")
        else:
            print(f"Local '{DATAFILES_DIR}' directory is empty.")
    else:
        print(f"Local '{DATAFILES_DIR}' directory not found or is not a directory.")

    # 2. iff local directory is empty or not found, try automatic Kenshi path detection
    if not dictionaryFiles:
        print(f"\nNo files found in '{DATAFILES_DIR}'. Attempting to locate Kenshi game files automatically...")
        kenshiInstallPath = findKenshiSteamPath()
        if kenshiInstallPath:
            print(f"Kenshi installation found at: {kenshiInstallPath}")
            gameFiles = collectModAndBaseFiles(kenshiInstallPath)
            if gameFiles:
                dictionaryFiles.extend(gameFiles)
                print(f"Using {len(gameFiles)} .mod and .base files from Kenshi installation as dictionaries.")
            else:
                print(f"Found Kenshi directory at '{kenshiInstallPath}', but no .mod or .base files were located within it.")
        else:
            print("Could not automatically locate Kenshi installation directory via SteamLibrary search.")
    
    print(f"--- Finished locating dictionary files ---\n")

    # proceed with translation if dictionary files are found
    if not dictionaryFiles:
        print("Error: No dictionary files were found locally or through automatic Kenshi detection.")
        print("Please ensure Kenshi is installed via Steam, or place .mod/.base files in a 'datafiles' directory.")
    elif MARKUPS_JSON_FILE == "extracted_game_markups.json" and not os.path.exists(MARKUPS_JSON_FILE):
         print(f"Error: The default input file '{MARKUPS_JSON_FILE}' does not exist in the current directory.")
         print("Please ensure the file from the previous script ('extract_game_data.py') is present or update MARKUPS_JSON_FILE path.")
    else:
        translateAllItemIds(MARKUPS_JSON_FILE, dictionaryFiles, OUTPUT_TRANSLATED_JSON_FILE)
