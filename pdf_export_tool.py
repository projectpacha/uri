import sys
import os
import csv
import json
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QTextEdit, QVBoxLayout, QWidget, QMessageBox,
    QDialog, QDialogButtonBox, QLabel, QHBoxLayout, QFormLayout, QFontComboBox, QColorDialog, QCheckBox,
    QComboBox, QSpinBox, QAction, QPushButton, QToolBar, QWidgetAction, QLineEdit
)
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtGui import QTextDocument, QFont, QIcon
from PyQt5.QtCore import QCoreApplication

logging.basicConfig(level=logging.DEBUG)


def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def load_settings():
    settings_file = "settings.json"
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error("Failed to load settings.json: " + str(e))
    return {
        "language": "en",
        "theme": "themes/default_style.qss"
    }


class CoverPageOptionsEditor(QDialog):
    def __init__(self, current_options=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Edit Info"))
        self.resize(400, 300)
        layout = QFormLayout(self)
        
        self.titleEdit = QLineEdit()
        self.subtitleEdit = QLineEdit()
        self.authorEdit = QLineEdit()
        self.yearEdit = QLineEdit()
        self.copyrightEdit = QLineEdit()
        
        if current_options:
            self.titleEdit.setText(current_options.get("title", ""))
            self.subtitleEdit.setText(current_options.get("subtitle", ""))
            self.authorEdit.setText(current_options.get("author", ""))
            self.yearEdit.setText(current_options.get("year", ""))
            self.copyrightEdit.setText(current_options.get("copyright", ""))
        
        layout.addRow(self.tr("Title") + ":", self.titleEdit)
        layout.addRow(self.tr("Subtitle") + ":", self.subtitleEdit)
        layout.addRow(self.tr("Author") + ":", self.authorEdit)
        layout.addRow(self.tr("Year") + ":", self.yearEdit)
        layout.addRow(self.tr("Copyright") + ":", self.copyrightEdit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def getOptions(self):
        return {
            "title": self.titleEdit.text(),
            "subtitle": self.subtitleEdit.text(),
            "author": self.authorEdit.text(),
            "year": self.yearEdit.text(),
            "copyright": self.copyrightEdit.text()
        }



class CoverPageCustomizer(QDialog):
    def __init__(self, current_style, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Customize Front Info Style"))
        self.resize(400, 300)
        self.current_style = current_style.copy()
        self.current_style.setdefault("margin", 50)
        self.current_style.setdefault("padding", 20)
        self.current_style.setdefault("page_break", True)
        layout = QVBoxLayout(self)
        # Font chooser
        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(QLabel(self.tr("Font") + ":"))
        self.fontCombo = QFontComboBox()
        self.fontCombo.setCurrentFont(self.current_style["font"])
        hlayout1.addWidget(self.fontCombo)
        layout.addLayout(hlayout1)
        # Font size chooser
        hlayout1b = QHBoxLayout()
        hlayout1b.addWidget(QLabel(self.tr("Font Size") + ":"))
        self.sizeSpin = QSpinBox()
        self.sizeSpin.setRange(6, 72)
        self.sizeSpin.setValue(self.current_style["font"].pointSize())
        hlayout1b.addWidget(self.sizeSpin)
        layout.addLayout(hlayout1b)
        # Text color chooser
        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(QLabel(self.tr("Text Color") + ":"))
        self.textColorButton = QPushButton(self.tr("Choose"))
        self.textColorButton.setStyleSheet(f"background-color: {self.current_style['text_color']}")
        self.textColorButton.clicked.connect(self.choose_text_color)
        hlayout2.addWidget(self.textColorButton)
        layout.addLayout(hlayout2)
        # Alignment chooser
        hlayout4 = QHBoxLayout()
        hlayout4.addWidget(QLabel(self.tr("Alignment") + ":"))
        self.alignmentCombo = QComboBox()
        self.alignmentCombo.addItems([
            self.tr("center"),
            self.tr("left"),
            self.tr("right")
        ])
        index = self.alignmentCombo.findText(self.current_style["alignment"])
        if index >= 0:
            self.alignmentCombo.setCurrentIndex(index)
        hlayout4.addWidget(self.alignmentCombo)
        layout.addLayout(hlayout4)
        # Margin chooser
        hlayout5 = QHBoxLayout()
        hlayout5.addWidget(QLabel(self.tr("Margin") + " (px):"))
        self.marginSpin = QSpinBox()
        self.marginSpin.setRange(0, 200)
        self.marginSpin.setValue(self.current_style["margin"])
        hlayout5.addWidget(self.marginSpin)
        layout.addLayout(hlayout5)
        # Padding chooser
        hlayout6 = QHBoxLayout()
        hlayout6.addWidget(QLabel(self.tr("Padding") + " (px):"))
        self.paddingSpin = QSpinBox()
        self.paddingSpin.setRange(0, 200)
        self.paddingSpin.setValue(self.current_style["padding"])
        hlayout6.addWidget(self.paddingSpin)
        layout.addLayout(hlayout6)
        # Page break option
        self.pageBreakCheck = QCheckBox(self.tr("Insert page break after cover page"))
        self.pageBreakCheck.setChecked(self.current_style["page_break"])
        layout.addWidget(self.pageBreakCheck)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_text_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            self.current_style["text_color"] = hex_color
            self.textColorButton.setStyleSheet(f"background-color: {hex_color}")

    def getStyle(self):
        font = QFont(self.fontCombo.currentFont())
        font.setPointSize(self.sizeSpin.value())
        self.current_style["font"] = font
        self.current_style["alignment"] = self.alignmentCombo.currentText()
        self.current_style["margin"] = self.marginSpin.value()
        self.current_style["padding"] = self.paddingSpin.value()
        self.current_style["page_break"] = self.pageBreakCheck.isChecked()
        return self.current_style


class FontCustomizationDialog(QDialog):
    def __init__(self, current_fonts, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Customize Entry Fonts"))
        self.fields = {}
        self.current_fonts = current_fonts
        layout = QVBoxLayout(self)

        labels = {
            "headword": self.tr("Headword"),
            "variation": self.tr("Variation"),
            "part_of_speech": self.tr("Part of Speech"),
            "notes": self.tr("Notes"),
            "meanings": self.tr("Meaning")
        }

        for field in labels:
            row_layout = QHBoxLayout()
            label = QLabel(labels[field] + ":")
            row_layout.addWidget(label)

            fontCombo = QFontComboBox()
            if field in current_fonts:
                fontCombo.setCurrentFont(current_fonts[field]["font"])
            row_layout.addWidget(fontCombo)

            sizeSpin = QSpinBox()
            sizeSpin.setRange(6, 72)
            if field in current_fonts:
                sizeSpin.setValue(current_fonts[field]["font"].pointSize())
            else:
                sizeSpin.setValue(12)
            row_layout.addWidget(QLabel(self.tr("Size") + ":"))
            row_layout.addWidget(sizeSpin)

            colorButton = QPushButton(self.tr("Choose Color"))
            initial_color = current_fonts[field]["color"] if field in current_fonts else "#000000"
            colorButton.setStyleSheet(f"background-color: {initial_color}")
            colorButton.clicked.connect(lambda checked, f=field: self.chooseColor(f))
            row_layout.addWidget(colorButton)

            boldCheck = QCheckBox(self.tr("Bold"))
            if field in current_fonts and current_fonts[field]["font"].bold():
                boldCheck.setChecked(True)
            row_layout.addWidget(boldCheck)

            italicCheck = QCheckBox(self.tr("Italic"))
            if field in current_fonts and current_fonts[field]["font"].italic():
                italicCheck.setChecked(True)
            row_layout.addWidget(italicCheck)

            self.fields[field] = {
                "fontCombo": fontCombo,
                "sizeSpin": sizeSpin,
                "color": initial_color,
                "bold": boldCheck,
                "italic": italicCheck,
                "colorButton": colorButton,
            }
            layout.addLayout(row_layout)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    def chooseColor(self, field):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            self.fields[field]["color"] = hex_color
            self.fields[field]["colorButton"].setStyleSheet(f"background-color: {hex_color}")



class PDFExporter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.setWindowTitle(self.tr("PDF Exporter"))
        self.setGeometry(100, 100, 800, 600)
        self.data = []  

        self.fonts = {
            "headword": {"font": QFont("Arial", 14, QFont.Bold), "color": "#000000"},
            "variation": {"font": QFont("Arial", 12), "color": "#000000"},
            "part_of_speech": {"font": QFont("Arial", 12), "color": "#000000"},
            "notes": {"font": QFont("Arial", 12), "color": "#000000"},
            "meanings": {"font": QFont("Arial", 12), "color": "#000000"},
        }

        self.coverPageStyle = {
            "font": QFont("Times New Roman", 24, QFont.Bold),
            "text_color": "#000000",
            "background_color": "#ffffff",
            "alignment": "center",
            "margin": 50,
            "padding": 20,
            "page_break": True,
        }
        self.coverPageOptions = {
            "title": "",
            "subtitle": "",
            "author": "",
            "year": "",
            "copyright": ""
        }
        self.currentLayout = "Standard" 

        self.textEdit = QTextEdit()
        self.textEdit.setReadOnly(True)
        self.setCentralWidget(self.textEdit)

        self.create_menubar()

    def create_menubar(self):
        menubar = self.menuBar()
        # File menu.
        fileMenu = menubar.addMenu(self.tr("File"))
        loadCSVAction = QAction(self.tr("Load CSV"), self)
        loadCSVAction.triggered.connect(self.load_csv)
        fileMenu.addAction(loadCSVAction)
        loadJSONAction = QAction(self.tr("Load JSON"), self)
        loadJSONAction.triggered.connect(self.load_json)
        fileMenu.addAction(loadJSONAction)
        exportPDFAction = QAction(self.tr("Export PDF"), self)
        exportPDFAction.triggered.connect(self.export_pdf)
        fileMenu.addAction(exportPDFAction)
        # Edit menu.
        editMenu = menubar.addMenu(self.tr("Edit"))
        customizeFontsAction = QAction(self.tr("Customize Entry Fonts"), self)
        customizeFontsAction.triggered.connect(self.customize_fonts)
        editMenu.addAction(customizeFontsAction)
        editCoverOptionsAction = QAction(self.tr("Edit Info Page Options"), self)
        editCoverOptionsAction.triggered.connect(self.edit_cover_page_options)
        editMenu.addAction(editCoverOptionsAction)
        customizeCoverAction = QAction(self.tr("Customize Info Page Style"), self)
        customizeCoverAction.triggered.connect(self.customize_cover_page)
        editMenu.addAction(customizeCoverAction)
        # Layout menu.
        layoutMenu = menubar.addMenu(self.tr("Layout"))
        standardLayoutAction = QAction(self.tr("Standard Layout"), self)
        standardLayoutAction.triggered.connect(lambda: self.set_layout("Standard"))
        layoutMenu.addAction(standardLayoutAction)
        twoColumnLayoutAction = QAction(self.tr("Two Column Layout"), self)
        twoColumnLayoutAction.triggered.connect(lambda: self.set_layout("Two Column"))
        layoutMenu.addAction(twoColumnLayoutAction)

    def edit_cover_page_options(self):
        dialog = CoverPageOptionsEditor(self.coverPageOptions, self)
        if dialog.exec_() == QDialog.Accepted:
            self.coverPageOptions = dialog.getOptions()
            self.display_data()

    def set_layout(self, layout_choice):
        self.currentLayout = layout_choice
        self.display_data()

    def load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Open CSV"), "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                self.data = []
                for row in reader:
                    try:
                        row['id'] = int(row['id'])
                    except (ValueError, KeyError):
                        pass
                    meanings = row.get('meanings', '')
                    if meanings:
                        row['meanings'] = [m.strip() for m in meanings.split(";;") if m.strip()]
                    else:
                        row['meanings'] = []
                    self.data.append(row)
            self.display_data()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"),
                                 self.tr("Failed to load CSV:") + " " + str(e))

    def load_json(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Open JSON"), "", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as file:
                self.data = json.load(file)
            self.display_data()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"),
                                 self.tr("Failed to load JSON:") + " " + str(e))

    def generate_css(self):
        css = "<style>\n"
        css += "body { font-family: Arial, sans-serif; margin: 0; }\n"  # Remove body margin
        cover_font = self.coverPageStyle["font"]
        cover_text_color = self.coverPageStyle["text_color"]
        cover_bg_color = self.coverPageStyle["background_color"]
        cover_alignment = self.coverPageStyle["alignment"]
        margin = self.coverPageStyle["margin"]
        padding = self.coverPageStyle["padding"]
        css += (
            f".cover {{ font-family: '{cover_font.family()}'; font-size: {cover_font.pointSize()}pt; "
            f"color: {cover_text_color}; background-color: {cover_bg_color}; text-align: {cover_alignment}; "
            f"margin: 0; padding: {padding}px; min-height: 100vh; }}\n"  
        )
        css += ".cover h1 { font-size: 50pt; margin-bottom: 10pt; margin-top: 20pt}\n"
        css += ".cover h2 { font-size: 48pt; margin-bottom: 10pt; }\n"
        css += ".cover p { font-size: 16pt; margin-bottom: 10pt; }\n"
        for field in ["headword", "variation", "part_of_speech", "notes", "meanings"]:
            font = self.fonts[field]["font"]
            color = self.fonts[field]["color"]
            css += (
                f".{field} {{\n"
                f"  font-family: '{font.family()}' !important;\n"
                f"  font-size: {font.pointSize()}pt !important;\n"
                f"  color: {color} !important;\n"
                f"  font-weight: {'bold' if font.bold() else 'normal'} !important;\n"
                f"  font-style: {'italic' if font.italic() else 'normal'} !important;\n"
                "}\n"
            )
        css += ".entry { margin-bottom: 5px; }\n"
        css += ".entry p { margin: 4px 0; }\n"
        css += "</style>\n"
        return css

    def generate_entry_html(self, entry):
        entry_html = '<div class="entry">'
        entry_html += f"<h2 class='headword'>{entry.get('headword', '')}</h2>"
        entry_html += (
            f"<p class='variation'><strong>{self.tr('Variation')}: </strong>{entry.get('variation', '')}</p>"
        )
        entry_html += (
            f"<p class='part_of_speech'><strong>{self.tr('Part of Speech')}: </strong>{entry.get('part_of_speech', '')}</p>"
        )
        entry_html += (
            f"<p class='notes'><strong>{self.tr('Notes')}: </strong>{entry.get('notes', '')}</p>"
        )
        meanings = entry.get('meanings', [])
        if meanings:
            entry_html += (
                f"<p class='meanings'><strong>{self.tr('Meaning')}: </strong>{', '.join(meanings)}</p>"
            )
        entry_html += "</div>"
        return entry_html

    def display_data(self):
        html = "<html><head>" + self.generate_css() + "</head><body>"
        if self.coverPageOptions.get("title"):
            html += "<div class='cover'>"
            html += f"<h1>{self.coverPageOptions.get('title')}</h1>"
            if self.coverPageOptions.get("subtitle"):
                html += f"<h2>{self.coverPageOptions.get('subtitle')}</h2>"
            if self.coverPageOptions.get("author") or self.coverPageOptions.get("year"):
                html += "<p>"
                if self.coverPageOptions.get("author"):
                    html += f"{self.coverPageOptions.get('author')}"
                if self.coverPageOptions.get("year"):
                    html += f" ({self.coverPageOptions.get('year')})"
                html += "</p>"
            if self.coverPageOptions.get("copyright"):
                html += f"<p>{self.coverPageOptions.get('copyright')}</p>"
            html += "</div></div>"
            if self.coverPageStyle.get("page_break", True):
                html += "<p style='page-break-after: always;'></p>"
        if self.currentLayout == "Two Column":
            html += "<div style='page-break-before: always;'>"
            html += "<table style='width:100%; border-collapse: collapse;'><tr>"
            half = (len(self.data) + 1) // 2
            col1 = self.data[:half]
            col2 = self.data[half:]
            html += "<td style='vertical-align: top; width:50%; padding: 10px;'>"
            for entry in col1:
                html += self.generate_entry_html(entry)
            html += "</td>"
            html += "<td style='vertical-align: top; width:50%; border-left: 1px solid #000; padding: 10px;'>"
            for entry in col2:
                html += self.generate_entry_html(entry)
            html += "</td></tr></table>"
        else:
            for entry in self.data:
                html += self.generate_entry_html(entry)
        html += "</body></html>"
        self.textEdit.setHtml(html)

    def customize_fonts(self):
        dialog = FontCustomizationDialog(self.fonts, self)
        if dialog.exec_() == QDialog.Accepted:
            for field, controls in dialog.fields.items():
                font = QFont(controls["fontCombo"].currentFont())
                font.setPointSize(controls["sizeSpin"].value())
                font.setBold(controls["bold"].isChecked())
                font.setItalic(controls["italic"].isChecked())
                self.fonts[field] = {"font": font, "color": controls["color"]}
            self.display_data()

    def customize_cover_page(self):
        dialog = CoverPageCustomizer(self.coverPageStyle, self)
        if dialog.exec_() == QDialog.Accepted:
            self.coverPageStyle = dialog.getStyle()
            self.display_data()

    def export_pdf(self):
        if not self.data:
            QMessageBox.warning(self, self.tr("No Data"),
                                self.tr("Please load CSV or JSON data first."))
            return
        file_path, _ = QFileDialog.getSaveFileName(self, self.tr("Save PDF"), "*.pdf", "PDF Files (*.pdf)")
        if not file_path:
            return
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(file_path)
        doc = QTextDocument()
        doc.setHtml(self.textEdit.toHtml())
        doc.print_(printer)
        QMessageBox.information(self, self.tr("Export Complete"),
                                self.tr("PDF exported successfully to:") + "\n" + file_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFExporter()
    window.show()
    sys.exit(app.exec_())