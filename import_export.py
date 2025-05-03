import json, csv, os, logging
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QMessageBox, QFileDialog

class ImportExportManager:
    def __init__(self, db_manager, status_callback):
        self.db_manager = db_manager
        self.status_callback = status_callback

    def export_csv(self, parent):
        path, _ = QFileDialog.getSaveFileName(
            parent, 
            QCoreApplication.translate("ImportExportManager", "Export CSV"),
            QCoreApplication.translate("ImportExportManager", "untitled.csv")
        )
        if not path:
            return
        try:
            self.db_manager.cursor.execute('''
                SELECT Entry.*, GROUP_CONCAT(Senses.meaning, ';;') AS meanings 
                FROM Entry 
                LEFT JOIN Senses ON Entry.id = Senses.entry_id 
                GROUP BY Entry.id
            ''')
            entries = self.db_manager.cursor.fetchall()
            headers = [description[0] for description in self.db_manager.cursor.description]
            with open(path, "w", newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                for row in entries:
                    writer.writerow(row)
            self.status_callback(QCoreApplication.translate("ImportExportManager", "CSV exported successfully"))
        except Exception as e:
            QMessageBox.critical(
                parent,
                QCoreApplication.translate("ImportExportManager", "Error"),
                QCoreApplication.translate("ImportExportManager", "CSV export failed: {error_message}").format(error_message=e)
            )

    def export_json(self, parent):
        path, _ = QFileDialog.getSaveFileName(
            parent, 
            QCoreApplication.translate("ImportExportManager", "Export JSON"),
            QCoreApplication.translate("ImportExportManager", "untitled.json")
        )
        if not path:
            return
        try:
            self.db_manager.cursor.execute('''
                SELECT Entry.*, GROUP_CONCAT(Senses.meaning, ';;') AS meanings 
                FROM Entry 
                LEFT JOIN Senses ON Entry.id = Senses.entry_id 
                GROUP BY Entry.id
            ''')
            entries = self.db_manager.cursor.fetchall()
            headers = [description[0] for description in self.db_manager.cursor.description]
            data = []
            for row in entries:
                entry_dict = dict(zip(headers, row))
                entry_dict['meanings'] = entry_dict['meanings'].split(';;') if entry_dict['meanings'] else []
                data.append(entry_dict)
            with open(path, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self.status_callback(QCoreApplication.translate("ImportExportManager", "JSON exported successfully"))
        except Exception as e:
            QMessageBox.critical(
                parent,
                QCoreApplication.translate("ImportExportManager", "Error"),
                QCoreApplication.translate("ImportExportManager", "JSON export failed: {error_message}").format(error_message=e)
            )

    def import_csv(self, parent):
        path, _ = QFileDialog.getOpenFileName(
            parent,
            QCoreApplication.translate("ImportExportManager", "Import CSV"),
            QCoreApplication.translate("ImportExportManager", "CSV files (*.csv);;All files (*.*)")
        )
        if not path:
            return

        reply = QMessageBox.question(
            parent,
            QCoreApplication.translate("ImportExportManager", "Confirm Import"),
            QCoreApplication.translate(
                "ImportExportManager",
                "Do you wish to import data from external file? This may create duplicates of your existing headwords."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            with open(path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
             
                clean_fields = [h.strip() for h in reader.fieldnames or [] if h and h.strip()]
                required = {'headword', 'variation', 'part_of_speech', 'notes', 'meanings'}
                missing = required - set(clean_fields)
                if missing:
                    raise ValueError(f"Invalid CSV: missing columns {sorted(missing)}")

                for row in reader:
                   
                    headword = row.get('headword', '').strip()
                    variation = row.get('variation', '').strip()
                    pos       = row.get('part_of_speech', '').strip()
                    notes     = row.get('notes', '').strip()
                    meanings  = row.get('meanings', '').strip()

                  
                    self.db_manager.cursor.execute(
                        "INSERT INTO Entry (headword, variation, part_of_speech, notes) VALUES (?, ?, ?, ?)",
                        (headword, variation, pos, notes)
                    )
                    entry_id = self.db_manager.cursor.lastrowid

                
                    if meanings:
                        for m in meanings.split(';;'):
                            m = m.strip()
                            if m:
                                self.db_manager.cursor.execute(
                                    "INSERT INTO Senses (entry_id, meaning) VALUES (?, ?)",
                                    (entry_id, m)
                                )

                self.db_manager.conn.commit()
            self.status_callback(QCoreApplication.translate("ImportExportManager", "CSV imported successfully"))

        except Exception as e:
            QMessageBox.critical(
                parent,
                QCoreApplication.translate("ImportExportManager", "Error"),
                QCoreApplication.translate(
                    "ImportExportManager",
                    "CSV import failed: {error_message}"
                ).format(error_message=e)
            )



    def import_json(self, parent):
        path, _ = QFileDialog.getOpenFileName(
            parent,
            QCoreApplication.translate("ImportExportManager", "Import JSON"),
            QCoreApplication.translate("ImportExportManager", "JSON files (*.json);;All files (*.*)")
        )
        if not path:
            return

        reply = QMessageBox.question(
            parent,
            QCoreApplication.translate("ImportExportManager", "Confirm Import"),
            QCoreApplication.translate(
                "ImportExportManager",
                "Do you wish to import data from external file? This may create duplicates of your existing headwords."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            with open(path, "r", encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise ValueError("Invalid JSON: top-level structure must be a list of entries.")

            required_keys = {"headword", "variation", "part_of_speech", "notes", "meanings"}
            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    raise ValueError(f"Entry {idx} is not an object.")
                missing = required_keys - set(item.keys())
                if missing:
                    raise ValueError(f"Entry {idx} missing keys: {missing}")
                if not isinstance(item["meanings"], list):
                    raise ValueError(f"Entry {idx}: 'meanings' must be a list.")

             
                self.db_manager.cursor.execute(
                    "INSERT INTO Entry (headword, variation, part_of_speech, notes) VALUES (?, ?, ?, ?)",
                    (
                        item["headword"].strip(),
                        item["variation"].strip(),
                        item["part_of_speech"].strip(),
                        item["notes"].strip()
                    )
                )
                eid = self.db_manager.cursor.lastrowid
                for m in item["meanings"]:
                    m = str(m).strip()
                    if m:
                        self.db_manager.cursor.execute(
                            "INSERT INTO Senses (entry_id, meaning) VALUES (?, ?)",
                            (eid, m)
                        )

            self.db_manager.conn.commit()
            self.status_callback(QCoreApplication.translate("ImportExportManager", "JSON imported successfully"))

        except Exception as e:
            QMessageBox.critical(
                parent,
                QCoreApplication.translate("ImportExportManager", "Error"),
                QCoreApplication.translate(
                    "ImportExportManager",
                    "JSON import failed: {error_message}"
                ).format(error_message=e)
            )

