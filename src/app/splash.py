from PyQt6.QtWidgets import QWidget, QLabel, QProgressBar, QVBoxLayout
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from pipeline.splash_backend import get_environment_metadata, verify_and_download
import time
#detects hardware, verifies models, and captures metadata without freezing the GUI
class InitWorker(QThread):
    status_update = pyqtSignal(str, int)
    finished = pyqtSignal(dict)

    def run(self):
        #hardware and environment detection
        self.status_update.emit("Capturing environment metadata...", 20)
        metadata = get_environment_metadata()
        time.sleep(1)
        #verify whisper
        self.status_update.emit("Verifying ASR artifacts...", 40)
        verify_and_download("whisper_small")
        time.sleep(1)
        #verify LLM
        self.status_update.emit("Verifying LLM artifacts...", 80)
        verify_and_download("qwen_0_5b")
        time.sleep(1)
        #finalize
        self.status_update.emit("Preparing deterministic runtime...", 95)
        self.finished.emit(metadata)

class SplashScreen(QWidget):
    def __init__(self, on_complete_callback):
        super().__init__()
        self.on_complete_callback = on_complete_callback

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("NurseAssist | Joel Molina")
        self.setFixedSize(400,250)

        #styling
        self.setStyleSheet("""
            QWidget {
                background-color: #010B30;
                color: white;
                border-radius: 10px;
            }
            QLabel#Title {
                font-size: 28px;
                font-weight: bold;
                margin-top: 20px;
            }
            QLabel#Author {
                font-size: 12px;
                margin-top: 20px;
                color: white;    
                margin-bottom: 40px;  
            }
            QLabel#Status {
                font-size: 14px;
                color: #d1d9e0;
                margin-bottom: 5px;
            }
            QProgressBar {
                border: 2px solid #2c3e50;
                border-radius: 5px;
                text-align: center;
                background-color: #2c3e50;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4facfe;
                width: 10px;
            }
        """)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel("NurseAssist")
        self.title_label.setObjectName("Title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.author_label = QLabel("Joel Molina")
        self.author_label.setObjectName("Author")
        self.author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("Initializing...")
        self.status_label.setObjectName("Status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        layout.addWidget(self.title_label)
        layout.addWidget(self.author_label)
        layout.addStretch()
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)
        
        #run backend
        self.worker = InitWorker()
        self.worker.status_update.connect(self.handle_status)
        self.worker.finished.connect(self.handle_finished)
        self.worker.start()

    def handle_status(self, text, value):
        self.status_label.setText(text)
        self.progress_bar.setValue(value)

    def handle_finished(self, metadata):
        #pass metadata to main GUI
        self.on_complete_callback(metadata)
        self.close()
