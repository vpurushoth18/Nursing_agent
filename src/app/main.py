import sys
from PyQt6.QtWidgets import QApplication
from .splash import SplashScreen
from .gui import MainWindow

import warnings
import logging
import transformers
warnings.filterwarnings("ignore")
transformers.logging.set_verbosity_error()
logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)
logging.getLogger("pyannote").setLevel(logging.ERROR)

#show splash screen
#perform initialization
#launch main GUI
class Application:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.main_window = None

        #pass metadata
        self.splash = SplashScreen(self.launch_main_gui)
        self.splash.show()

    def launch_main_gui(self, metadata):
        self.main_window = MainWindow(metadata)
        self.main_window.show()

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    application = Application()
    application.run()