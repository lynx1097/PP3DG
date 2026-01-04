import sys
import os
import ctypes
# 1. Force load the core Windows library that handles DLLs
try:
    ctypes.windll.kernel32.SetDefaultDllDirectories(0x00000800) # LOAD_LIBRARY_SEARCH_DEFAULT_DIRS
except Exception:
    pass

# 2. Manually point Python to the bundled Qt binaries
if getattr(sys, 'frozen', False):
    # If running as EXE
    base_path = sys._MEIPASS
else:
    # If running as script
    base_path = os.path.dirname(__file__)

qt_dir = os.path.join(base_path, "PyQt6", "Qt6", "bin")
if os.path.exists(qt_dir):
    os.add_dll_directory(qt_dir)
# ============================================
# CRITICAL: Set up paths BEFORE any Qt imports
# ============================================
def setup_frozen_environment():
    """Configure environment for PyInstaller frozen app."""
    if getattr(sys, 'frozen', False):
        # Get the bundle directory
        bundle_dir = sys._MEIPASS
        
        # Set Qt plugin paths
        qt_plugins = os.path.join(bundle_dir, 'PyQt6', 'Qt6', 'plugins')
        qt_platforms = os.path.join(qt_plugins, 'platforms')
        
        # Try alternate locations if default doesn't exist
        if not os.path.exists(qt_plugins):
            qt_plugins = os.path.join(bundle_dir, 'qt6_plugins')
        if not os.path.exists(qt_platforms):
            qt_platforms = os.path.join(bundle_dir, 'platforms')
        
        # Set environment variables
        os.environ['QT_PLUGIN_PATH'] = qt_plugins
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_platforms
        
        # Add DLL directories on Windows
        if sys.platform == 'win32':
            os.environ['PATH'] = bundle_dir + os.pathsep + os.environ.get('PATH', '')
            if hasattr(os, 'add_dll_directory'):
                os.add_dll_directory(bundle_dir)
                qt_bin = os.path.join(bundle_dir, 'PyQt6', 'Qt6', 'bin')
                if os.path.exists(qt_bin):
                    os.add_dll_directory(qt_bin)

# Call setup BEFORE importing PyQt6
setup_frozen_environment()

os.environ['QT_API'] = 'pyqt6'

os.environ.pop("QT_PLUGIN_PATH", None)
os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

# Now import everything else
import json
import IDE as code
import VoxelRenderer as vis
from Client import GeminiWorker as gworker
import DiagnosticModule as diag  
import google.generativeai as ai

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QLabel, QTextBrowser, QSplashScreen, QMessageBox, QInputDialog
from PyQt6.QtGui import QFont, QPixmap, QIcon, QMovie
from PyQt6.QtCore import Qt, QTimer, QSize
from pathlib import Path
import tempfile


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running in normal Python environment
        base_path = Path(__file__).parent.parent
    return os.path.join(base_path, relative_path)


# Define path to visual context
CONTEXT_FILE = Path(get_resource_path('visual_context.json'))


