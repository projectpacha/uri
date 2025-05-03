from PyQt5.QtWidgets import QUndoCommand
from PyQt5.QtCore import QCoreApplication

class UpdateEntryCommand(QUndoCommand):
    def __init__(self, db_manager, entry_id, old_data, new_data, description=None):
        if description is None:
            description = QCoreApplication.translate("UpdateEntryCommand", "Update Entry")
        super().__init__(description)
        self.db_manager = db_manager
        self.entry_id = entry_id
        self.old_data = old_data  
        self.new_data = new_data

    def undo(self):
        self.db_manager.cursor.execute(
            "UPDATE Entry SET headword=?, variation=?, part_of_speech=?, notes=? WHERE id=?",
            (self.old_data['headword'], self.old_data['variation'],
             self.old_data['pos'], self.old_data['notes'], self.entry_id)
        )
        self.db_manager.cursor.execute("DELETE FROM Senses WHERE entry_id=?", (self.entry_id,))
        for meaning in self.old_data['meanings']:
            self.db_manager.cursor.execute(
                "INSERT INTO Senses (entry_id, meaning) VALUES (?, ?)",
                (self.entry_id, meaning)
            )
        self.db_manager.conn.commit()

    def redo(self):
        self.db_manager.cursor.execute(
            "UPDATE Entry SET headword=?, variation=?, part_of_speech=?, notes=? WHERE id=?",
            (self.new_data['headword'], self.new_data['variation'],
             self.new_data['pos'], self.new_data['notes'], self.entry_id)
        )
        self.db_manager.cursor.execute("DELETE FROM Senses WHERE entry_id=?", (self.entry_id,))
        for meaning in self.new_data['meanings']:
            self.db_manager.cursor.execute(
                "INSERT INTO Senses (entry_id, meaning) VALUES (?, ?)",
                (self.entry_id, meaning)
            )
        self.db_manager.conn.commit()


class DeleteEntryCommand(QUndoCommand):
    def __init__(self, db_manager, entry_id, entry_data, description=None):
        if description is None:
            description = QCoreApplication.translate("DeleteEntryCommand", "Delete Entry")
        super().__init__(description)
        self.db_manager = db_manager
        self.entry_id = entry_id
        self.entry_data = entry_data  

    def undo(self):
        self.db_manager.cursor.execute(
            "INSERT INTO Entry (id, headword, variation, part_of_speech, notes) VALUES (?, ?, ?, ?, ?)",
            (self.entry_id, self.entry_data['headword'], self.entry_data['variation'],
             self.entry_data['pos'], self.entry_data['notes'])
        )
        for meaning in self.entry_data['meanings']:
            self.db_manager.cursor.execute(
                "INSERT INTO Senses (entry_id, meaning) VALUES (?, ?)",
                (self.entry_id, meaning)
            )
        self.db_manager.conn.commit()

    def redo(self):
        self.db_manager.cursor.execute("DELETE FROM Senses WHERE entry_id=?", (self.entry_id,))
        self.db_manager.cursor.execute("DELETE FROM Entry WHERE id=?", (self.entry_id,))
        self.db_manager.conn.commit()
