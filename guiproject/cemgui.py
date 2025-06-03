import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QTextEdit, QTableWidget, QTableWidgetItem, QLabel, QComboBox, QFileDialog
)
from PyQt5.QtGui import QFont, QColor, QBrush
from PyQt5.QtCore import Qt
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.dom import minidom

import subprocess as subp;

NUM_CAUSES = 32
NUM_EFFECTS = 32

CAUSE_FIELDS = ["CauseName", "Input1", "Input1Type", "Input2", "Input2Type", "Op", "Description"]
EFFECT_FIELDS = ["EffectName", "Output", "OutputType", "Op", "OptTimerValue", "Description"]

class MainWindow(QMainWindow):
    def init_fill(self):
        header_font = QFont()
        header_font.setBold(True)

        for col, field in enumerate(CAUSE_FIELDS):
            item = QTableWidgetItem(field)
            item.setFont(header_font)
            item.setBackground(QBrush(QColor("#f280a1")))
            self.table.setItem(5,col, item)
            self.table.item(5, col).setFlags(Qt.NoItemFlags) # Makes the headers untragetable.
            self.table.item(5, col).setForeground(QBrush(QColor("black")))
            
        for row, field in enumerate(EFFECT_FIELDS):
            item = QTableWidgetItem(field)
            item.setFont(header_font)
            if (row == 5):
                item.setBackground(QBrush(QColor("#C573B6")))
            else:
                item.setBackground(QBrush(QColor("#9966cc")))
            self.table.setItem(row,6, item)
            self.table.item(row, 6).setFlags(Qt.NoItemFlags) # Makes the headers untragetable.
            self.table.item(row,6).setForeground(QBrush(QColor("black")))

        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                if not self.table.item(row,col):
                    self.table.setItem(row,col, QTableWidgetItem())
                        
                if row < 5 and col < 6:
                    self.table.item(row,col).setFlags(Qt.NoItemFlags)
                    self.table.item(row,col).setBackground(QBrush(QColor("black")))

                elif (row >= 6 and (col == 2 or col == 4)):
                    item = QComboBox()
                    item.addItems(["","Bool","Int","ConstantBool","ConstantInt"])
                    self.table.setCellWidget(row,col,item)

                elif (row == 2 and col >= 7):
                    item = QComboBox()
                    item.addItems(["","Bool"])
                    self.table.setCellWidget(row,col,item)

                elif (row >= 6 and col == 5):
                    item = QComboBox()
                    item.addItems(["","Direct","And","Or","Xor","EQ","GE","GT","LE","LT","NEQ"])
                    self.table.setCellWidget(row,col,item)

                elif (row == 3 and col >= 7):
                    item = QComboBox()
                    item.addItems(["","Direct","TOf","TOn","TP"])
                    self.table.setCellWidget(row,col,item)
                
                # Intersections

                elif row >= 6 and col >= 7:
                    self.table.item(row,col).setBackground(QBrush(QColor("#f280a1")))
                    self.table.item(row,col).setForeground(QBrush(QColor("black")))

                # Rows for cause section
                
                elif row >= 6 and col < 7:
                    self.table.item(row,col).setBackground(QBrush(QColor("white")))
                    self.table.item(row,col).setForeground(QBrush(QColor("black")))

                # Columns for effect section

                elif row < 6 and col >= 7:
                    self.table.item(row,col).setBackground(QBrush(QColor("white")))
                    self.table.item(row,col).setForeground(QBrush(QColor("black")))

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cause & Effect Matrix")
        self.setGeometry(100, 100, 1400, 800)
        layout = QVBoxLayout()
        self.table= QTableWidget()
        self.table.setRowCount(NUM_CAUSES + 6)
        self.table.setColumnCount(NUM_EFFECTS + 7)

        for i in range(self.table.rowCount()):
            if i >= 6:
                self.table.setVerticalHeaderItem(i, QTableWidgetItem(str(i-5)))
            else:
                self.table.setVerticalHeaderItem(i, QTableWidgetItem(""))
        for i in range(self.table.columnCount()):
            if i >= 7:
                self.table.setHorizontalHeaderItem(i, QTableWidgetItem(str(i-6)))
            else:
                self.table.setHorizontalHeaderItem(i, QTableWidgetItem(""))

        self.init_fill()

        layout.addWidget(QLabel("Enter Causes & Effects, then fill in intersection Ops in the matrix:"))
        layout.addWidget(self.table)

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        self.output= QTextEdit()
        self.output.setReadOnly(True)
        self.output.setEnabled(False)
        self.output.hide()

        layout.addWidget(QPushButton("Generate XML",clicked=self.generate_xml))

        self.close_xml_window_button = QPushButton("Close XML Window", clicked=self.close_xml_window)
        self.close_xml_window_button.hide()
        layout.addWidget(self.close_xml_window_button)

        self.open_xml_window_button = QPushButton("Open XML Window", clicked=self.open_xml_window)
        self.open_xml_window_button.hide()
        layout.addWidget(self.open_xml_window_button)

        self.copy_to_clipboard_button = QPushButton("Copy XML to Clipboard", clicked=self.copy_to_clipboard)
        self.copy_to_clipboard_button.hide()
        layout.addWidget(self.copy_to_clipboard_button)

        layout.addWidget(QLabel("Generated XML:"))
        layout.addWidget(self.output)

        self.save_button = QPushButton("Save XML to file",clicked=self.save_xml_to_file)
        self.save_button.setEnabled(False)
        layout.addWidget(self.save_button)

        layout.addWidget(QPushButton("Load XML from file",clicked=self.load_xml_from_file))

        layout.addWidget(QLabel("Info field:"))
        self.info_field = QTextEdit()
        self.info_field.setMinimumHeight(50)
        self.info_field.setMaximumHeight(100)
        self.info_field.setReadOnly(True)
        layout.addWidget(self.info_field)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.load_resources()

    

    def generate_xml(self):
        causes = []
        effects = []
        matrix = []

        for row in range(6, 6 + NUM_CAUSES):
            values = [self.get_cell(row,col) for col in range(7)]
            if any(values) and values[0]:
                causes.append({
                    "name": values[0],
                    "input1": values[1],
                    "input1_type": values[2],
                    "input2": values[3],
                    "input2_type": values[4],
                    "op": values[5],
                    "description": values[6]
            })

        for col in range(7, 7 + NUM_EFFECTS):
            values = [self.get_cell(row,col) for row in range(6)]
            if any(values) and values[0]:
                effects.append({
                    "name": values[0],
                    "output": values[1],
                    "output_type": values[2],
                    "op": values[3],
                    "opt_timer_value": values[4],
                    "description": values[5]
                })

        for i, cause in enumerate(causes):
            for j, effect in enumerate(effects):
                op = self.get_cell(i+ 6, j + 7)
                if op:
                    matrix.append({
                        "cause": cause["name"],
                        "effect": effect["name"],
                        "op": op
                    })

        cem = Element("CEM")

        for cause in causes:
            if cause["description"]:
                c = SubElement(
                cem,"Cause", 
                Name=cause["name"],
                Op=cause["op"],
                Description=cause["description"])
            else:
                c = SubElement(
                    cem,"Cause", 
                    Name=cause["name"],
                    Op=cause["op"])
            inputs = SubElement(c,"Inputs")
            if cause["input1"]:
                if cause["input1_type"] == "ConstantBool":
                    SubElement(inputs, "Constant", Type="Bool", Value=cause["input1"])
                elif cause["input1_type"] == "ConstantInt":
                    SubElement(inputs, "Constant", Type="Int", Value=cause["input1"])
                else:
                    SubElement(inputs,"InSignal", 
                    Name=cause["input1"],
                    Type=cause["input1_type"])
            if cause["input2"]:
                if cause["input2_type"] == "ConstantBool":
                    SubElement(inputs, "Constant", Type="Bool", Value=cause["input2"])
                elif cause["input2_type"] == "ConstantInt":
                    SubElement(inputs, "Constant", Type="Int", Value=cause["input2"])
                else:
                    SubElement(inputs,"InSignal", 
                    Name=cause["input2"],
                    Type=cause["input2_type"])

        for effect in effects:
            if effect["description"] != "":
                e = SubElement(
                    cem,"Effect", 
                    Name=effect["name"],
                    Op=effect["op"],
                    Description=effect["description"])
            else:
                e = SubElement(
                    cem,"Effect", 
                    Name=effect["name"],
                    Op=effect["op"])
            if ((effect["op"] == "TOf") or (effect["op"] == "TOn") or (effect["op"] == "TP")):
                SubElement(e, "Timer",
                           Type=effect["op"],
                           Value=effect["opt_timer_value"])
            SubElement(
                e,"OutSignal", 
                Name=effect["output"],
                Type=effect["output_type"])

        for inter in matrix:
            SubElement(
                cem,"Intersection", 
                CauseRef=inter["cause"],
                EffectRef=inter["effect"],
                Op=inter["op"])

        self.xml_with_version = minidom.parseString(tostring(cem)).toprettyxml(indent="  ")
        self.pretty_xml = "\n".join(self.xml_with_version.split("\n")[1:]).strip()
        self.output.setPlainText(self.pretty_xml)
        self.output.setEnabled(True)
        self.output.show()
        self.save_button.setEnabled(True)
        self.close_xml_window_button.show()
        self.copy_to_clipboard_button.show()
        self.open_xml_window_button.hide()
        self.report_errors_from_jar()

    def get_cell(self, row, col):
        widget = self.table.cellWidget(row,col)
        if widget and isinstance(widget, QComboBox):
                return widget.currentText()
        item = self.table.item(row,col)
        return item.text().strip() if item else ""
    
    def save_xml_to_file(self):
            if hasattr(self, 'pretty_xml'):
                options = QFileDialog.Options()
                file_name, _ = QFileDialog.getSaveFileName(self, "Save XML File", "", "XML Files (*.xml);; All Files (*)", options=options)
                if file_name:
                    with open (file_name, 'w') as f:
                        f.write(self.pretty_xml)

    def load_xml_from_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self,"Open XML File", "", "XML Files (*.xml);; All Files (*)")
        if file_name:
            tree = parse(file_name)
            root = tree.getroot()
            self.table.clearContents()
            self.init_fill()

            for i, cause in enumerate(root.findall("Cause")):
                self.table.item(6 + i, 0).setText(cause.attrib.get("Name", ""))
                self.table.cellWidget(6 + i, 5).setCurrentText(cause.attrib.get("Op", ""))
                self.table.item(6 + i, 6).setText(cause.attrib.get("Description", ""))
                inputs = cause.find("Inputs")
                if inputs is not None:
                    insignals = inputs.findall("InSignal")
                    constants = inputs.findall("Constant")
                    if (len(insignals) > 0):
                        self.table.item(6+i, 1).setText(insignals[0].attrib.get("Name",""))
                        self.table.cellWidget(6+i, 2).setCurrentText(insignals[0].attrib.get("Type",""))
                    if (len(insignals) > 1):
                        self.table.item(6+i, 3).setText(insignals[1].attrib.get("Name",""))
                        self.table.cellWidget(6+i, 4).setCurrentText(insignals[1].attrib.get("Type",""))
                    if (len(constants) > 0):
                        self.table.item(6+i, 3).setText(constants[0].attrib.get("Value",""))
                        self.table.cellWidget(6+i, 4).setCurrentText("Constant"+constants[0].attrib.get("Type",""))

            for i, effect in enumerate(root.findall("Effect")):
                self.table.item(0, 7 + i).setText(effect.attrib.get("Name", ""))
                outsignal = effect.find("OutSignal")
                if outsignal is not None:
                    self.table.item(1, 7 + i).setText(outsignal.attrib.get("Name", ""))
                    self.table.cellWidget(2, 7 + i).setCurrentText(outsignal.attrib.get("Type", ""))
                timer = effect.find("Timer")
                if timer is not None:
                    self.table.cellWidget(3, 7 + i).setCurrentText(timer.attrib.get("Type", ""))
                    self.table.item(4, 7 + i).setText(timer.attrib.get("Value", ""))
                else:
                    self.table.cellWidget(3, 7 + i).setCurrentText(effect.attrib.get("Op", ""))
                self.table.item(5, 7 + i).setText(effect.attrib.get("Description", ""))
            
            for intersect in root.findall("Intersection"):
                cause_name = intersect.attrib.get("CauseRef","")
                effect_name = intersect.attrib.get("EffectRef","")
                cause_i = -1
                effect_i = -1
                for i in range(6, NUM_CAUSES):
                    if self.table.item(i,0).text() == cause_name:
                        cause_i = i
                for i in range (7, NUM_EFFECTS):
                    if self.table.item(0,i).text() == effect_name:
                        effect_i = i
                op = intersect.attrib.get("Op","")
                self.table.item(cause_i, effect_i).setText(op)
                


    def close_xml_window(self):
        self.output.hide()
        self.open_xml_window_button.show()
        self.close_xml_window_button.hide()
        self.copy_to_clipboard_button.hide()

    def open_xml_window(self):
        self.output.show()
        self.open_xml_window_button.hide()
        self.close_xml_window_button.show()
        self.copy_to_clipboard_button.show()
    
    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.pretty_xml)
        self.info_field.setPlainText("Copied XML to Clipboard!")

    def load_resources(self):
        with open("donttouch\\hardcoded_app_beginning.txt", 'r', encoding='utf-8') as file:
            self.hardcoded_app_beginning = file.read()
        with open("donttouch\\hardcoded_app_end.txt", 'r', encoding='utf-8') as file:
            self.hardcoded_app_end = file.read()

    def report_errors_from_jar(self):
        app = f"{self.hardcoded_app_beginning}{self.pretty_xml}{self.hardcoded_app_end}"
        with open("donttouch\\Test\\Input\\Application_1.app", 'w', encoding='utf-8') as file:
            file.write(app)
        result = subp.run(["java", "-jar", "AppCompiler.jar", "-build", "donttouch\\Test\\Input", "-targetdir", "donttouch\\Test\\Output"], capture_output=True, text=True)
        self.info_field.setPlainText(result.stderr)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

"""
TODO:
Add dropdown menus for types: Bool, Int, ConstantBool, ConstantInt                  DONE
Add dropdown menus for ops: .....                                                   DONE
Add dropdown menus for intersections: .....                                         DONE
Make matrix descriptions lignup.                                                    DONE
Make cell size autoadjust.                                                          DONE
Adjur Numbers of table to start where effects and causes start.                     DONE
Save file.                                                                          DONE
Open/Close XML Window                                                               DONE
Make Errorfield un-editable                                                         DONE
Scrolling changes drop-down options: solved by removing interseciton-drop-downs     DONE
Change Errorfield to Infofield                                                      DONE
Add a copy-to-clipboard function/button                                             DONE
Add another row for timer values                                                    DONE
Read from file.                                                                     DONE
Generate FunctionBlock.                 Dont Think this is needed?                  DONE
Get Compiler Feedback - Errors/Warnings                                             DONE
Change code to not replace table objects but just the text                          DONE
Implement cell/row/collumn-highlighting                                             OutOfScope
Fix Info Field Size                                                                 
"""