class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cube Lab")
        self.setWindowState(Qt.WindowState.WindowMaximized)
        
        self.visual_context_data = self.load_visual_context()
        self.run_startup_diagnostics()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Instantiate widgets
        self.ide_panel = code.SmartIDEWidget()
        self.viz_panel = vis.VoxelViewerWidget()

        # --- CONNECT SIGNALS ---
        self.viz_panel.metadata_shared.connect(self.ide_panel.receive_metadata)
        self.ide_panel.ai_help_requested.connect(self.populate_chat_from_error)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.ide_panel, 1)
        top_layout.addWidget(self.viz_panel, 1)
        
        chat_panel = QWidget()
        chat_layout = QHBoxLayout(chat_panel)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        
        send_panel = QWidget()
        send_panel.setStyleSheet("background-color: darkyellow;")
        send_layout = QVBoxLayout(send_panel)
        
        # --- HEADER ---
        h_chat_header = QHBoxLayout()
        self.send_label = QLabel("CL Assistant ")
        self.send_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        
        self.btn_vision = QPushButton("Where Can I find...?")
        self.btn_vision.setCheckable(True)
        self.btn_vision.setStyleSheet("""
            QPushButton { background-color: #444; color: white; border-radius: 4px; padding: 4px; font-weight: bold; }
            QPushButton:checked { background-color: #2e7d32; border: 1px solid #0f0; }
        """)
        self.btn_vision.setToolTip("Enable Visual UI Guidance Mode")
        
        h_chat_header.addWidget(self.send_label)
        h_chat_header.addStretch()
        h_chat_header.addWidget(self.btn_vision)
        send_layout.addLayout(h_chat_header)
        
        self.send_input = QTextEdit()
        self.send_input.setFont(QFont("Segoe UI", 10))
        self.send_input.setPlaceholderText("Chat with your Assistant")
        send_layout.addWidget(self.send_input)

        self.loading_label = QLabel()
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.hide()
        
        loading_gif = get_resource_path(os.path.join('resources', 'images', 'loading.gif'))
        self.movie = QMovie(loading_gif)
        self.movie.setScaledSize(QSize(40, 30)) 
        self.loading_label.setMovie(self.movie)
        
        self.send_button = QPushButton("Send")
        self.send_button.setFont(QFont("Segoe UI", 10))
    
        self.send_button.clicked.connect(self.agent_request)
        send_layout.addWidget(self.send_button)
        
        self.response_panel = QWidget()
        self.response_panel.setStyleSheet("background-color: darkyellow;")
        response_layout = QVBoxLayout(self.response_panel)
        
        response_label = QLabel("CL Response")
        response_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        response_layout.addWidget(response_label)
        
        self.response_display = QTextBrowser()
        self.response_display.setFont(QFont("Segoe UI", 10))
        self.response_display.setReadOnly(True)
        response_layout.addWidget(self.response_display)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.setFont(QFont("Segoe UI", 10))
        self.clear_button.clicked.connect(self.clear_chat)
        response_layout.addWidget(self.clear_button)
        
        chat_layout.addWidget(send_panel)
        chat_layout.addWidget(self.loading_label)
        chat_layout.addWidget(self.response_panel)
        
        main_layout.addLayout(top_layout, 7)
        main_layout.addWidget(chat_panel, 3)
    
    def load_visual_context(self):
        try:
            if CONTEXT_FILE.exists():
                with open(CONTEXT_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Context Load Error: {e}")
        return None

    def get_relevant_ui_context(self, user_query):
        if not self.visual_context_data: return "{}"
        
        query_words = user_query.lower().split()
        relevant_data = {"relevant_workflows": [], "relevant_ui_elements": []}
        
        data = self.visual_context_data.get('visual_context', {})
        
        workflows = data.get('workflows', {})
        for wf_key, wf_val in workflows.items():
            text_to_search = (wf_val.get('name', '') + " " + wf_val.get('description', '')).lower()
            if any(w in text_to_search for w in query_words):
                relevant_data['relevant_workflows'].append(wf_val)
        
        ui_index = data.get('ui_element_index', {})
        for category, items in ui_index.items():
            if isinstance(items, list):
                for item in items:
                    text_to_search = (str(item.get('label', '')) + " " + str(item.get('action', ''))).lower()
                    if any(w in text_to_search for w in query_words):
                        relevant_data['relevant_ui_elements'].append(item)

        if not relevant_data['relevant_workflows'] and not relevant_data['relevant_ui_elements']:
            return json.dumps(data.get('application_structure', {}), indent=2)
            
        return json.dumps(relevant_data, indent=2)

    def closeEvent(self, event):
        msg = QMessageBox()
        msg.setWindowTitle("Exit Cube Lab")
        msg.setText("Do you want to save the session data before exiting?")
        msg.setInformativeText("Temporary files (RAW outputs, scripts) will be deleted if not saved.")
        msg.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        msg.setDefaultButton(QMessageBox.StandardButton.Save)
        
        ret = msg.exec()

        if ret == QMessageBox.StandardButton.Save:
            self.ide_panel.save_session_dialog()
            self.ide_panel.cleanup_session()
            event.accept()
        elif ret == QMessageBox.StandardButton.Discard:
            self.ide_panel.cleanup_session()
            event.accept()
        else:
            event.ignore()

    def run_startup_diagnostics(self):
        try:
            diag.send_crash_report("Application Started", context="Startup")
        except Exception:
            pass 

    def populate_chat_from_error(self, error_text):
        if len(error_text) > 2000:
            error_text = "...[Truncated]...\n" + error_text[-2000:]
        prompt = f"I encountered the following output/error while running my code. How can I fix this?\n\n```text\n{error_text}\n```"
        self.send_input.setText(prompt)
        self.send_input.setFocus()

    def agent_request(self):
        user_text = self.send_input.toPlainText().strip()
        if not user_text: return

        self.send_button.setEnabled(False)
        self.loading_label.show() 
        self.movie.start()        
        self.response_display.clear()
        
        if self.btn_vision.isChecked():
            pixmap = self.grab()
            tmp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            pixmap.save(tmp_img.name)
            
            ui_context_str = self.get_relevant_ui_context(user_text)
            enhanced_prompt = f"{user_text}\n\n[Context from Application Registry]:\n{ui_context_str}"
            
            self.worker = gworker(enhanced_prompt, use_case="vision", image_path=tmp_img.name)
            self.worker.vision_received.connect(lambda data: self.ide_panel.show_vision_overlay(pixmap, data))
            
        else:
            self.worker = gworker(user_text)
        
        self.worker.response_received.connect(self.handle_agent_response)
        self.worker.error_occurred.connect(self.handle_agent_error)
        self.worker.finished_signal.connect(self.reset_agent_chat)
        
        self.worker.start()

    def handle_agent_response(self, text):
        self.response_display.setMarkdown(text)

    def handle_agent_error(self, error_msg):
        self.response_display.setText(f"Error: {error_msg}")
        diag.send_crash_report(error_msg, context="Agent Error")

    def reset_agent_chat(self):
        self.movie.stop()
        self.loading_label.hide()
        self.send_button.setEnabled(True)
        self.send_input.clear()
        
    def clear_chat(self):
        self.response_display.clear()
    

if __name__ == '__main__':
    diag.register_crash_handler()

    app = QApplication(sys.argv)
    
    splash_path = get_resource_path(os.path.join('resources', 'images', 'Splash.jpg'))
    splash_pix = QPixmap(splash_path)
    splash = QSplashScreen(splash_pix)
    splash.show()
    
    app.processEvents()
    
    icon_path = get_resource_path(os.path.join('resources', 'images', 'Icon.ico'))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))        
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    viewer = MainWindow()
    QTimer.singleShot(2000, lambda: (splash.finish(viewer), viewer.show()))
    
    sys.exit(app.exec())
