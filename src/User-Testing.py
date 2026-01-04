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
os.environ["PYTHONIOENCODING"] = "utf-8"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    
# Now import everything else
import json
import time
import datetime
import platform
import uuid
from functools import partial

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QLineEdit, QDialog, QFormLayout, QFrame, 
    QScrollArea, QCheckBox, QProgressBar, QMessageBox, QComboBox,
    QSizePolicy, QListWidget
)
from PyQt6.QtCore import Qt, QTimer, QObject, QEvent, pyqtSignal, QPoint, QSize, QPropertyAnimation, QParallelAnimationGroup
from PyQt6.QtGui import QColor, QPalette, QPainter, QPen, QBrush, QIcon

# IMPORT YOUR EXISTING MODULES
import GUI
import DiagnosticModule as diag


# --- CONFIGURATION WITH STEPS ---
TASKS_CONFIG = [
    {
        "id": "T1", 
        "name": "Ask the Assistant", 
        "desc": "Ask AI about analysis types",
        "steps": [
            "1. Locate the 'CL Assistant' panel at the bottom left.",
            "2. Type a question like 'How do I filter noise?'",
            "3. Click 'Send' and wait for the response."
        ]
    },
    {
        "id": "T2", 
        "name": "Load and View Data", 
        "desc": "Load sample .raw file",
        "steps": [
            "1. In the 3D Viewer (right panel), click 'Open sample'.",
            "2. Select a .raw file from your disk.",
            "3. Enter dimensions (e.g., 391, 391, 430) and encoding 'uint-8' when prompted , you should see a green OK.",
            "4. Verify the 3D volume renders correctly."
        ]
    },
    {
        "id": "T3", 
        "name": "Create a Subroutine", 
        "desc": "Add new subroutine in IDE",
        "steps": [
            "1. Go to the 'Subroutines' tab (top left).",
            "2. Click the '+ Add New Subroutine' button.",
            "3. Verify a new subroutine block appears."
        ]
    },
    {
        "id": "T4", 
        "name": "Add/Config Function", 
        "desc": "Add 'Basic Analysis' function",
        "steps": [
            "1. Inside the subroutine, click '+ Func'.",
            "2. Find and select 'p3dBasicAnalysis'.",
            "3. Click 'Add Function'.",
            "4. Fill in the required parameters (e.g., dimensions)."
        ]
    },
    {
        "id": "T5", 
        "name": "Adjust Visualization", 
        "desc": "Change mode/opacity & Snapshot",
        "steps": [
            "1. Open the floating 'Controls' panel in the viewer.",
            "2. Change 'Rendering Mode' (e.g., to Vol-CT).",
            "3. Adjust the Opacity slider.",
            "4. Click 'Snapshot' to save an image."
        ]
    },
    {
        "id": "T6", 
        "name": "Switch to IDE View", 
        "desc": "Check generated code",
        "steps": [
            "1. Click the 'IDE' tab (next to Subroutines).",
            "2. Review the Python code generated automatically.",
            "3. Verify the imports and function calls match your actions."
        ]
    },
    {
        "id": "T7", 
        "name": "Complete Workflow", 
        "desc": "Add Anisotropy & Save",
        "steps": [
            "1. Go back to 'Subroutines'.",
            "2. Add 'p3dAnisotropyAnalysis'.",
            "3. Link its input to the previous function's output.",
            "4. Click 'Save' in the main toolbar."
        ]
    }
]

class UserIntakeDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Usability Test Setup")
        self.setModal(True)
        self.setFixedSize(450, 350)
        self.user_data = {}
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.inp_name = QLineEdit()
        self.inp_email = QLineEdit()
        
        self.inp_age = QComboBox()
        self.inp_age.addItems(["", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"])
        
        self.inp_prof = QComboBox()
        self.inp_prof.addItems([
            "", "Student", "General Researcher", "Biologist", "Pharmacist",
            "Physician-Medical", "Material Scientist", "Physicist", "Chemist", 
            "Developer", "Geologist", "Other"
        ])
        
        form.addRow("Name (Optional):", self.inp_name)
        form.addRow("Email (Optional):", self.inp_email)
        form.addRow("Age Range (Required):", self.inp_age)
        form.addRow("Profession (Required):", self.inp_prof)
        
        layout.addLayout(form)
        
        self.btn_start = QPushButton("Start Test")
        self.btn_start.clicked.connect(self.validate)
        self.btn_start.setStyleSheet("background-color: #007acc; color: white; padding: 10px; font-weight: bold;")
        layout.addWidget(self.btn_start)

    def validate(self):
        if not self.inp_prof.currentText():
            QMessageBox.warning(self, "Missing Info", "Profession field is required.")
            return
        if not self.inp_age.currentText():
            QMessageBox.warning(self, "Missing Info", "Age Range is required.")
            return
        
        self.user_data = {
            "name": self.inp_name.text(),
            "email": self.inp_email.text(),
            "age_range": self.inp_age.currentText(),
            "profession": self.inp_prof.currentText(),
            "timestamp": datetime.datetime.now().isoformat(),
            "system": {
                "os": platform.system(),
                "release": platform.release(),
                "machine": platform.machine()
            }
        }
        self.accept()

class TaskWidget(QFrame):
    def __init__(self, task_data, parent_controller):
        super().__init__()
        self.data = task_data
        self.controller = parent_controller
        self.start_time = None
        self.is_active = False
        self.is_completed = False
        self.details_visible = False
        
        self.setStyleSheet("background-color: #2d2d2d; border-radius: 5px; margin-bottom: 2px;")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5,5,5,5)
        self.main_layout.setSpacing(0)
        
        # --- Header Row ---
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0,0,0,0)
        
        self.btn_expand = QPushButton("▶")
        self.btn_expand.setFixedSize(20, 20)
        self.btn_expand.setStyleSheet("border: none; color: #aaa; font-size: 10px;")
        self.btn_expand.clicked.connect(self.toggle_details)
        
        self.lbl_status = QLabel("⬜") 
        self.lbl_name = QLabel(f"<b>{task_data['id']}</b>: {task_data['name']}")
        self.lbl_name.setStyleSheet("color: white;")
        
        self.btn_action = QPushButton("Start")
        self.btn_action.setFixedSize(60, 25)
        self.btn_action.setStyleSheet("background-color: #007acc; color: white; border: none; border-radius: 3px;")
        self.btn_action.clicked.connect(self.toggle_task)
        
        h_layout.addWidget(self.btn_expand)
        h_layout.addWidget(self.lbl_status)
        h_layout.addWidget(self.lbl_name)
        h_layout.addStretch()
        h_layout.addWidget(self.btn_action)
        self.main_layout.addWidget(header)
        
        # --- Details Row (Collapsible) ---
        self.details_frame = QFrame()
        self.details_frame.setVisible(False)
        d_layout = QVBoxLayout(self.details_frame)
        d_layout.setContentsMargins(30, 5, 5, 5) # Indent
        
        for step in task_data.get('steps', []):
            s_lbl = QLabel(step)
            s_lbl.setWordWrap(True)
            s_lbl.setStyleSheet("color: #ccc; font-size: 11px;")
            d_layout.addWidget(s_lbl)
            
        self.main_layout.addWidget(self.details_frame)

    def toggle_details(self):
        self.details_visible = not self.details_visible
        self.details_frame.setVisible(self.details_visible)
        self.btn_expand.setText("▼" if self.details_visible else "▶")

    def toggle_task(self):
        if self.is_completed: return
        
        if not self.is_active:
            self.controller.start_task(self.data['id'])
            self.start_task_ui()
        else:
            self.controller.stop_task(self.data['id'], manual=True)
            self.finish_task_ui()

    def start_task_ui(self):
        self.is_active = True
        self.start_time = time.time()
        self.btn_action.setText("Stop")
        self.btn_action.setStyleSheet("background-color: #d32f2f; color: white;")
        self.lbl_status.setText("⏳") 
        # Auto expand details when started
        if not self.details_visible: self.toggle_details()

    def finish_task_ui(self):
        self.is_active = False
        self.is_completed = True
        self.btn_action.setText("Done")
        self.btn_action.setEnabled(False)
        self.btn_action.setStyleSheet("background-color: #388e3c; color: white;")
        self.lbl_status.setText("✅")
        # Auto collapse when done
        if self.details_visible: self.toggle_details()
        
    def auto_complete(self):
        if self.is_active:
            self.controller.stop_task(self.data['id'], manual=False)
            self.finish_task_ui()

