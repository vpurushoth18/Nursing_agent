from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QWidget, 
    QVBoxLayout, QLabel, QPushButton, QFileDialog, QTextEdit, QMessageBox, QProgressBar
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import subprocess
import sys
import json
import shutil
import os

#worker class for backend
class Worker(QThread):
    finished = pyqtSignal(dict) #signal that sends results back to GUI
    progress_update = pyqtSignal(int)

    def __init__(self, audio_path, rubric_path):
        super().__init__()
        self.audio_path = audio_path
        self.rubric_path = rubric_path
        self.internal_output = "temp_graded_report.docx"


    def run(self):
        #transcription
        self.progress_update.emit(10)
        subprocess.run([sys.executable, "-m", "pipeline.asr", self.audio_path], check=True)
        self.progress_update.emit(70)

        #scoring
        self.progress_update.emit(70)
        subprocess.run([
            sys.executable, "-m", "pipeline.scoring",
            "temp_asr_output.json", self.rubric_path, self.internal_output
        ], check=True)

        #load data for GUI
        with open("temp_asr_output.json", "r") as f:
            data = json.load(f)
        
        self.progress_update.emit(100)
        self.finished.emit({
            "transcript": data["text"],
            "metadata": data["metadata"],
            "file_ready": self.internal_output
        })

# Worker class for reproducibility verification
class VerifierWorker(QThread):
    finished = pyqtSignal(dict)
    progress_update = pyqtSignal(int)

    def __init__(self, audio_path, rubric_path):
        super().__init__()
        self.audio_path = audio_path
        self.rubric_path = rubric_path

    def run(self):
        self.progress_update.emit(10)
        subprocess.run([sys.executable, "-m", "pipeline.verifier", self.audio_path, self.rubric_path], check=True)
        self.progress_update.emit(90)

        with open("verified_master_report.json", "r") as f:
            result = json.load(f)
        
        self.progress_update.emit(100)
        self.finished.emit(result)



