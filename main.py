import sys
import os
import ctypes
import requests
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtWebEngineWidgets import *

os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-gpu --enable-webgl --ignore-gpu-blocklist"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

width, height = (
    ctypes.windll.user32.GetSystemMetrics(0),
    ctypes.windll.user32.GetSystemMetrics(1)
)

#print(width, height)

windowDimensions = {'x': int(width / 6), 'y': int(height / 8), 'w': 1280, 'h': 800}

class APIFetcher(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, id_type, id_value):
        super().__init__()
        self.id_type = id_type
        self.id_value = id_value

    def run(self):
        try:
            if self.id_type == "TMPID":
                url = f"https://api.truckersmp.com/v2/player/{self.id_value}"
            else:
                url = f"https://api.truckersmp.com/v2/player/{self.id_value}"

            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                raise Exception("API returned non-200 status")

            data = response.json()
            if not data["response"]:
                raise Exception("No player data found")

            self.finished.emit(data["response"])

        except Exception as e:
            self.error.emit(str(e))

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TruckersMP Player Lookup")
        self.setGeometry(
            windowDimensions['x'],
            windowDimensions['y'],
            windowDimensions['w'],
            windowDimensions['h']
        )
        self.setup_ui()

    def setup_ui(self):
        self.dropdown = QComboBox()
        self.dropdown.addItems(["TMPID", "SteamID"])

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter ID...")

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.start_search)

        # Stylish result frame
        self.result_frame = QFrame()
        self.result_frame.setObjectName("resultFrame")

        self.result_label = QLabel("Player Info will appear here.")
        self.result_label.setWordWrap(True)
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        frame_layout = QVBoxLayout()
        frame_layout.addWidget(self.result_label)
        self.result_frame.setLayout(frame_layout)

        # Embedded browser (map.truckersmp.com)
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://map.truckersmp.com"))
        self.browser.setMinimumHeight(400)  # Adjust height as needed

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.dropdown)
        layout.addWidget(self.input_field)
        layout.addWidget(self.search_button)
        layout.addWidget(self.result_frame)
        layout.addWidget(self.browser)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def apply_stylesheet_from_file(self, app: QApplication, qss_path: str):
        try:
            with open(qss_path, "r") as file:
                app.setStyleSheet(file.read())
            return 0
        except Exception as e:
            print(f"[ERROR]: Failed to load QSS: {e}")
            return 1

    def start_search(self):
        id_value = self.input_field.text().strip()
        id_type = self.dropdown.currentText()

        if not id_value:
            QMessageBox.warning(self, "Warning", "Please enter a valid ID.")
            return

        self.search_button.setEnabled(False)
        self.result_label.setText("Searching...")

        # Setup fetcher thread
        self.thread = QThread()
        if id_type == "TMPID" and len(id_value) > 7:
            print("[CRITICAL]: The TruckersMP ID you gave is invalid,\nswitch to 'SteamID' search from the dropdown menu\nto use a SteamID as input.")
            exit(1)
        self.worker = APIFetcher(id_type, id_value)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_data_received)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_data_received(self, data):
        info = f"""<b>Username:</b> {data.get("name", "N/A")}<br>
<b>SteamID:</b> {data.get("steamID", "N/A")}<br>
<b>Group:</b> {data.get("groupName", "N/A")}<br>
<b>Banned:</b> {"Yes" if data.get("banned", False) else "No"}<br>
<b>Member Since:</b> {data.get("joinDate", "N/A")}<br>
"""
        self.result_label.setText(info)
        self.search_button.setEnabled(True)

    def on_error(self, message):
        QMessageBox.critical(self, "API Error", f"Failed to fetch data:\n{message}")
        self.result_label.setText("Error fetching player data.")
        self.search_button.setEnabled(True)

def main():
    print("[INFO]: Starting the application..")
    app = QApplication(sys.argv)
    currentWorkingDir = os.getcwd()
    window = MyWindow()
    if window.apply_stylesheet_from_file(app, currentWorkingDir + "\\data\\styles.qss") == 1:
        return 1
    window.show()
    app.exec()
    return 0

if __name__ == "__main__":
    result = main()
    if result == 1:
        print("[CRITICAL]: Critical error occurred. Exit code 1.")
        exit(1)
    print("[INFO]: Program exited successfully. Exit code 0.")
    exit(0)