class TaskOverlay(QWidget):
    submit_requested = pyqtSignal() # New signal

    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)
        
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 245);
                border: 1px solid #555;
                border-radius: 10px;
                color: white;
            }
        """)
        self.container_layout = QVBoxLayout(self.container)
        
        # Header
        header = QHBoxLayout()
        lbl = QLabel("📋 Usability Tasks")
        lbl.setStyleSheet("font-weight: bold; font-size: 14px; background: transparent; border: none;")
        self.btn_min = QPushButton("-")
        self.btn_min.setFixedSize(20,20)
        self.btn_min.clicked.connect(self.toggle_minimize)
        self.btn_min.setStyleSheet("background: transparent; border: 1px solid #666; border-radius: 10px; color: white;")
        
        header.addWidget(lbl)
        header.addStretch()
        header.addWidget(self.btn_min)
        self.container_layout.addLayout(header)
        
        # Scroll Area for Tasks
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.tasks_list_widget = QWidget()
        self.tasks_list_widget.setStyleSheet("background: transparent;")
        self.tasks_layout = QVBoxLayout(self.tasks_list_widget)
        self.tasks_layout.setContentsMargins(0,0,0,0)
        self.tasks_layout.setSpacing(2)
        
        self.task_widgets = {}
        self.current_active_id = None
        
        for t_conf in TASKS_CONFIG:
            w = TaskWidget(t_conf, self)
            self.tasks_layout.addWidget(w)
            self.task_widgets[t_conf['id']] = w
            
        self.scroll.setWidget(self.tasks_list_widget)
        self.container_layout.addWidget(self.scroll)
        
        # --- NEW: SUBMIT BUTTON ---
        self.btn_submit = QPushButton("Submit Test Results")
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32; 
                color: white; 
                font-weight: bold; 
                padding: 8px; 
                border-radius: 5px;
                margin-top: 5px;
            }
            QPushButton:hover { background-color: #388e3c; }
        """)
        self.btn_submit.clicked.connect(self.submit_clicked)
        self.container_layout.addWidget(self.btn_submit)

        self.main_layout.addWidget(self.container)
        
        self.is_minimized = False
        self.resize(320, 500)
        self.show()

    def start_task(self, task_id):
        if self.current_active_id and self.current_active_id != task_id:
            prev = self.task_widgets[self.current_active_id]
            if prev.is_active:
                prev.is_active = False 
                prev.btn_action.setText("Start")
                prev.btn_action.setStyleSheet("background-color: #007acc; color: white;")
                prev.lbl_status.setText("⬜")
                
        self.current_active_id = task_id
        logger.log_system_event(f"Task Started: {task_id}")

    def stop_task(self, task_id, manual=True):
        if self.current_active_id == task_id:
            self.current_active_id = None
        
        w = self.task_widgets[task_id]
        duration = time.time() - w.start_time if w.start_time else 0
        logger.log_system_event(f"Task Completed: {task_id} (Manual: {manual}, Duration: {duration:.2f}s)")
        logger.record_task_success(task_id, duration)

    def toggle_minimize(self):
        if self.is_minimized:
            self.scroll.show()
            self.btn_submit.show()
            self.resize(320, 500)
            self.btn_min.setText("-")
        else:
            self.scroll.hide()
            self.btn_submit.hide()
            self.resize(320, 50)
            self.btn_min.setText("+")
        self.is_minimized = not self.is_minimized
        
    def submit_clicked(self):
        self.submit_requested.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

