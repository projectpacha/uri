import sys, os, logging, difflib, json, math, datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QListWidget, QProgressDialog, 
    QPushButton, QMessageBox, QFileDialog, QInputDialog, QMenuBar, QMenu, QStatusBar, QFrame, QShortcut, QListWidgetItem,  QSplitter, QComboBox, QCheckBox, QToolBar, QAction, QUndoStack)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QEvent, QTimer, QSize, QTranslator, QSettings, QLibraryInfo
from settings import load_settings, save_settings
from database import DatabaseManager
from import_export import ImportExportManager
from duplicates import DuplicatesWindow
from dict_help import DictionaryAidWindow
from undo_commands import UpdateEntryCommand, DeleteEntryCommand
from pdf_export_tool import PDFExporter 

MAX_RECENT_FILES = 5
SETTINGS_ORG = "Uri"
SETTINGS_APP = "DictMaker"

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class DictionaryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self.setWindowIcon(QIcon(resource_path("icons/app_icon.png")))
        global window
        window = self
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.current_language = "en"
        self.current_theme = "themes/default_style.qss"
        self.current_entry_id = None
        self.undoStack = QUndoStack(self)
        self.undoStack.indexChanged.connect(self.refresh_headwords_panel)
        self.db_manager = DatabaseManager(self.update_status)
        self.import_export_manager = ImportExportManager(self.db_manager, self.update_status)
        self.duplicates_window = None
        self.initUI()
        settings = load_settings()
        self.base_font_size = self.font().pointSize()
        self.zoom_offset = 0
        self.change_theme(settings.get("theme", "themes/default_style.qss"))
        self.change_language(settings.get("language", "en"))
        interval = settings.get("autosave_interval", 30)
        if interval < 30:
            interval = 30
        elif interval > 300:
            interval = 300
        self.autosave_interval = interval

        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave)
        self.autosave_timer.start(self.autosave_interval * 1000)

    def initUI(self):
        self.setWindowTitle(self.tr("Uri DictMaker"))
        self.setGeometry(100, 100, 1280, 800)
        # Menu system
        menubar = self.menuBar()
        self.file_menu = menubar.addMenu(self.tr("File"))
        self.recent_menu = QMenu(self.tr("Open Recent"), self)
        self.file_menu.addMenu(self.recent_menu)
        self.update_recent_menu()
        self.new_db_action = self.file_menu.addAction(self.tr("New Database"), self.create_database)
        self.open_db_action = self.file_menu.addAction(self.tr("Open Database"), self.load_database)
        self.file_menu.addSeparator()
        self.import_csv_action = self.file_menu.addAction(self.tr("Import CSV"), self.import_csv)
        self.export_csv_action = self.file_menu.addAction(self.tr("Export CSV"), self.export_csv)
        self.import_json_action = self.file_menu.addAction(self.tr("Import JSON"), self.import_json)
        self.export_json_action = self.file_menu.addAction(self.tr("Export JSON"), self.export_json)
        self.export_pdf_action = self.file_menu.addAction(self.tr("Publish PDF"), self.export_pdf)
        self.file_menu.addSeparator()
        self.exit_action = self.file_menu.addAction(self.tr("Exit"), self.exit_app)
        self.edit_menu = menubar.addMenu(self.tr("Edit"))
        self.undo_action = self.edit_menu.addAction(self.tr("Undo"), self.undoStack.undo)
        self.redo_action = self.edit_menu.addAction(self.tr("Redo"), self.undoStack.redo)
        self.copy_action = self.edit_menu.addAction(self.tr("Copy"), self.copy_text)
        self.cut_action = self.edit_menu.addAction(self.tr("Cut"), self.cut_text)
        self.paste_action = self.edit_menu.addAction(self.tr("Paste"), self.paste_text)
        self.file_menu.addSeparator()
        self.show_duplicates_action = self.edit_menu.addAction(self.tr("Show Duplicates"), self.show_duplicates)
        self.view_menu = menubar.addMenu(self.tr("View"))
        self.left_panel_action = self.view_menu.addAction(self.tr("Toggle left panel"), self.toggle_left_panel)
        self.right_panel_action = self.view_menu.addAction(self.tr("Toggle right panel"), self.toggle_right_panel)
        self.status_bar_action = self.view_menu.addAction(self.tr("Toggle status bar"), self.toggle_status_bar)
        self.view_menu.addSeparator()
        self.fullscreen_action = self.view_menu.addAction(self.tr("Fullscreen"), self.toggle_fullscreen)
        self.tools_menu = menubar.addMenu(self.tr("Tools"))
        self.dictionary_help_action = self.tools_menu.addAction(self.tr("Help with Dictionary making"), self.show_dictionary_aid)
        self.file_menu.addSeparator()
        self.database_stats_action = self.tools_menu.addAction(self.tr("Database Statistics"), self.show_db_statistics)
        self.preferences_menu = menubar.addMenu(self.tr("Preferences"))
        self.theme_menu = self.preferences_menu.addMenu(self.tr("Theme"))
        self.dark_theme_action = self.theme_menu.addAction(self.tr("Dark"), lambda: self.change_theme("themes/style_dark.qss"))
        self.material_theme_action = self.theme_menu.addAction(self.tr("Material"), lambda: self.change_theme("themes/material_style.qss"))
        self.default_theme_action = self.theme_menu.addAction(self.tr("Default"), lambda: self.change_theme("themes/default_style.qss"))
        self.language_menu = self.preferences_menu.addMenu(self.tr("Language"))
        self.arabic_action = self.language_menu.addAction(self.tr("Arabic"), lambda: self.change_language("ar"))
        self.english_action = self.language_menu.addAction(self.tr("English"), lambda: self.change_language("en"))
        self.french_action = self.language_menu.addAction(self.tr("French"), lambda: self.change_language("fr"))
        self.german_action = self.language_menu.addAction(self.tr("German"), lambda: self.change_language("de"))
        self.kannada_action = self.language_menu.addAction(self.tr("Kannada"), lambda: self.change_language("kn"))
        self.malayalam_action = self.language_menu.addAction(self.tr("Malayalam"), lambda: self.change_language("ml"))
        self.rajasthani_action = self.language_menu.addAction(self.tr("Rajasthani"), lambda: self.change_language("mrw"))
        self.telugu_action = self.language_menu.addAction(self.tr("Telugu"), lambda: self.change_language("te"))
        self.autosave_interval_action = self.preferences_menu.addAction(self.tr("Set Autosave Interval"), self.set_autosave_interval)
        self.help_menu = menubar.addMenu(self.tr("Help"))
        self.keyboard_shortcuts_action = self.help_menu.addAction(self.tr("Keyboard Shortcuts"), self.show_help)
        self.about_action = self.help_menu.addAction(self.tr("About"), self.show_about)
        self.toolbar = QToolBar(self.tr("Main Toolbar"))
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        
        # Toolbar actions
        save_action = QAction(QIcon(resource_path("icons/save.svg")),
                              self.tr("Save entry, Ctrl+S"), self)
        save_action.triggered.connect(self.save_entry)
        self.toolbar.addAction(save_action)
        self.toolbar.addSeparator()
        new_action = QAction(QIcon(resource_path("icons/file-plus.svg")),
                             self.tr("New entry, Ctrl+N"), self)
        new_action.triggered.connect(self.clear_fields)
        self.toolbar.addAction(new_action)
        self.toolbar.addSeparator()
        delete_action = QAction(QIcon(resource_path("icons/delete.svg")),
                                self.tr("Delete entry, Ctrl+D"), self)
        delete_action.triggered.connect(self.delete_entry)
        self.toolbar.addAction(delete_action)
        self.toolbar.addSeparator()
        duplicates_action = QAction(QIcon(resource_path("icons/duplicate.svg")),
                                    self.tr("Check for duplicate entries"), self)
        duplicates_action.triggered.connect(self.show_duplicates)
        self.toolbar.addAction(duplicates_action)
        self.toolbar.addSeparator()
        undo_action = QAction(QIcon(resource_path("icons/undo.svg")),
                              self.tr("Undo, Ctrl+Z"), self)
        undo_action.triggered.connect(self.undoStack.undo)
        self.toolbar.addAction(undo_action)
        self.toolbar.addSeparator()
        redo_action = QAction(QIcon(resource_path("icons/redo.svg")),
                              self.tr("Redo, Ctrl+Y"), self)
        redo_action.triggered.connect(self.undoStack.redo)
        self.toolbar.addAction(redo_action)
        self.toolbar.addSeparator()

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Search bar
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        self.search_label = QLabel(self.tr("Search:"))
        search_layout.addWidget(self.search_label)
        self.entry_search = QLineEdit()
        self.entry_search.returnPressed.connect(self.search_filter)  
        self.entry_search.setToolTip(self.tr("Enter search term"))
        search_layout.addWidget(self.entry_search)
        self.search_criteria_combo = QComboBox()
        self.search_criteria_combo.addItems([
            self.tr("All"),
            self.tr("Headword"),
            self.tr("Part of Speech"),
            self.tr("Variation"),
            self.tr("Meaning"),
        ])
        self.search_criteria_combo.setToolTip(self.tr("Select search criteria"))
        search_layout.addWidget(self.search_criteria_combo)
        self.fuzzy_search_checkbox = QCheckBox(self.tr("Fuzzy Search"))
        self.fuzzy_search_checkbox.setToolTip(self.tr("Check for approximate matches"))
        search_layout.addWidget(self.fuzzy_search_checkbox)
        self.search_button = QPushButton("")
        self.search_button.setIcon(QIcon(resource_path("icons/search.svg")))
        self.search_button.clicked.connect(self.search_filter)
        search_layout.addWidget(self.search_button)
        main_layout.addWidget(search_frame)

        # Content area
        content_frame = QFrame()
        content_layout = QHBoxLayout(content_frame)
        splitter = QSplitter(Qt.Horizontal)

        # Left Panel
        list_frame = QFrame()
        list_layout = QVBoxLayout(list_frame)
        self.alphabet_combo = QComboBox()
        self.alphabet_combo.setToolTip(self.tr("Filter by first letter"))
        self.alphabet_combo = QComboBox()
        self.alphabet_combo.setToolTip(self.tr("Filter by first letter"))
        self.alphabet_combo.currentIndexChanged.connect(self.filter_by_alphabet)
        list_layout.addWidget(self.alphabet_combo)
        self.entries_label = QLabel(self.tr("Entries"))
        list_layout.addWidget(self.entries_label)
        self.listbox_headwords = QListWidget()
        self.listbox_headwords.setFocusPolicy(Qt.StrongFocus)  
        self.listbox_headwords.itemClicked.connect(self.display_entry)
        list_layout.addWidget(self.listbox_headwords)
        splitter.addWidget(list_frame)
        self.listbox_headwords.setSelectionMode(QListWidget.ExtendedSelection)
        self.listbox_headwords.itemClicked.connect(self.display_entry)
        list_layout.addWidget(self.listbox_headwords)
        splitter.addWidget(list_frame)

        # Right Panel
        form_frame = QFrame()
        form_layout = QVBoxLayout(form_frame)
        self.id_label = QLabel()
        form_layout.addWidget(self.id_label)
        self.headword_label = QLabel(self.tr("Headword"))
        form_layout.addWidget(self.headword_label)
        self.entry_headword = QLineEdit()
        form_layout.addWidget(self.entry_headword)
        self.variation_label = QLabel(self.tr("Variation"))
        form_layout.addWidget(self.variation_label)
        self.entry_variation = QLineEdit()
        form_layout.addWidget(self.entry_variation)
        self.pos_label = QLabel(self.tr("Part of Speech"))
        form_layout.addWidget(self.pos_label)
        self.entry_pos = QLineEdit()
        form_layout.addWidget(self.entry_pos)
        self.notes_label = QLabel(self.tr("Notes"))
        form_layout.addWidget(self.notes_label)
        self.entry_notes = QLineEdit()
        form_layout.addWidget(self.entry_notes)
        self.meaning_label = QLabel(self.tr("Meaning"))
        form_layout.addWidget(self.meaning_label)
        self.entry_meaning = QTextEdit()
        form_layout.addWidget(self.entry_meaning)
        self.left_panel = list_frame
        self.right_panel = form_frame
        splitter.addWidget(form_frame)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter)


        self.entry_headword.installEventFilter(self)
        self.entry_variation.installEventFilter(self)
        self.entry_pos.installEventFilter(self)
        self.entry_notes.installEventFilter(self)
        self.entry_meaning.installEventFilter(self) 

       
        QWidget.setTabOrder(self.entry_headword, self.entry_variation)
        QWidget.setTabOrder(self.entry_variation, self.entry_pos)
        QWidget.setTabOrder(self.entry_pos, self.entry_notes)
        QWidget.setTabOrder(self.entry_notes, self.entry_meaning)

        self.entry_headword.setFocusPolicy(Qt.StrongFocus)
        self.entry_variation.setFocusPolicy(Qt.StrongFocus)
        self.entry_pos.setFocusPolicy(Qt.StrongFocus)
        self.entry_notes.setFocusPolicy(Qt.StrongFocus)

        self.entry_meaning.setFocusPolicy(Qt.StrongFocus)


        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel(self.tr("Total Headwords: 0"))
        self.status_bar.addPermanentWidget(self.status_label)

        self.initialize_last_db()

        # Keyboard shortcuts
        self.add_shortcut(Qt.CTRL + Qt.Key_S, self.save_entry)
        self.add_shortcut(Qt.CTRL + Qt.Key_D, self.delete_entry)
        self.add_shortcut(Qt.CTRL + Qt.Key_F, self.search_filter)
        self.add_shortcut(Qt.CTRL + Qt.Key_N, self.clear_fields)
        self.add_shortcut(Qt.CTRL + Qt.Key_A, self.create_database)
        self.add_shortcut(Qt.CTRL + Qt.Key_O, self.load_database)
        self.add_shortcut(Qt.CTRL + Qt.Key_Q, self.exit_app)
        self.add_shortcut(Qt.CTRL + Qt.Key_Z, self.undoStack.undo)
        self.add_shortcut(Qt.CTRL + Qt.Key_Y, self.undoStack.redo)
        self.add_shortcut(Qt.CTRL + Qt.SHIFT + Qt.Key_F, self.show_duplicates)
        self.add_shortcut(Qt.CTRL + Qt.SHIFT + Qt.Key_C, self.import_csv)
        self.add_shortcut(Qt.CTRL + Qt.SHIFT + Qt.Key_J, self.import_json)
        self.add_shortcut(Qt.CTRL + Qt.ALT + Qt.Key_C, self.export_csv)
        self.add_shortcut(Qt.CTRL + Qt.ALT + Qt.Key_J, self.export_json)
        self.add_shortcut(Qt.CTRL + Qt.ALT + Qt.Key_P, self.export_pdf)
        self.add_shortcut(Qt.CTRL + Qt.Key_BracketLeft, self.toggle_left_panel)
        self.add_shortcut(Qt.CTRL + Qt.Key_BracketRight, self.toggle_right_panel)
        self.add_shortcut(Qt.CTRL + Qt.Key_Slash, self.toggle_status_bar)
        self.add_shortcut(Qt.CTRL + Qt.SHIFT + Qt.Key_S, self.show_db_statistics)
        self.add_shortcut(Qt.Key_F1, self.show_help)

    def add_shortcut(self, key, function):
        shortcut = QShortcut(key, self)
        shortcut.activated.connect(function)

    def format_size(self, size_bytes):
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    def show_db_statistics(self):
        title = self.tr("Database Statistics")
        no_db_message = self.tr("No database loaded.")
        
        if not self.db_manager.conn:
            QMessageBox.information(self, title, no_db_message)
            return
        self.db_manager.cursor.execute("SELECT COUNT(*) FROM Entry")
        headword_count = self.db_manager.cursor.fetchone()[0]
        self.db_manager.cursor.execute("SELECT COUNT(*) FROM Senses")
        meaning_count = self.db_manager.cursor.fetchone()[0]
        self.db_manager.cursor.execute(
            "SELECT COUNT(*) FROM (SELECT headword FROM Entry GROUP BY headword HAVING COUNT(*) > 1)"
        )
        duplicate_count = self.db_manager.cursor.fetchone()[0]

        db_file = self.db_manager.load_last_db()
        if db_file and os.path.exists(db_file):
            db_size_bytes = os.path.getsize(db_file)
            db_size = self.format_size(db_size_bytes)
            last_modified_timestamp = os.path.getmtime(db_file)
            last_modified = datetime.datetime.fromtimestamp(last_modified_timestamp).strftime("%Y-%m-%d %H:%M:%S")
        else:
            db_size = self.tr("Unknown")
            last_modified = self.tr("Unknown")
            db_file = self.tr("Not Available")
        stats_message = (
            f"{self.tr('Database Statistics:')}\n\n"
            f"{self.tr('Headwords')}: {headword_count}\n"
            f"{self.tr('Meanings')}: {meaning_count}\n"
            f"{self.tr('Duplicate Headwords')}: {duplicate_count}\n\n"
            f"{self.tr('Database File')}: {db_file}\n"
            f"{self.tr('File Size')}: {db_size}\n"
            f"{self.tr('Last Modified')}: {last_modified}\n"
        )

        QMessageBox.information(self, title, stats_message)

    def initialize_last_db(self):
        last_db = self.db_manager.load_last_db()
        if last_db and os.path.exists(last_db):
            self.db_manager.load_database(self, last_db)
            self.populate_headwords()

    def populate_headwords(self):
        self.listbox_headwords.clear()
        if self.db_manager.conn:
            self.db_manager.cursor.execute("SELECT id, headword FROM Entry ORDER BY headword")
            for row in self.db_manager.cursor.fetchall():
                item = QListWidgetItem(row[1])  
                item.setData(Qt.UserRole, row[0])  
                self.listbox_headwords.addItem(item)
        self.update_headword_count()
        self.populate_alphabet_combo()

    def display_entry(self, item):
        entry_id = item.data(Qt.UserRole)  
        self.db_manager.cursor.execute('''
        SELECT Entry.*, Senses.meaning 
        FROM Entry LEFT JOIN Senses 
        ON Entry.id = Senses.entry_id 
        WHERE Entry.id=?''', (entry_id,))
        result = self.db_manager.cursor.fetchone()
        if result:
            self.current_entry_id = result[0]
            self.id_label.setText(self.tr("ID: {id}").format(id=self.current_entry_id))
            self.entry_headword.setText(result[1])
            self.entry_variation.setText(result[2])
            self.entry_pos.setText(result[3])
            self.entry_notes.setText(result[4])
            self.entry_meaning.clear()
            self.db_manager.cursor.execute("SELECT meaning FROM Senses WHERE entry_id=?", (self.current_entry_id,))
            for row in self.db_manager.cursor.fetchall():
                self.entry_meaning.append(row[0])

    def search_filter(self):
        search_term = self.entry_search.text().lower().strip()
        criteria = self.search_criteria_combo.currentText()
        fuzzy = self.fuzzy_search_checkbox.isChecked()
        self.listbox_headwords.clear()
        if not search_term:
            self.populate_headwords()
            return

        try:
            if fuzzy:
              
                self.db_manager.cursor.execute("SELECT id, headword, part_of_speech, variation FROM Entry")
                rows = self.db_manager.cursor.fetchall()
                matched = []
                for row in rows:
                    entry_id, headword, pos, variation = row[0], row[1], row[2], row[3]
                    if criteria == self.tr("Headword"):
                        field = (headword or "").lower()
                        if difflib.get_close_matches(search_term, [field], cutoff=0.6):
                            matched.append((headword, entry_id))
                    elif criteria == self.tr("Part of Speech"):
                        field = (pos or "").lower()
                        if difflib.get_close_matches(search_term, [field], cutoff=0.6):
                            matched.append((headword, entry_id))
                    elif criteria == self.tr("Variation"):
                        field = (variation or "").lower()
                        if difflib.get_close_matches(search_term, [field], cutoff=0.6):
                            matched.append((headword, entry_id))
                    else:  
                        fields = [
                            (headword or "").lower(),
                            (pos or "").lower(),
                            (variation or "").lower()
                        ]
                        if any(difflib.get_close_matches(search_term, [f], cutoff=0.6) for f in fields):
                            matched.append((headword, entry_id))
                
               
                for head, entry_id in sorted(matched, key=lambda x: x[0]):
                    item = QListWidgetItem(head)
                    item.setData(Qt.UserRole, entry_id)
                    self.listbox_headwords.addItem(item)
            
            else:  
                if criteria == self.tr("Headword"):
                    query = "SELECT id, headword FROM Entry WHERE LOWER(headword) LIKE ?"
                    param = ('%' + search_term + '%',)
                elif criteria == self.tr("Part of Speech"):
                    query = "SELECT id, headword FROM Entry WHERE LOWER(part_of_speech) LIKE ?"
                    param = ('%' + search_term + '%',)
                elif criteria == self.tr("Variation"):
                    query = "SELECT id, headword FROM Entry WHERE LOWER(variation) LIKE ?"
                    param = ('%' + search_term + '%',)
                elif criteria == self.tr("Meaning"):
                    query = '''SELECT Entry.id, Entry.headword FROM Entry 
                               WHERE id IN (
                                   SELECT entry_id FROM Senses WHERE LOWER(meaning) LIKE ?
                               )'''
                    param = ('%' + search_term + '%',)
                else: 
                    query = '''SELECT Entry.id, Entry.headword FROM Entry
                               WHERE LOWER(headword) LIKE ? 
                               OR LOWER(part_of_speech) LIKE ? 
                               OR LOWER(variation) LIKE ?
                               OR id IN (
                                   SELECT entry_id FROM Senses WHERE LOWER(meaning) LIKE ?
                               )'''
                    param = ('%' + search_term + '%', '%' + search_term + '%', 
                             '%' + search_term + '%', '%' + search_term + '%')
                
                self.db_manager.cursor.execute(query, param)
                rows = self.db_manager.cursor.fetchall()
                
             
                for row in rows:
                    entry_id, headword = row[0], row[1]
                    item = QListWidgetItem(headword)
                    item.setData(Qt.UserRole, entry_id)
                    self.listbox_headwords.addItem(item)
        
        except Exception as e:
            logging.exception("Error in search_filter")

    def populate_alphabet_combo(self):
        self.alphabet_combo.blockSignals(True)
        self.alphabet_combo.clear()
        self.alphabet_combo.addItem(self.tr("All"))

        if not self.db_manager.conn:
            self.alphabet_combo.blockSignals(False)
            return

   
        self.db_manager.cursor.execute("SELECT headword FROM Entry")
        first_chars = {
            row[0][0] for row in self.db_manager.cursor.fetchall()
            if row[0]  
        }
        for ch in sorted(first_chars):
            self.alphabet_combo.addItem(ch)

        self.alphabet_combo.blockSignals(False)

    def filter_by_alphabet(self, index):
        """Show only headwords whose first letter matches the dropdown selection."""
        letter = self.alphabet_combo.currentText()
        self.listbox_headwords.clear()

        if letter == self.tr("All"):
            return self.populate_headwords()

        if not self.db_manager.conn:
            return

      
        query = "SELECT id, headword FROM Entry WHERE headword LIKE ? ORDER BY headword"
        self.db_manager.cursor.execute(query, (letter + '%',))
        for entry_id, headword in self.db_manager.cursor.fetchall():
            item = QListWidgetItem(headword)
            item.setData(Qt.UserRole, entry_id)
            self.listbox_headwords.addItem(item)

        self.update_headword_count()

    def save_entry(self, auto=False):
        if not self.db_manager.conn:
            if not auto:
                QMessageBox.warning(self, self.tr("Database Error"),
                                    self.tr("Please create or load a database first."))
            return

        fields = {
            'headword': self.entry_headword.text(),
            'variation': self.entry_variation.text(),
            'pos': self.entry_pos.text(),
            'notes': self.entry_notes.text(),
            'meanings': [m.strip() for m in self.entry_meaning.toPlainText().strip().splitlines() if m.strip()]
        }

        if auto:
            if not fields['headword'] or not fields['meanings']:
                return
        else:
            if not fields['headword'] or not fields['meanings']:
                QMessageBox.warning(self, self.tr("Missing"),
                                    self.tr("Headword and Meaning(s) are required!"))
                return

        try:
            if self.current_entry_id:
                self.db_manager.cursor.execute(
                    "SELECT headword, variation, part_of_speech, notes FROM Entry WHERE id=?", 
                    (self.current_entry_id,)
                )
                row = self.db_manager.cursor.fetchone()
                if not row:
                    return
                old_data = {
                    'headword': row[0],
                    'variation': row[1],
                    'pos': row[2],
                    'notes': row[3],
                    'meanings': []
                }
                self.db_manager.cursor.execute("SELECT meaning FROM Senses WHERE entry_id=?", (self.current_entry_id,))
                old_data['meanings'] = [r[0] for r in self.db_manager.cursor.fetchall()]

                new_data = fields
                command = UpdateEntryCommand(self.db_manager, self.current_entry_id, old_data, new_data)
                self.undoStack.push(command)
            else:
                self.db_manager.cursor.execute(
                    "INSERT INTO Entry (headword, variation, part_of_speech, notes) VALUES (?, ?, ?, ?)",
                    (fields['headword'], fields['variation'], fields['pos'], fields['notes'])
                )
                entry_id = self.db_manager.cursor.lastrowid
                self.current_entry_id = entry_id 
                for meaning in fields['meanings']:
                    self.db_manager.cursor.execute("INSERT INTO Senses (entry_id, meaning) VALUES (?, ?)",
                                                   (entry_id, meaning))
                self.db_manager.conn.commit()

            if not self.current_entry_id or auto:
                self.db_manager.conn.commit()
                self.update_status(self.tr("Autosaved"))
                self.populate_headwords()
            else:
                self.db_manager.conn.commit()
                self.update_status(self.tr("Entry saved successfully"))
                self.clear_fields()
                self.populate_headwords()
        except Exception as e:
            QMessageBox.critical(
                self,
                self.tr("Save Error"),
                self.tr("Failed to save entry:\n{error}").format(error=str(e))
            )


    def delete_entry(self):
        selected_items = self.listbox_headwords.selectedItems()
        if not selected_items:
            return

      
        entries_to_delete = [item.data(Qt.UserRole) for item in selected_items]

       
        reply = QMessageBox.question(
            self,
            self.tr("Confirm"),
            self.tr("Delete {} selected entries?").format(len(entries_to_delete)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
               
                for entry_id in entries_to_delete:
                    self.db_manager.cursor.execute("DELETE FROM Senses WHERE entry_id=?", (entry_id,))
                    self.db_manager.cursor.execute("DELETE FROM Entry WHERE id=?", (entry_id,))
                self.db_manager.conn.commit()

                for item in selected_items:
                    self.listbox_headwords.takeItem(self.listbox_headwords.row(item))

                self.update_status(self.tr("Deleted {} entries").format(len(entries_to_delete)))
                self.clear_fields()

            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.tr("Error"),
                    self.tr("Delete failed: {}").format(str(e))
                )


    def clear_fields(self):
        self.current_entry_id = None
        self.id_label.clear()
        self.entry_headword.clear()
        self.entry_variation.clear()
        self.entry_pos.clear()
        self.entry_notes.clear()
        self.entry_meaning.clear()


    def update_headword_count(self):
        if self.db_manager.conn:
            self.db_manager.cursor.execute("SELECT COUNT(*) FROM Entry")
            total_count = self.db_manager.cursor.fetchone()[0]
            self.status_label.setText(self.tr("Total Headwords: {count}").format(count=total_count))


    def update_status(self, message):
        self.status_bar.showMessage(message)


    def export_pdf(self):
        self.pdf_tool_window = PDFExporter()
        self.pdf_tool_window.show()


    def show_duplicates(self):
        if not self.db_manager.conn or not self.db_manager.cursor:
            QMessageBox.warning(
                self,
                self.tr("Database Error"),
                self.tr("Please create or load a database first.")
            )
            return

        self.db_manager.cursor.execute("SELECT headword, COUNT(*) FROM Entry GROUP BY headword HAVING COUNT(*) > 1")
        rows = self.db_manager.cursor.fetchall()
        if rows:
            duplicates_text = ""
            for row in rows:
                duplicates_text += self.tr("Duplicate Headword: {headword} (Appears {count} times)\n\n").format(headword=row[0], count=row[1])
            self.duplicates_window = DuplicatesWindow(duplicates_text, self)
            self.duplicates_window.show()
            self.duplicates_window.raise_()
            self.duplicates_window.activateWindow()
        else:
            QMessageBox.information(
                self,
                self.tr("No Duplicates"),
                self.tr("No duplicate headwords found.")
            )


    def show_dictionary_aid(self):
        aid_window = DictionaryAidWindow(self)
        aid_window.exec_() 


    def create_database(self):
        db_name = self.db_manager.create_database(self)
        if db_name:
            self.populate_headwords()
            self.add_to_recent_files(db_name)


    def load_database(self):
        db_name = self.db_manager.load_database(self)
        if db_name:
            self.populate_headwords()
            self.add_to_recent_files(db_name)


    def export_csv(self):
        self.import_export_manager.export_csv(self)


    def export_json(self):
        self.import_export_manager.export_json(self)


    def import_csv(self):
        progress = QProgressDialog(self.tr("Importing CSV..."), self.tr("Cancel"), 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        self.import_export_manager.import_csv(self)
        self.populate_headwords()
        progress.close()


    def import_json(self):
        progress = QProgressDialog(self.tr("Importing JSON..."), self.tr("Cancel"), 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        self.import_export_manager.import_json(self)
        self.populate_headwords()
        progress.close()


    def show_about(self):
        QMessageBox.information(
            self,
            self.tr("About Uri Dictmaker"),
            self.tr("Uri Dictmaker\nVersion 1.2.0\n\nUri DictMaker is a professional dictionary creation and management tool designed primarily for bilingual projects. It enables users to efficiently build, manage, and edit dictionaries with structured entries that include headwords, parts of speech, and custom notes. Whether you're a linguist, researcher, translator, or language enthusiast, Uri DictMaker offers a user-friendly interface and powerful features to streamline dictionary development.")
        )


    def show_help(self):
        help_text = self.tr("Keyboard Shortcuts:\n"
                              "Ctrl+S - Save Entry\n"
                              "Ctrl+D - Delete Entry\n"
                              "Ctrl+F - Search/Filter Entries\n"
                              "Ctrl+N - New Entry\n"
                              "Ctrl+A - New Database\n"
                              "Ctrl+O - Open/Load Database\n"
                              "Ctrl+Q - Quit\n"
                              "CTRL+Z        - Undo\n"
                              "CTRL+Y        - Redo\n"
                              "CTRL+SHIFT+F  - Show Duplicates\n"
                              "CTRL+SHIFT+C  - Import CSV\n"
                              "CTRL+SHIFT+J  - Import JSON\n"
                              "CTRL+ALT+C    - Export CSV\n"
                              "CTRL+ALT+J    - Export JSON\n"
                              "CTRL+ALT+P    - Export PDF\n"
                              "CTRL+[        - Toggle Left Panel\n"
                              "CTRL+]        - Toggle Right Panel\n"
                              "CTRL+/        - Toggle Status bar\n"
                              "CTRL+SHIFT+S  - Show Database Statistics\n"
                              "F1            - Show Help")
        QMessageBox.information(self, self.tr("Help"), help_text)


    def load_stylesheet(self, filename):
        style_path = resource_path(filename)
        if os.path.exists(style_path):
            with open(style_path, "r") as file:
                self.setStyleSheet(file.read())
        else:
            logging.error(f"Stylesheet not found: {style_path}")

    def closeEvent(self, event):
        if self.db_manager.conn:
            self.db_manager.cursor.close()
            self.db_manager.conn.close()
        event.accept()

    def change_theme(self, theme_filename):
        self.load_stylesheet(theme_filename)
        self.current_theme = theme_filename
        settings = load_settings()
        settings["theme"] = theme_filename
        save_settings(settings)
        self.update_status(self.tr("Theme changed to {theme}").format(theme=theme_filename))


    def change_language(self, lang_code):
        self.current_language = lang_code
        app = QApplication.instance()

      
        if hasattr(self, 'translator'):
            app.removeTranslator(self.translator)

    
        if hasattr(self, 'qt_translator'):
            app.removeTranslator(self.qt_translator)

 
        translator = QTranslator()
        qm_file = resource_path(f"translations/{lang_code}.qm")
        if translator.load(qm_file):
            app.installTranslator(translator)
            self.translator = translator

        qt_translator = QTranslator()
        qt_qm = QLibraryInfo.location(QLibraryInfo.TranslationsPath) + f"/qtbase_{lang_code}.qm"
        if qt_translator.load(qt_qm):
            app.installTranslator(qt_translator)
            self.qt_translator = qt_translator

        settings = load_settings()
        settings["language"] = lang_code
        save_settings(settings)
        self.update_status(self.tr("Language changed."))
        self.apply_translations()


    def toggle_left_panel(self):
        if self.left_panel.isVisible():
            self.left_panel.hide()
        else:
            self.left_panel.show()


    def toggle_right_panel(self):
        if self.right_panel.isVisible():
            self.right_panel.hide()
        else:
            self.right_panel.show()


    def toggle_status_bar(self):
        if self.status_bar.isVisible():
            self.status_bar.hide()
        else:
            self.status_bar.show()


    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()


    def apply_translations(self):
        self.setWindowTitle(self.tr("Uri Dictmaker"))
        self.file_menu.setTitle(self.tr("File"))
        self.edit_menu.setTitle(self.tr("Edit"))
        self.view_menu.setTitle(self.tr("View"))
        self.tools_menu.setTitle(self.tr("Tools"))
        self.new_db_action.setText(self.tr("New Database"))
        self.open_db_action.setText(self.tr("Open Database"))
        self.import_csv_action.setText(self.tr("Import CSV"))
        self.export_csv_action.setText(self.tr("Export CSV"))
        self.import_json_action.setText(self.tr("Import JSON"))
        self.export_json_action.setText(self.tr("Export JSON"))
        self.export_pdf_action.setText(self.tr("Publish PDF"))
        self.undo_action.setText(self.tr("Undo"))
        self.redo_action.setText(self.tr("Redo"))
        self.copy_action.setText(self.tr("Copy"))
        self.cut_action.setText(self.tr("Cut"))
        self.paste_action.setText(self.tr("Paste"))
        self.left_panel_action.setText(self.tr("Toggle left panel"))
        self.right_panel_action.setText(self.tr("Toggle right panel"))
        self.status_bar_action.setText(self.tr("Toggle status bar"))
        self.show_duplicates_action.setText(self.tr("Show Duplicates"))
        self.fullscreen_action.setText(self.tr("Fullscreen"))
        self.dictionary_help_action.setText(self.tr("Help with Dictionary making"))
        self.database_stats_action.setText(self.tr("Database Statistics"))
        self.autosave_interval_action.setText(self.tr("Set Autosave Interval"))
        self.exit_action.setText(self.tr("Exit"))
        self.preferences_menu.setTitle(self.tr("Preferences"))
        self.theme_menu.setTitle(self.tr("Theme"))
        self.dark_theme_action.setText(self.tr("Dark"))
        self.default_theme_action.setText(self.tr("Default"))
        self.material_theme_action.setText(self.tr("Material"))
        self.language_menu.setTitle(self.tr("Language"))
        self.arabic_action.setText(self.tr("العربية"))
        self.english_action.setText(self.tr("English"))
        self.french_action.setText(self.tr("française"))
        self.german_action.setText(self.tr("Deutsch"))
        self.kannada_action.setText(self.tr("ಕನ್ನಡ"))
        self.malayalam_action.setText(self.tr("മലയാളം"))
        self.rajasthani_action.setText(self.tr("राजस्थानी"))
        self.telugu_action.setText(self.tr("తెలుగు"))
        self.help_menu.setTitle(self.tr("Help"))
        self.keyboard_shortcuts_action.setText(self.tr("Keyboard Shortcuts"))
        self.about_action.setText(self.tr("About"))
        self.fuzzy_search_checkbox.setText(self.tr("Fuzzy Search"))
        self.fuzzy_search_checkbox.setToolTip(self.tr("Check for approximate matches"))
        self.entry_search.setToolTip(self.tr("Enter search term"))
        self.search_label.setText(self.tr("Search:"))
        self.entries_label.setText(self.tr("Entries"))
        self.headword_label.setText(self.tr("Headword"))
        self.variation_label.setText(self.tr("Variation"))
        self.pos_label.setText(self.tr("Part of Speech"))
        self.notes_label.setText(self.tr("Notes"))
        self.meaning_label.setText(self.tr("Meaning"))
        self.search_criteria_combo.setToolTip(self.tr("Select search criteria"))
        self.search_criteria_combo.clear()
        self.search_criteria_combo.addItems([
            self.tr("All"),
            self.tr("Headword"),
            self.tr("Part of Speech"),
            self.tr("Variation"),
            self.tr("Meaning"),
        ])

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if obj in [
                self.entry_headword, 
                self.entry_variation, 
                self.entry_pos, 
                self.entry_notes, 
                self.entry_meaning
            ]:
                if event.key() == Qt.Key_Down:
                    self.focusNextChild()
                    return True
                elif event.key() == Qt.Key_Up:
                    self.focusPreviousChild()
                    return True
        return super().eventFilter(obj, event)

    def delete_selected_entries(self):
        selected_items = self.listbox_headwords.selectedItems()
        if not selected_items:
            return

        reply = QMessageBox.question(
            self,
            self.tr("Confirm"),
            self.tr("Delete selected entries permanently?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                for item in selected_items:
                    headword = item.text()
                    self.db_manager.cursor.execute("SELECT id FROM Entry WHERE headword=?", (headword,))
                    rows = self.db_manager.cursor.fetchall()
                    for row in rows:
                        entry_id = row[0]
                        self.db_manager.cursor.execute("DELETE FROM Senses WHERE entry_id=?", (entry_id,))
                        self.db_manager.cursor.execute("DELETE FROM Entry WHERE id=?", (entry_id,))
                self.db_manager.conn.commit()
                self.update_status(self.tr("Entry deleted"))
                self.clear_fields()
                self.populate_headwords()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.tr("Error"),
                    self.tr("Delete failed: {error_message}").format(error_message=e)
                )

    def autosave(self):
        if self.entry_headword.text().strip() and self.entry_meaning.toPlainText().strip():
            self.save_entry(auto=True)

    def refresh_headwords_panel(self):
        self.populate_headwords()
        self.listbox_headwords.clearSelection()
        self.clear_fields()
        self.populate_headwords()

    def set_autosave_interval(self):
        current_interval = self.autosave_interval
        new_interval, ok = QInputDialog.getInt(
            self,
            self.tr("Autosave"),
            self.tr("Enter autosave interval in seconds (30-300)"),
            value=current_interval, 
            min=30, 
            max=300
        )
        if ok:
            self.autosave_interval = new_interval
            settings = load_settings()
            settings["autosave_interval"] = new_interval
            save_settings(settings)
            self.autosave_timer.start(new_interval * 1000)
            self.update_status(
                self.tr("Autosave interval set to {interval} seconds").format(interval=new_interval)
            )

    def copy_text(self):
        widget = QApplication.focusWidget()
        if widget is not None and hasattr(widget, 'copy'):
            widget.copy()

    def cut_text(self):
        widget = QApplication.focusWidget()
        if widget is not None and hasattr(widget, 'cut'):
            widget.cut()

    def paste_text(self):
        widget = QApplication.focusWidget()
        if widget is not None and hasattr(widget, 'paste'):
            widget.paste()

    def exit_app(self):
        reply = QMessageBox.question(
            self,
            self.tr("Exit Confirmation"),
            self.tr("Are you sure you want to exit the application?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._exit_confirmed = True
            self.close()

    def closeEvent(self, event):
        if getattr(self, "_exit_confirmed", False):
            event.accept()
        else:
            reply = QMessageBox.question(
                self,
                self.tr("Exit Confirmation"),
                self.tr("Are you sure you want to exit the application?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()

    def recent_files(self):
        return self.settings.value("recentFiles", [], type=list)

    def save_recent_files(self, files):
        self.settings.setValue("recentFiles", files[:MAX_RECENT_FILES])

    def update_recent_menu(self):
        self.recent_menu.clear()
        paths = self.recent_files()
        if not paths:
            placeholder = QAction(self.tr("(No Recent Files)"), self)
            placeholder.setEnabled(False)
            self.recent_menu.addAction(placeholder)
            return

        for i, path in enumerate(paths):
            name = os.path.basename(path)
            action = QAction(f"&{i+1}. {name}", self)
            action.setData(path)
            action.triggered.connect(self.open_recent_file)
            self.recent_menu.addAction(action)

    def add_to_recent_files(self, filepath):
        if not filepath:
            return
        paths = [filepath] + [p for p in self.recent_files() if p != filepath]
        self.save_recent_files(paths)
        self.update_recent_menu()

    def open_recent_file(self):
        path = self.sender().data()
        if not os.path.exists(path):
            QMessageBox.warning(self, self.tr("File Not Found"),
                                self.tr(f"Cannot find:\n{path}\nIt will be removed from the list."))
            paths = [p for p in self.recent_files() if p != path]
            self.save_recent_files(paths)
            self.update_recent_menu()
            return

        self.db_manager.load_database(self, path)
        self.populate_headwords()
        self.add_to_recent_files(path)
        self.update_status(self.tr(f"Opened {path}"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DictionaryApp()
    window.show()
    sys.exit(app.exec_())