class MainWindow(QMainWindow):
    def __init__(self, metadata):
        super().__init__()
        self.metadata = metadata

        #create basic size and title
        self.setWindowTitle("NurseAssist")
        self.resize(1000,800)

        #styling
        self.setStyleSheet("""
    QMainWindow {
        background-color: #010B30;
    }
    QTabWidget::pane {
        border: 2px solid black;
        background-color: #010B30;
    }
    QTabBar::tab {
        background: #05164d;
        color: #d1d9e0;
        padding: 15px 30px;
        font-size: 14px;
        font-weight: bold;
        min-width:188px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background: #1a2a6c;
        color: white;
        border-bottom: 3px solid #4facfe;
    }
    QWidget#InputTab {
        background-color: #010B30;
    }
    QLabel {
        color: white;
        font-size: 16px;
    }
    QPushButton {
        background-color: #1a2a6c;
        color: white;
        border: 1px solid #4facfe;
        border-radius: 8px;
        padding: 20px;
        font-size: 18px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #2a3a7c;
        border: 2px solid #4facfe;
    }
    QProgressBar {
        border: 1px solid #4facfe;
        border-radius: 5px;
        text-align: center;
        background-color: #05164d;
        color: white;
        height: 30px;
        font-weight: bold;
    }
    QProgressBar::chunk {
        background-color: #4facfe;
    }
""")

        #set tabs as central widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        #initialize input document paths
        self.audio_path = None
        self.rubric_path = None

        self.create_input_tab()
        self.create_transcript_tab()
        self.create_rubric_tab()
        self.create_forensic_tab()

    
    def create_input_tab(self):
        self.input_tab = QWidget()
        self.input_tab.setObjectName("InputTab")
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(60,40,60,40)
        input_layout.setSpacing(20)

        #header
        header = QLabel("Clinical Assessment Input")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #4facfe;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        input_layout.addWidget(header)
        input_layout.addStretch(1)

        #audio section
        self.audio_label = QLabel("No audio file selected.")
        self.audio_label.setStyleSheet("color: white; font-style: italic")
        self.audio_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.audio_button = QPushButton("Select Audio File (mp3)")
        self.audio_button.clicked.connect(self.select_audio)

        #rubric section
        self.rubric_label = QLabel("No rubric file selected.")
        self.rubric_label.setStyleSheet("color: white; font-style: italic;")
        self.rubric_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rubric_button = QPushButton("Select rubric (DOCX)")
        self.rubric_button.clicked.connect(self.select_rubric)

        #run section
        self.run_button = QPushButton("Begin Grading")
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                border: none;
                font-size: 22px;
            }
            QPushButton:hover { background-color: #218838 }
        """)                   
        self.run_button.clicked.connect(self.run_pipeline)

        #progress bar
        self.progress_bar = QProgressBar()

        input_layout.addStretch(1)
        input_layout.addWidget(self.audio_button)
        input_layout.addWidget(self.audio_label)
        input_layout.addStretch(1)
        input_layout.addWidget(self.rubric_button)
        input_layout.addWidget(self.rubric_label)
        input_layout.addStretch(2)
        input_layout.addWidget(self.run_button)
        input_layout.addWidget(self.progress_bar)
        input_layout.addStretch(1)

        self.input_tab.setLayout(input_layout)
        self.tabs.addTab(self.input_tab, "Input")


    def create_transcript_tab(self):
        self.transcript_tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20,20,20,20)

        self.transcript_output = QTextEdit()
        self.transcript_output.setReadOnly(True)

        #placeholder
        self.transcript_output.setPlaceholderText(
            "The assessment transcript will appear here automatically after you click 'Begin Grading'..."
        )

        self.transcript_output.setStyleSheet("""
        QTextEdit {
            background-color: #010B30;
            color: #d1d9e0;
            border: 1px solid #4facfe;
            border-radius: 8px;
            font-size: 14px;
            padding: 15px;
        }
    """)

        layout.addWidget(self.transcript_output)
        self.transcript_tab.setLayout(layout)
        self.tabs.addTab(self.transcript_tab, "Transcription")

    def create_forensic_tab(self):
        self.forensic_tab = QWidget()
        layout = QVBoxLayout()

        self.export_button = QPushButton("Download Master Artifact (.json)")
        self.export_button.setEnabled(False)
        self.export_button.setStyleSheet(("""
            QPushButton { background-color: #1a2a6c; border: 1px solid #4facfe; font-size: 14px; }
            QPushButton:hover { background-color: #2a3a7c; }
        """))
        self.export_button.clicked.connect(self.export_master_log)

        self.forensic_display = QTextEdit()
        self.forensic_display.setReadOnly(True)
        self.forensic_display.setPlaceholderText("Forensic record will appear here after grading...")
        self.forensic_display.setStyleSheet("""
            QTextEdit {
                background-color: #010B30; color: #00ff41; border: 1px solid #4facfe;
                font-family: 'Consolas', monospace; font-size: 12px; padding: 15px;
            }
        """)

        self.verify_progress = QProgressBar()
        self.verify_progress.hide()

        self.verify_button = QPushButton("Verify Reproducibility (Rerun & Hash)")
        self.verify_button.setEnabled(False)
        self.verify_button.clicked.connect(self.run_verifier) 
        self.verify_button.setStyleSheet("""
            QPushButton { background-color: #010B30; border: 2px solid #ff4500; font-size: 16px; color: #ff4500;}
            QPushButton:hover { background-color: #ff4500; color: white;}
        """)

        layout.addWidget(QLabel("<b>Forensic Chain of Custody</b>"))
        layout.addWidget(self.export_button)
        layout.addWidget(self.forensic_display)
        layout.addWidget(self.verify_progress)
        layout.addWidget(self.verify_button)
        self.forensic_tab.setLayout(layout)
        self.tabs.addTab(self.forensic_tab, "Forensics")


    def export_master_log(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Master Artifact", "Master_Audit_Log.json", "JSON Files (*.json)")
        if save_path:
            master_doc = {"COMBINED_AUDIT_LOGS": {}}
            for log_file in ["asr_forensic_log.json", "speaker_id_forensic_log.json", "forensic_log.json"]:
                if os.path.exists(log_file):
                    with open(log_file, "r") as f:
                        master_doc["COMBINED_AUDIT_LOGS"][log_file.split('.')[0]] = json.load(f)
            
            with open(save_path, "w") as f:
                json.dump(master_doc, f, indent=4)
            QMessageBox.information(self, "Success", f"Master Artifact saved to:\n{save_path}")

    def run_verifier(self):
        self.verify_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.verify_progress.show()
        self.forensic_display.append("\n[SYSTEM] Initializing isolated reproducible verification run...")

        self.verify_worker = VerifierWorker(self.audio_path, self.rubric_path)
        self.verify_worker.progress_update.connect(self.verify_progress.setValue)
        self.verify_worker.finished.connect(self.on_verifier_finished)
        self.verify_worker.start()

    def create_rubric_tab(self):
        self.rubric_tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(15)


        self.rubric_output = QTextEdit()
        self.rubric_output.setReadOnly(True)
        self.rubric_output.setPlaceholderText("Graded results will appear here after generating report..")

        self.rubric_output.setStyleSheet("""
            QTextEdit {
                background-color: #010B30;
                color: #d1d9e0;
                border: 1px solid #4facfe;
                border-radius: 8px;
                font-size: 14px;
                padding: 15px;
                line-height: 1.6;
            }
        """)

        self.download_button = QPushButton("Download Graded Rubric (.docx)")
        self.download_button.setEnabled(False)
        self.download_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #1a2a6c;
                color: white;
                border: 2px solid #4facfe;
                border-radius: 8px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a3a7c;
            }
            QPushButton:disabled {
                background-color: #05164d;
                border: 1px solid #2c3e50;
                color: #555;
            }
        """)

        layout.addWidget(self.rubric_output)
        layout.addWidget(self.download_button)
        self.rubric_tab.setLayout(layout)
        self.tabs.addTab(self.rubric_tab, "Rubric Output")

        self.download_button.clicked.connect(self.run_scoring)

    def run_scoring(self):
        #download button action
        import shutil
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Download Graded Rubric", "Graded_Assessment.docx", "Word Files (*.docx)"
        )

        if save_path:
            #move file already created in backend
            shutil.copy("temp_graded_report.docx", save_path)
            self.rubric_output.setText(f"File saved to: \n{save_path}")

    
    def select_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio files (*.wav *.mp3 *.mp4 *.m4a)"
        )
        if file_path:
            self.audio_path = file_path
            self.audio_label.setText(file_path)

    
    def select_rubric(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Rubric File",
            "",
            "Documents (*.pdf, *.docx)"
        )
        if file_path:
            self.rubric_path = file_path
            self.rubric_label.setText(file_path)


    def run_pipeline(self):
        if not self.audio_path or not self.rubric_path:
            self.transcript_output.setText("Please select both audio and rubric files.")
            return
        
        #show loading once the run button is pressed. 
        self.run_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.progress_bar.show()
        self.transcript_output.setText("Transcribing... please wait")

        #start background thread
        self.worker = Worker(self.audio_path, self.rubric_path)
        self.worker.progress_update.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_pipeline_finished)
        self.worker.start()
        
    
    def on_pipeline_finished(self, results):
        #once ASR model is done
        self.run_button.setEnabled(True)
        self.download_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.verify_button.setEnabled(True)
        self.progress_bar.hide()

        #display transcript in transcript tab.
        transcript_text = results["transcript"]
        self.transcript_output.setText(transcript_text)

        #update forensic tab with recorded metadata
        with open("forensic_log.json", "r") as f:
            log_data = json.load(f)
        readable_log = json.dumps(log_data, indent=4)
        self.forensic_display.setText(readable_log)

    def on_verifier_finished(self, result):
            self.verify_button.setEnabled(True)
            self.export_button.setEnabled(True)
            self.verify_progress.hide()

            cert = result.get("REPRODUCIBILITY_CERTIFICATE", {})
            status = cert.get("result", "ERROR")
            diagnostics = cert.get("diagnostics", [])

            color = "#00ff41" if status == "PASS" else "#ff0000"

            self.forensic_display.append(f"\n<span style='color:{color}; font-size: 16px; font-weight:bold;'>[VERIFICATION COMPLETE] Status: {status}</span>")

            if diagnostics:
                self.forensic_display.append("<span style='color:#ff0000;'>Diagnostics / Failures:</span>")
                for d in diagnostics:
                    self.forensic_display.append(f"<span style='color:#ffaa00;'> - {d}</span>")
            else:
                self.forensic_display.append("<span style='color:#00ff41;'>All cryptographic hashes matched perfectly. Zero environment drift.</span>")

            self.forensic_display.append("\nYou can now download the VERIFIED master document.")

            #prompt to save document
            save_path, _ = QFileDialog.getSaveFileName(self, "Save Verified Artifact", "Verified_Master_Report.json", "JSON Files (*.json)")
            if save_path:
                shutil.copy("verified_master_report.json", save_path)
                QMessageBox.information(self, "Success", f"Verified Artifact saved to:\n{save_path}")