# --- GLOBAL LOGGER ---
class BigBrotherLogger(QObject):
    def __init__(self):
        super().__init__()
        self.log_data = []
        self.task_results = {}
        self.session_start = time.time()
        
    def eventFilter(self, obj, event):
        if not QApplication.activeWindow():
            return False
            
        etype = event.type()
        if etype in [QEvent.Type.MouseMove, QEvent.Type.Paint, QEvent.Type.Timer, QEvent.Type.HoverMove]:
            return False
            
        if etype in [QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress, QEvent.Type.FocusIn]:
            self.log_interaction(obj, event)
            
        return False

    def log_interaction(self, obj, event):
        try:
            widget_name = obj.objectName() if hasattr(obj, 'objectName') else "Unknown"
            widget_type = type(obj).__name__
            parent = obj.parent()
            parent_name = parent.objectName() if parent and hasattr(parent, 'objectName') else "Root"
            
            details = ""
            if event.type() == QEvent.Type.KeyPress:
                details = f"Key: {event.key()}"
            elif event.type() == QEvent.Type.MouseButtonPress:
                details = "Click"
                if isinstance(obj, QPushButton): details += f" '{obj.text()}'"

            entry = {
                "timestamp": time.time(),
                "type": "interaction",
                "widget": widget_name,
                "class": widget_type,
                "parent": parent_name,
                "details": details
            }
            self.log_data.append(entry)
        except: pass

    def log_system_event(self, message):
        self.log_data.append({
            "timestamp": time.time(),
            "type": "system",
            "message": message
        })

    def record_task_success(self, task_id, duration):
        self.task_results[task_id] = {
            "completed": True,
            "duration": duration
        }

    def compile_report(self, user_info, ide_ref, console_ref):
        report = {
            "user": user_info,
            "session_duration": time.time() - self.session_start,
            "tasks": self.task_results,
            "logs": self.log_data,
            "context": {
                "generated_code": ide_ref.editor.text() if ide_ref else "N/A",
                "console_output": console_ref.toPlainText() if console_ref else "N/A"
            }
        }
        return json.dumps(report, indent=2)

logger = BigBrotherLogger()

class TestManager:
    def __init__(self, main_win, overlay, intake_data):
        self.win = main_win
        self.overlay = overlay
        self.intake_data = intake_data
        
        # Connect Submit
        self.overlay.submit_requested.connect(self.finish_test)
        self.connect_signals()

    def connect_signals(self):
        self.win.send_button.clicked.connect(lambda: self.check_auto_complete("T1"))
        self.win.viz_panel.metadata_shared.connect(lambda: self.check_auto_complete("T2"))
        self.win.ide_panel.btn_add_sub.clicked.connect(lambda: self.check_auto_complete("T3"))
        self.win.ide_panel.editor.textChanged.connect(self.check_function_added)
        
        if hasattr(self.win.viz_panel, 'panel') and self.win.viz_panel.panel:
             self.win.viz_panel.panel.btn_snap.clicked.connect(lambda: self.check_auto_complete("T5"))
        
        self.win.ide_panel.tabs.currentChanged.connect(self.check_tab_switch)
        self.win.ide_panel.btn_save.clicked.connect(lambda: self.check_auto_complete("T7"))

    def check_auto_complete(self, task_id):
        if self.overlay.current_active_id == task_id:
            self.overlay.task_widgets[task_id].auto_complete()

    def check_function_added(self):
        if self.overlay.current_active_id == "T4":
            if "<CLST_FUNC" in self.win.ide_panel.editor.text():
                self.check_auto_complete("T4")

    def check_tab_switch(self, index):
        if self.overlay.current_active_id == "T6" and index == 1:
            self.check_auto_complete("T6")
            
    def finish_test(self):
        # 1. Disable Interactions
        self.overlay.btn_submit.setText("Sending Data...")
        self.overlay.btn_submit.setEnabled(False)
        self.win.setEnabled(False) # Freeze GUI
        QApplication.processEvents()
        
        # 2. Compile Data
        print("Compiling Usability Report...")
        console_widget = None
        try:
            if self.win.ide_panel.subroutines:
                console_widget = self.win.ide_panel.subroutines[0].console.console
        except: pass
        
        report_payload = logger.compile_report(
            self.intake_data, 
            self.win.ide_panel, 
            console_widget
        )
        
        # 3. Send
        print("Sending to New Relic...")
        try:
            diag.send_crash_report("Usability Test Data (SUBMITTED)", context=report_payload)
            QMessageBox.information(self.win, "Test Complete", "Thank you! Data sent successfully.")
        except Exception as e:
            QMessageBox.critical(self.win, "Error", f"Failed to send data: {e}")
        
        # 4. Exit
        self.win.close()
        sys.exit(0)

def main():
    app = QApplication(sys.argv)
    
    intake = UserIntakeDialog()
    if intake.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)
    
    main_win = GUI.MainWindow()
    main_win.show()
    app.processEvents()
    
    app.installEventFilter(logger)
    
    overlay = TaskOverlay(main_win)
    
    # Pass intake data to manager for final report
    manager = TestManager(main_win, overlay, intake.user_data)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()