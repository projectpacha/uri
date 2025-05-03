import os
import sys
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QApplication
from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView 

class DictionaryAidWindow(QDialog):
    def __init__(self, parent=None):
        super(DictionaryAidWindow, self).__init__(parent)
        self.setWindowTitle(self.tr("Dictionary Aids"))
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        self.browser = QWebEngineView(self)
        layout.addWidget(self.browser)

        html_path = os.path.join(os.path.dirname(__file__), "dict_help.html")
        if os.path.exists(html_path):
            self.browser.setUrl(QUrl.fromLocalFile(html_path))
        else:
            not_found_title = self.tr("Help file not found")
            not_found_text = self.tr("Please ensure dict_help.html is in the correct folder.")
            html = f"<html><body><h1>{not_found_title}</h1><p>{not_found_text}</p></body></html>"
            self.browser.setHtml(html)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DictionaryAidWindow()
    window.show()
    sys.exit(app.exec_())
