import sys
import os
import json
import struct
import subprocess
import random
from PySide6.QtWidgets import (QApplication, QMainWindow, QTableWidget, 
                               QTableWidgetItem, QVBoxLayout, QWidget,
                               QPushButton, QMenuBar, QMessageBox, QLineEdit, 
                               QHBoxLayout, QComboBox, QLabel)
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtCore import Qt
# few bits AI generated, mostly error handling and subprocess handling
EXTRACTED_MARKUPS_FILE = "extracted_game_markups.json"
TRANSLATED_MARKUPS_FILE = "translated_game_markups.json"
DEFAULT_SAVE_PATH_MARKER = "SAVE_FILE_PATH:"

class MarkupEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kenshi Save Game Markup Editor")
        self.setGeometry(100, 100, 850, 650)

        # random
        randomizationLayout = QHBoxLayout()
        self.lowerCapLineEdit = QLineEdit("70.0")
        self.lowerCapLineEdit.setPlaceholderText("Lower Cap %")
        self.upperCapLineEdit = QLineEdit("140.5")
        self.upperCapLineEdit.setPlaceholderText("Upper Cap %")
        self.distTypeComboBox = QComboBox()
        self.distTypeComboBox.addItems(["Uniform", "Normal", "Triangular", "Beta (Two-Peak)"])
        self.randomizeButton = QPushButton("Randomize Markups")
        self.randomizeButton.clicked.connect(self.randomizeMarkups)

        randomizationLayout.addWidget(QLabel("Lower Cap:"))
        randomizationLayout.addWidget(self.lowerCapLineEdit)
        randomizationLayout.addWidget(QLabel("Upper Cap:"))
        randomizationLayout.addWidget(self.upperCapLineEdit)
        randomizationLayout.addWidget(QLabel("Distribution:"))
        randomizationLayout.addWidget(self.distTypeComboBox)
        randomizationLayout.addWidget(self.randomizeButton)

        # filterin
        self.cityFilterLineEdit = QLineEdit()
        self.cityFilterLineEdit.setPlaceholderText("Filter by City")
        self.cityFilterLineEdit.textChanged.connect(self.filterTable)

        self.itemFilterLineEdit = QLineEdit()
        self.itemFilterLineEdit.setPlaceholderText("Filter by Item Name")
        self.itemFilterLineEdit.textChanged.connect(self.filterTable)

        filterLayout = QHBoxLayout()
        filterLayout.addWidget(self.cityFilterLineEdit)
        filterLayout.addWidget(self.itemFilterLineEdit)

        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(["City", "Item Name", "Markup (%)"])
        self.tableWidget.setColumnWidth(0, 150) 
        self.tableWidget.setColumnWidth(1, 350) 
        self.tableWidget.setColumnWidth(2, 100)

        self.saveButton = QPushButton("Apply Changes")
        self.saveButton.clicked.connect(self.applyChanges)

        self.reloadButton = QPushButton("Reload Data & Scripts")
        self.reloadButton.clicked.connect(self.reloadAllData)

        self.saveModeComboBox = QComboBox()
        self.saveModeComboBox.addItems(["Save to Local Copy (Default)", "Direct Write to Original Save"])
        self.saveModeComboBox.currentIndexChanged.connect(self.handleSaveModeChange)

        controlsLayout = QHBoxLayout()
        controlsLayout.addWidget(self.reloadButton)
        controlsLayout.addWidget(self.saveButton)
        controlsLayout.addWidget(self.saveModeComboBox)

        layout = QVBoxLayout()
        layout.addLayout(randomizationLayout) 
        layout.addLayout(filterLayout)
        layout.addWidget(self.tableWidget)
        layout.addLayout(controlsLayout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.menuBar().setVisible(False) # Hide the menu bar

        self.data = {}
        self.originalSaveFilePath = None
        self.saveMode = "local_copy" # "direct_write" or "local_copy"

        self.runInitialScripts()
        if self.saveButton.isEnabled(): # only load data when stuff works
            self.loadData()

    def handleSaveModeChange(self, index):
        if index == 0:
            newMode = "local_copy"
        elif index == 1:
            newMode = "direct_write"
        else:
            return
        self.setSaveMode(newMode)

    def setSaveMode(self, saveMode):
        self.saveMode = saveMode
        QMessageBox.information(self, "Save Mode Changed", f"Save mode set to: {saveMode.replace('_', ' ').title()}")

    def filterTable(self):
        cityFilterText = self.cityFilterLineEdit.text().lower()
        itemFilterText = self.itemFilterLineEdit.text().lower()

        for rowIdx in range(self.tableWidget.rowCount()):
            cityItem = self.tableWidget.item(rowIdx, 0)
            itemNameItem = self.tableWidget.item(rowIdx, 1)

            if cityItem and itemNameItem:
                cityMatch = cityFilterText in cityItem.text().lower()
                itemMatch = itemFilterText in itemNameItem.text().lower()
                
                self.tableWidget.setRowHidden(rowIdx, not (cityMatch and itemMatch))
    
    def randomizeMarkups(self):
        try:
            lowerCap = float(self.lowerCapLineEdit.text())
            upperCap = float(self.upperCapLineEdit.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Lower and Upper caps must be valid numbers.")
            return

        if lowerCap >= upperCap:
            QMessageBox.warning(self, "Invalid Input", "Lower cap must be less than Upper cap.")
            return

        distributionType = self.distTypeComboBox.currentText()
        
        changedCount = 0
        for rowIdx in range(self.tableWidget.rowCount()):
            markupItem = self.tableWidget.item(rowIdx, 2)
            if markupItem:
                newMarkupValue = 0.0
                if distributionType == "Uniform":
                    newMarkupValue = random.uniform(lowerCap, upperCap)
                elif distributionType == "Normal":
                    mu = (lowerCap + upperCap) / 2
                    sigma = (upperCap - lowerCap) / 4 
                    if sigma <= 0:
                        newMarkupValue = mu
                    else:
                        value = random.normalvariate(mu, sigma)
                        newMarkupValue = max(lowerCap, min(upperCap, value))
                elif distributionType == "Triangular":
                    mode = (lowerCap + upperCap) / 2
                    newMarkupValue = random.triangular(lowerCap, upperCap, mode)
                elif distributionType == "Beta (Two-Peak)":
                    alpha = 0.5
                    beta = 0.5
                    x = random.betavariate(alpha, beta)
                    newMarkupValue = lowerCap + x * (upperCap - lowerCap)

                markupItem.setText(f"{newMarkupValue:.2f}")
                changedCount +=1
        
        if changedCount > 0:
            QMessageBox.information(self, "Randomization Complete", f"Randomized markups for {changedCount} items.")
        else:
            QMessageBox.information(self, "Randomization", "No items found to randomize.")
        
        self.filterTable()

    def runInitialScripts(self):
        self.originalSaveFilePath = None 
        self.saveButton.setEnabled(True)
        try:
            scriptDir = os.path.dirname(os.path.realpath(__file__))
            extractScriptPath = os.path.join(scriptDir, "extract_game_data.py")
            translateScriptPath = os.path.join(scriptDir, "translate_item_ids.py")

            print("Running extraction script...")
            processExtract = subprocess.run([sys.executable, extractScriptPath], capture_output=True, text=True, check=False, cwd=scriptDir)
            print("Extraction script stdout:")
            print(processExtract.stdout)
            if processExtract.stderr:
                print("Extraction script stderr:")
                print(processExtract.stderr)
            if processExtract.returncode != 0:
                raise subprocess.CalledProcessError(processExtract.returncode, extractScriptPath, processExtract.stdout, processExtract.stderr)

            for line in processExtract.stdout.splitlines():
                if line.startswith(DEFAULT_SAVE_PATH_MARKER):
                    self.originalSaveFilePath = line.split(DEFAULT_SAVE_PATH_MARKER, 1)[1].strip()
                    print(f"Detected original save file path: {self.originalSaveFilePath}")
                    break
            
            if not self.originalSaveFilePath:
                QMessageBox.warning(self, "Error", "Could not determine original save file path from extraction script output. Please ensure the script prints 'SAVE_FILE_PATH:your_path_to.save'. Saving will be disabled.")
                self.saveButton.setEnabled(False)
                return 

            print("\nRunning translation script...")
            processTranslate = subprocess.run([sys.executable, translateScriptPath], capture_output=True, text=True, check=False, cwd=scriptDir)
            print("Translation script stdout:")
            print(processTranslate.stdout)
            if processTranslate.stderr:
                print("Translation script stderr:")
                print(processTranslate.stderr)
            if processTranslate.returncode != 0:
                raise subprocess.CalledProcessError(processTranslate.returncode, translateScriptPath, processTranslate.stdout, processTranslate.stderr)
            
            QMessageBox.information(self, "Scripts Complete", "Data extraction and translation finished successfully.")

        except subprocess.CalledProcessError as e:
            errorMessage = f"Error running script: {os.path.basename(e.cmd[-1])}\nReturn Code: {e.returncode}\nOutput:\n{e.stdout}\nError:\n{e.stderr}"
            QMessageBox.critical(self, "Script Execution Error", errorMessage)
            print(errorMessage)
            self.saveButton.setEnabled(False) 
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Script Not Found", f"A Python script was not found: {e.filename}. Ensure extract_game_data.py and translate_item_ids.py are in the same directory as this editor.")
            self.saveButton.setEnabled(False)
        except subprocess.TimeoutExpired as e:
            QMessageBox.critical(self, "Script Timeout", f"The script {os.path.basename(e.cmd[-1])} timed out.")
            self.saveButton.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error During Script Execution", f"An unexpected error occurred: {e}")
            self.saveButton.setEnabled(False)

    def loadData(self):
        try:
            scriptDir = os.path.dirname(os.path.realpath(__file__))
            translatedFileFullPath = os.path.join(scriptDir, TRANSLATED_MARKUPS_FILE)
            with open(translatedFileFullPath, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            QMessageBox.warning(self, "Data File Error", f"{TRANSLATED_MARKUPS_FILE} not found in script directory. Was translation successful?")
            self.data = {}
            self.tableWidget.setRowCount(0) # we clearin table
            return
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Data File Error", f"Could not decode JSON from {TRANSLATED_MARKUPS_FILE}. The file might be corrupted.")
            self.data = {}
            self.tableWidget.setRowCount(0) # again clearin table
            return
 
        self.populateTable()

    def populateTable(self):
        self.tableWidget.setRowCount(0)
        rowIdx = 0
        for city, items in self.data.items():
            for itemName, dataList in items.items():
                if not isinstance(dataList, list) or len(dataList) != 2:
                    print(f"Skipping malformed data entry for City: '{city}', Item: '{itemName}'. Data: {dataList}")
                    continue

                markupValue, offset = dataList
                self.tableWidget.insertRow(rowIdx)
                
                cityItemWidget = QTableWidgetItem(city)
                cityItemWidget.setFlags(cityItemWidget.flags() & ~Qt.ItemIsEditable)
                self.tableWidget.setItem(rowIdx, 0, cityItemWidget)

                nameItemWidget = QTableWidgetItem(itemName)
                nameItemWidget.setFlags(nameItemWidget.flags() & ~Qt.ItemIsEditable)
                self.tableWidget.setItem(rowIdx, 1, nameItemWidget)

                markupItemWidget = QTableWidgetItem(str(markupValue))
                markupItemWidget.setData(Qt.UserRole, {"originalValue": markupValue, "offset": offset, "city": city, "itemName": itemName})
                self.tableWidget.setItem(rowIdx, 2, markupItemWidget)
                rowIdx += 1
        self.filterTable()

    def reloadAllData(self):
        self.runInitialScripts()
        if self.saveButton.isEnabled():
            self.loadData()
        else:
            self.tableWidget.setRowCount(0)
            self.filterTable()

    def applyChanges(self):
        if not self.originalSaveFilePath:
            QMessageBox.critical(self, "Cannot Save", "Original save file path is unknown. Cannot apply changes. Try reloading data & scripts.")
            return

        targetFilePath = ""
        scriptDir = os.path.dirname(os.path.realpath(__file__))

        if self.saveMode == "direct_write":
            targetFilePath = self.originalSaveFilePath
            reply = QMessageBox.warning(self, "Direct Write Confirmation",
                                        f"This will directly overwrite your save file:\n{targetFilePath}\n\nARE YOU ABSOLUTELY SURE? This action cannot be undone.",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return
        elif self.saveMode == "local_copy":
            baseName = os.path.basename(self.originalSaveFilePath)
            localCopyName = f"edited_{baseName}"
            targetFilePath = os.path.join(scriptDir, localCopyName)
            
            try:
                import shutil
                shutil.copy2(self.originalSaveFilePath, targetFilePath)
                QMessageBox.information(self, "Local Copy Created", f"A local copy has been made at:\n{targetFilePath}\nChanges will be applied to this copy.")
            except FileNotFoundError:
                QMessageBox.critical(self, "Error Creating Local Copy", f"Original save file not found at: {self.originalSaveFilePath}")
                return
            except Exception as e:
                QMessageBox.critical(self, "Error Creating Local Copy", f"Could not create local copy: {e}")
                return
        else:
            QMessageBox.critical(self, "Internal Error", "Invalid save mode selected.")
            return

        changesToApply = []
        for rowIdxTable in range(self.tableWidget.rowCount()):
            markupItem = self.tableWidget.item(rowIdxTable, 2)
            itemData = markupItem.data(Qt.UserRole)
            
            try:
                newMarkupStr = markupItem.text()
                newMarkupFloat = float(newMarkupStr)
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", f"Invalid markup value for '{itemData['itemName']}' in city '{itemData['city']}': '{newMarkupStr}'. It must be a number. This item will be skipped.")
                continue

            # compare floats with a small tolerance
            if abs(newMarkupFloat - itemData["originalValue"]) > 1e-9:
                rawValueToWrite = int(round(newMarkupFloat * 100))
                try:
                    # kenshi uses signed short (2 bytes), little-endian (i think)
                    if not (-32768 <= rawValueToWrite <= 32767):
                        raise ValueError(f"Markup value {newMarkupFloat}% ({rawValueToWrite}) is out of range for a 16-bit signed integer.")
                    bytesToWrite = struct.pack('<h', rawValueToWrite)
                    changesToApply.append({"offset": itemData["offset"], "bytes": bytesToWrite, "itemName": itemData["itemName"], "city": itemData["city"]})
                except (struct.error, ValueError) as e:
                    QMessageBox.warning(self, "Value Error", f"Could not prepare value for '{itemData['itemName']}' (City: {itemData['city']}, New Value: {newMarkupFloat}%): {e}. This item will be skipped.")
                    continue
        
        if not changesToApply:
            QMessageBox.information(self, "No Changes", "No markups were modified or valid changes detected.")
            return

        try:
            with open(targetFilePath, 'r+b') as saveFile:
                for change in changesToApply:
                    saveFile.seek(change["offset"])
                    saveFile.write(change["bytes"])
            QMessageBox.information(self, "Success", f"{len(changesToApply)} change(s) successfully applied to:\n{targetFilePath}")
        except FileNotFoundError:
             QMessageBox.critical(self, "File Error", f"Target file for saving not found: {targetFilePath}. This may occur if the original file was moved or deleted.")
        except Exception as e:
            QMessageBox.critical(self, "Error Writing File", f"Could not write changes to {targetFilePath}: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = MarkupEditor()
    editor.show()
    sys.exit(app.exec())
