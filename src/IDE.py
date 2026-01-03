import sys
import json
import re
import os
import uuid
import subprocess
import shutil
import tempfile
import datetime
import ast
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFileDialog, QTabWidget, QMessageBox, QLabel,
    QFrame, QToolTip, QStyle, QScrollArea, QLineEdit, QSpinBox,
    QDoubleSpinBox, QCheckBox, QComboBox, QListWidget, QDialog,
    QGridLayout, QToolButton, QSizePolicy, QGraphicsOpacityEffect,
    QTextEdit, QInputDialog, QTextBrowser
)
from PyQt6.QtGui import QColor, QFont, QDrag, QIcon, QAction, QPixmap, QPainter, QPen, QCursor
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QMimeData, QSize, QPropertyAnimation, QEasingCurve, QPoint, QByteArray

from PyQt6.Qsci import (
    QsciScintilla, QsciLexerPython, QsciLexerCPP, QsciAPIs
)

# Import the updated Client Worker
try:
    from Client import GeminiWorker
except ImportError:
    print("Warning: Client.py not found. AI features will not work.")
    GeminiWorker = None

PARSING_RULES = """
IMPORTANT: 
1. The code MUST strictly adhere to this structure for the visualizer to work:
   # <CLST_SUBROUTINE name="SubName"> ... # </CLST_SUBROUTINE>
   # <CLST_FUNC id="..."> ... # </CLST_FUNC>
2. DO NOT remove these tags.
3. For every line you change or fix, append a python comment explain WHY, e.g.: 
   x = x + 1 # FIX: Corrected increment logic
"""

class SessionManager:
    def __init__(self):
        self.session_id = str(uuid.uuid4())[:8]
        self.session_dir = os.path.join(tempfile.gettempdir(), f"CubeLab_Session_{self.session_id}")
        if not os.path.exists(self.session_dir): os.makedirs(self.session_dir)
    def get_path(self, filename): return os.path.join(self.session_dir, filename)
    def save_session_to(self, dest_dir):
        if not os.path.exists(self.session_dir): return
        try:
            if not os.path.exists(dest_dir): os.makedirs(dest_dir)
            for item in os.listdir(self.session_dir):
                s = os.path.join(self.session_dir, item); d = os.path.join(dest_dir, item)
                if os.path.isdir(s): shutil.copytree(s, d, dirs_exist_ok=True)
                else: shutil.copy2(s, d)
            return True
        except: return False
    def cleanup(self):
        if os.path.exists(self.session_dir):
            try: shutil.rmtree(self.session_dir)
            except: pass

session = SessionManager()

class FunctionLibrary:
    def __init__(self, json_data):
        self.raw_data = json_data
        self.functions = {fn['function_call']: fn for fn in json_data['pypore3d_function_reference']['functions']}
        self.id_map = {fn['id']: fn for fn in json_data['pypore3d_function_reference']['functions']}
        self.categories = set(); self.modules = set()
        for fn in self.functions.values(): self.categories.add(fn['metadata']['category']); self.modules.add(fn['metadata']['module'])
    def get_filtered_functions(self, category=None):
        results = []
        for fn in self.functions.values():
            if category and category != "Sort By : " and fn['metadata']['category'] != category and fn['metadata']['module'] != category: continue
            results.append(fn)
        return results
global_library = None

class Theme:
    DARK = { "app_bg": "#1e1e1e", "panel_bg": "#252526", "card_bg": "#333333", "sub_bg": "#2d2d2d", "text_main": "#e0e0e0", "text_dim": "#aaaaaa", "accent": "#007acc", "accent_hover": "#0098ff", "danger": "#d32f2f", "input_bg": "#3c3c3c", "border": "#454545", "success": "#388e3c", "toast_bg": "#333333", "toast_border": "#007acc" }

class OverlayButton(QPushButton):
    def __init__(self, parent, tooltip, icon_path="ai_help.png", color="#9c27b0"):
        super().__init__(parent)
        self.setFixedSize(60, 60); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setToolTip(tooltip)
        icon_full_path = str(Path(__file__).parent.parent / 'resources' / 'images' / icon_path)
        if os.path.exists(icon_full_path): self.setIcon(QIcon(icon_full_path))
        else: self.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.setIconSize(QSize(32, 32))
        self.setStyleSheet(f"QPushButton {{ background-color: {color}; border-radius: 30px; border: 2px solid {Theme.DARK['panel_bg']}; }} QPushButton:hover {{ background-color: white; border-color: {color}; }} QPushButton:pressed {{ background-color: {Theme.DARK['success']}; }}")
        shadow = QGraphicsOpacityEffect(self); self.setGraphicsEffect(shadow); shadow.setOpacity(0.9)

    def update_position(self):
        if not self.parent(): return
        p_rect = self.parent().rect()
        y_offset = 80 
        parent_obj = self.parent()
        has_statusbar = False
        if isinstance(parent_obj, QWidget):
            for child in parent_obj.children():
                if isinstance(child, QFrame) and child.height() == 35: has_statusbar = True; break
        if has_statusbar: y_offset += 35 
        x = p_rect.width() - self.width() - 80; y = p_rect.height() - self.height() - y_offset
        self.move(x, y); self.raise_()

# --- REDESIGNED VISION RESULT WINDOW ---
class VisionOverlay(QDialog):
    """
    Standard resizeable dialog showing marked-up screenshot and scrollable text.
    Replaces the old full-screen transparent overlay.
    """
    def __init__(self, screenshot_pixmap, analysis_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Visual Guide")
        self.resize(900, 700)
        self.setStyleSheet(f"background-color: {Theme.DARK['app_bg']}; color: white;")
        
        layout = QVBoxLayout(self)
        
        # 1. Image Area (Scrollable to handle large screenshots)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: 1px solid #444;")
        
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.img_label)
        layout.addWidget(self.scroll_area, 2) # Takes 2/3 space
        
        # 2. Text Area (Scrollable instructions)
        self.text_browser = QTextBrowser()
        self.text_browser.setStyleSheet(f"""
            background-color: {Theme.DARK['panel_bg']}; 
            border: 1px solid {Theme.DARK['border']};
            padding: 10px; font-family: 'Segoe UI'; font-size: 14px;
        """)
        layout.addWidget(self.text_browser, 1) # Takes 1/3 space
        
        # 3. Process Data
        self.process_data(screenshot_pixmap, analysis_data)
        self.show()

    def process_data(self, pixmap, data):
        # Draw markups on a COPY of the pixmap
        marked_pixmap = pixmap.copy()
        painter = QPainter(marked_pixmap)
        pen = QPen(QColor("#00ff00")); pen.setWidth(4); painter.setPen(pen)
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        
        instruction_text = ""
        
        if hasattr(data, 'elements'):
            img_w = marked_pixmap.width()
            img_h = marked_pixmap.height()
            
            for i, el in enumerate(data.elements):
                # Calc coords
                x = int((el.xmin / 1000) * img_w)
                y = int((el.ymin / 1000) * img_h)
                w = int(((el.xmax - el.xmin) / 1000) * img_w)
                h = int(((el.ymax - el.ymin) / 1000) * img_h)
                
                # Draw Box
                painter.drawRect(x, y, w, h)
                
                # Draw Label Background
                label_text = f"{i+1}. {el.label}"
                fm = painter.fontMetrics()
                rect_w = fm.horizontalAdvance(label_text) + 10
                rect_h = fm.height() + 5
                painter.fillRect(x, y - rect_h, rect_w, rect_h, QColor(0,0,0,180))
                painter.drawText(x+5, y-5, label_text)
                
                # Append to Instruction Text
                instruction_text += f"### {i+1}. {el.label}\n{el.usage_instruction}\n\n"
        
        painter.end()
        
        # Set Image
        self.img_label.setPixmap(marked_pixmap)
        
        # Set Text (using Markdown)
        if not instruction_text: instruction_text = "No specific UI elements detected for this query."
        self.text_browser.setMarkdown(instruction_text)


class AIBubble(QFrame):
    def __init__(self, parent, text):
        super().__init__(parent); self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(f"QFrame {{ background-color: {Theme.DARK['panel_bg']}; border: 2px solid {Theme.DARK['accent']}; border-radius: 12px; }} QLabel {{ color: white; font-weight: bold; }} QTextBrowser {{ border: none; color: #e0e0e0; font-family: Consolas; }}")
        self.resize(500, 400); layout = QVBoxLayout(self)
        header_widget = QWidget(); header_widget.setStyleSheet("background: transparent;"); header = QHBoxLayout(header_widget); header.setContentsMargins(0,0,0,0)
        lbl = QLabel("AI Assistant"); btn_close = QToolButton(); btn_close.setText("âœ•"); btn_close.setStyleSheet("background: transparent; color: #ff5555; font-size: 16px; font-weight: bold; border: none;"); btn_close.clicked.connect(self.close)
        header.addWidget(lbl); header.addStretch(); header.addWidget(btn_close); layout.addWidget(header_widget)
        self.browser = QTextBrowser(); self.browser.setMarkdown(text); layout.addWidget(self.browser)
        if parent: geo = parent.geometry(); cx, cy = geo.center().x(), geo.center().y(); self.move(cx - 300, cy - 200) 
        self.show(); self._drag_pos = None
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); event.accept()
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos: self.move(event.globalPosition().toPoint() - self._drag_pos); event.accept()

class AIUndoRedoHUD(QWidget):
    undo_requested = pyqtSignal(); redo_requested = pyqtSignal()
    def __init__(self, parent):
        super().__init__(parent); self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow); layout = QHBoxLayout(self); layout.setContentsMargins(5, 5, 5, 5)
        self.btn = QPushButton("  â†© Undo AI Fix  "); self.btn.setStyleSheet(f"QPushButton {{ background-color: {Theme.DARK['accent']}; color: white; border-radius: 18px; padding: 8px 20px; font-family: 'Segoe UI'; font-weight: bold; border: 2px solid white; }} QPushButton:hover {{ background-color: {Theme.DARK['accent_hover']}; }}")
        self.btn.clicked.connect(self.toggle_state); layout.addWidget(self.btn); self.is_undo_state = True; self.hide()
    def show_undo(self): self.is_undo_state = True; self.btn.setText("  â†© Undo AI Fix  "); self.show_animated()
    def toggle_state(self):
        if self.is_undo_state: self.undo_requested.emit(); self.btn.setText("  â†ª Redo AI Fix  "); self.btn.setStyleSheet(f"QPushButton {{ background-color: #444; color: #aaa; border-radius: 18px; padding: 8px 20px; font-weight: bold; border: 2px solid #666; }}")
        else: self.redo_requested.emit(); self.btn.setText("  â†© Undo AI Fix  "); self.btn.setStyleSheet(f"QPushButton {{ background-color: {Theme.DARK['accent']}; color: white; border-radius: 18px; padding: 8px 20px; font-weight: bold; border: 2px solid white; }}")
        self.is_undo_state = not self.is_undo_state
    def show_animated(self):
        if not self.isVisible(): self.show(); parent_geo = self.parent().geometry(); x = (parent_geo.width() - self.width()) // 2; self.move(x, 20); self.raise_()

class AIQueryDialog(QDialog):
    def __init__(self, parent, error_context=""):
        super().__init__(parent); self.setWindowTitle("AI Assistance Request"); self.setFixedSize(400, 250); self.setStyleSheet(f"background-color: {Theme.DARK['panel_bg']}; color: white;")
        layout = QVBoxLayout(self); layout.addWidget(QLabel("Describe your request (or leave empty to check errors):"))
        self.text_input = QTextEdit(); self.text_input.setPlaceholderText("E.g., 'Optimize this function' or 'Why is this failing?'..."); layout.addWidget(self.text_input)
        if error_context: lbl_err = QLabel(f"Context: Error detected"); lbl_err.setStyleSheet(f"color: {Theme.DARK['danger']}; font-style: italic;"); layout.addWidget(lbl_err)
        btn_layout = QHBoxLayout(); btn_cancel = QPushButton("Cancel"); btn_cancel.clicked.connect(self.reject); btn_ok = QPushButton("Ask AI"); btn_ok.setStyleSheet(f"background-color: {Theme.DARK['accent']}; color: white; border: none; padding: 5px;"); btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel); btn_layout.addWidget(btn_ok); layout.addLayout(btn_layout)
    def get_text(self): return self.text_input.toPlainText().strip()

class ConsoleOverlayWidget(QWidget):
    help_requested = pyqtSignal(str, object) 
    def __init__(self, parent=None):
        super().__init__(parent); self.layout = QGridLayout(self); self.layout.setContentsMargins(0,0,0,0)
        self.console = QTextEdit(); self.console.setReadOnly(True); self.console.setPlaceholderText("Subroutine Console Output..."); self.console.setStyleSheet(f"background-color: #111; border: none; padding: 5px; color: #0f0; font-family: Consolas;"); self.console.setFixedHeight(100); self.layout.addWidget(self.console, 0, 0)
        self.btn_help = QPushButton(self); self.btn_help.setFlat(True); self.btn_help.setFixedSize(30, 30); self.btn_help.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)); self.btn_help.setToolTip("Ask AI about this error"); self.btn_help.clicked.connect(self.request_help)
    def resizeEvent(self, event): super().resizeEvent(event); self.btn_help.move(self.width() - 35, 5)
    def request_help(self): 
        text = self.console.toPlainText(); 
        if text.strip(): self.help_requested.emit(text, self.parent())
    def append(self, text): self.console.append(text)
    def setText(self, text): self.console.setText(text)
    def verticalScrollBar(self): return self.console.verticalScrollBar()

class ToastNotification(QWidget):
    def __init__(self, parent):
        super().__init__(parent); self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow); self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) 
        self.setStyleSheet(f"background-color: {Theme.DARK['toast_bg']}; color: {Theme.DARK['text_main']}; border: 1px solid {Theme.DARK['toast_border']}; border-radius: 4px; padding: 10px;")
        self.layout = QHBoxLayout(self); self.label = QLabel(""); self.label.setStyleSheet("font-weight: bold; font-size: 13px;"); self.layout.addWidget(self.label)
        self.opacity_effect = QGraphicsOpacityEffect(self); self.setGraphicsEffect(self.opacity_effect); self.anim = QPropertyAnimation(self.opacity_effect, b"opacity"); self.anim.setDuration(300); self.anim.finished.connect(self.check_hide) 
        self.timer = QTimer(self); self.timer.setSingleShot(True); self.timer.timeout.connect(self.fade_out); self.hide()
    def show_message(self, message, is_error=False):
        self.timer.stop(); self.anim.stop(); color = Theme.DARK['danger'] if is_error else Theme.DARK['success']
        self.setStyleSheet(f"background-color: {Theme.DARK['toast_bg']}; color: {Theme.DARK['text_main']}; border-left: 5px solid {color}; border-radius: 4px; padding: 10px;")
        self.label.setText(message); self.adjustSize(); 
        p_width = self.parent().width(); 
        if self.width() > p_width - 40: self.setFixedWidth(p_width - 40); self.label.setWordWrap(True); self.adjustSize()
        parent_geo = self.parent().geometry(); x = (parent_geo.width() - self.width()) // 2; y = parent_geo.height() - self.height() - 60; self.move(x, y)
        self.show(); self.opacity_effect.setOpacity(1); duration = 5000; self.timer.start(duration)
    def fade_out(self): self.anim.setStartValue(1); self.anim.setEndValue(0); self.anim.start()
    def check_hide(self): 
        if self.opacity_effect.opacity() == 0: self.hide()

class FloatingRevertButton(QWidget):
    clicked = pyqtSignal()
    def __init__(self, parent):
        super().__init__(parent); self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow); layout = QHBoxLayout(self); layout.setContentsMargins(0,0,0,0)
        self.btn = QPushButton("  Undo Last Change  "); self.btn.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.btn.setStyleSheet(f"QPushButton {{ background-color: {Theme.DARK['danger']}; color: white; border-radius: 20px; padding: 10px 20px; font-weight: bold; border: 2px solid white; }} QPushButton:hover {{ background-color: #b71c1c; }}")
        self.btn.clicked.connect(self.clicked); layout.addWidget(self.btn); self.hide()
    def show_animated(self):
        if not self.isVisible(): self.show(); parent_geo = self.parent().geometry(); x = (parent_geo.width() - self.width()) // 2; self.move(x, 20)

class PythonRunner(QThread):
    output_signal = pyqtSignal(str); error_signal = pyqtSignal(str)
    def __init__(self, code, script_path=None): super().__init__(); self.code = code; self.script_path = script_path
    def run(self):
        try:
            args = [sys.executable, "-u"]
            if self.script_path: args.append(self.script_path)
            else: args.extend(["-c", self.code])
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            while True:
                output = process.stdout.readline(); 
                if output == '' and process.poll() is not None: break
                if output: self.output_signal.emit(output)
            _, stderr = process.communicate()
            if stderr: self.error_signal.emit(stderr)
        except Exception as e: self.error_signal.emit(str(e))

class AdvancedEditor(QsciScintilla):
    error_found = pyqtSignal(int, str); errors_cleared = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent); self.setUtf8(True); self.setFont(QFont("Consolas", 11)); self.syntax_timer = QTimer(); self.syntax_timer.setSingleShot(True); self.syntax_timer.interval = 1000 
        self.syntax_timer.timeout.connect(self.check_syntax); self.textChanged.connect(lambda: self.syntax_timer.start()); self.indicatorDefine(QsciScintilla.IndicatorStyle.SquiggleIndicator, 0)
        self.setIndicatorForegroundColor(QColor("red"), 0); self.setMarginType(0, QsciScintilla.MarginType.NumberMargin); self.setMarginWidth(0, "0000"); self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle)
        self.setMarginWidth(2, 14); self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch); self.setMouseTracking(True); self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll); self.setAutoCompletionThreshold(1); self.current_errors = {}; self.set_language("python")
    def keyPressEvent(self, e):
        pairs = {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}
        if e.text() in pairs: self.insert(pairs[e.text()]); super().keyPressEvent(e); self.SendScintilla(QsciScintilla.SCI_CHARLEFT)
        else: super().keyPressEvent(e)
    def check_syntax(self):
        if not isinstance(self.lexer(), QsciLexerPython): return
        code = self.text(); self.clearIndicatorRange(0, 0, self.lines(), self.lineLength(self.lines()), 0); self.current_errors.clear(); self.errors_cleared.emit()
        if not code.strip(): return
        import ast
        try: ast.parse(code)
        except SyntaxError as e:
            if e.lineno: line = e.lineno - 1; self.fillIndicatorRange(line, 0, line, self.lineLength(line), 0); self.current_errors[line] = e.msg; self.error_found.emit(1, e.msg)
        except Exception: pass
    def mouseMoveEvent(self, e):
        pos = e.pos(); line = self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, self.SendScintilla(QsciScintilla.SCI_POSITIONFROMPOINT, pos.x(), pos.y()))
        if line in self.current_errors: QToolTip.showText(self.mapToGlobal(pos), f"âš  {self.current_errors[line]}", self)
        else: QToolTip.hideText()
        super().mouseMoveEvent(e)
    def set_language(self, lang):
        if lang == "python": self.lexer_obj = QsciLexerPython(self)
        else: self.lexer_obj = QsciLexerCPP(self)
        api = QsciAPIs(self.lexer_obj); 
        for k in ["def", "class", "print", "import", "return", "int", "void"]: api.add(k)
        api.prepare(); self.setLexer(self.lexer_obj)

# --- 5. WIDGET COMPONENTS ---

class DraggableOutput(QLabel):
    def __init__(self, var_name, var_type, parent=None):
        super().__init__(parent); self.var_name = var_name; self.var_type = var_type
        self.output_file_path = None 
        if var_type in ["bytearray", "ushort_array", "uint_array"]:
            self.setText(f"ðŸ“„ {var_name}"); self.setStyleSheet(f"background-color: {Theme.DARK['accent']}33; color: {Theme.DARK['accent']}; border: 1px solid {Theme.DARK['accent']}; padding: 4px 8px; border-radius: 12px; font-weight: bold;")
        else:
            self.setText(f"x= {var_name}"); self.setStyleSheet(f"background-color: #9c27b033; color: #ce93d8; border: 1px solid #ce93d8; padding: 4px 8px; border-radius: 12px; font-weight: bold;")
    def set_output_file(self, path): self.output_file_path = path
    def mouseMoveEvent(self, e):
        if e.buttons() != Qt.MouseButton.LeftButton: return
        drag = QDrag(self); mime = QMimeData(); mime.setText(self.var_name)
        card = self.parent()
        while card and not isinstance(card, FunctionCard): card = card.parent()
        if card:
            meta = {}
            for key, widget in card.inputs.items():
                val = None
                if isinstance(widget, QSpinBox): val = widget.value()
                elif isinstance(widget, QLineEdit): val = widget.text()
                if key in ['dimx', 'dimy', 'dimz']: meta[key] = int(val) if val else 0
            if self.output_file_path and os.path.exists(self.output_file_path): meta['filename'] = self.output_file_path
            else:
                found_file = False
                for key, widget in card.inputs.items():
                    if isinstance(widget, FileSelector):
                        if widget.path_info.get('direction') == 'output' and widget.text().strip(): meta['filename'] = widget.text().strip(); found_file = True; break
                if not found_file:
                    for key, widget in card.inputs.items():
                        if isinstance(widget, FileSelector):
                            if widget.path_info.get('direction') == 'input' and widget.text().strip(): meta['filename'] = widget.text().strip(); break
            if meta: json_data = json.dumps(meta); mime.setData("application/x-pypore3d-data", QByteArray(json_data.encode('utf-8')))
        drag.setMimeData(mime); drag.exec(Qt.DropAction.CopyAction)

class DropInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent); self.setAcceptDrops(True); self.setPlaceholderText("Value or drop var...")
        self.setStyleSheet(f"QLineEdit {{ background-color: {Theme.DARK['input_bg']}; border: 1px solid {Theme.DARK['border']}; border-radius: 4px; padding: 5px; color: {Theme.DARK['text_main']}; }} QLineEdit:focus {{ border: 1px solid {Theme.DARK['accent']}; }}")
    def dragEnterEvent(self, e):
        if e.mimeData().hasText(): e.accept()
        else: e.ignore()
    def dropEvent(self, e): self.setText(e.mimeData().text())

class FileSelector(QWidget):
    textChanged = pyqtSignal(str)
    def __init__(self, path_info, parent=None):
        super().__init__(parent); self.path_info = path_info; layout = QHBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(5)
        self.line_edit = QLineEdit(); self.line_edit.setPlaceholderText("Select absolute path...")
        self.line_edit.setStyleSheet(f"background-color: {Theme.DARK['input_bg']}; border: 1px solid {Theme.DARK['border']}; border-radius: 4px; padding: 5px; color: {Theme.DARK['text_main']};")
        self.btn_browse = QToolButton(); self.btn_browse.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        self.btn_browse.setStyleSheet(f"background-color: {Theme.DARK['panel_bg']}; border: 1px solid {Theme.DARK['border']}; border-radius: 4px;")
        self.btn_browse.clicked.connect(self.browse); layout.addWidget(self.line_edit); layout.addWidget(self.btn_browse)
        self.line_edit.textChanged.connect(self.validate); self.line_edit.textChanged.connect(self.textChanged)
        if self.line_edit.text(): self.validate(self.line_edit.text())
    def validate(self, text):
        if not text.strip(): self.line_edit.setStyleSheet(f"background-color: {Theme.DARK['input_bg']}; border: 1px solid {Theme.DARK['danger']}; border-radius: 4px; padding: 5px; color: {Theme.DARK['text_main']};"); self.line_edit.setToolTip("Path is required")
        else: self.line_edit.setStyleSheet(f"background-color: {Theme.DARK['input_bg']}; border: 1px solid {Theme.DARK['border']}; border-radius: 4px; padding: 5px; color: {Theme.DARK['text_main']};"); self.line_edit.setToolTip(text)
    def browse(self):
        path_type = self.path_info.get('path_type', 'file'); direction = self.path_info.get('direction', 'input'); filter_str = self.path_info.get('file_filter', 'All Files (*.*)')
        fname = ""
        if path_type == 'folder' or path_type == 'dir': fname = QFileDialog.getExistingDirectory(self, "Select Folder")
        else:
            if direction == 'output': fname, _ = QFileDialog.getSaveFileName(self, "Save File", "", filter_str)
            else: fname, _ = QFileDialog.getOpenFileName(self, "Open File", "", filter_str)
        if fname: self.line_edit.setText(os.path.abspath(fname))
    def text(self): return self.line_edit.text()
    def setText(self, t): self.line_edit.setText(t)

class FunctionCard(QFrame):
    code_changed = pyqtSignal(); delete_requested = pyqtSignal(object); run_requested = pyqtSignal(object)
    request_viewer_metadata = pyqtSignal(object) 

    def __init__(self, fn_metadata, var_name_out=None, parent=None):
        super().__init__(parent); self.metadata = fn_metadata
        self.setStyleSheet(f"FunctionCard {{ background-color: {Theme.DARK['card_bg']}; border-radius: 8px; border: 1px solid {Theme.DARK['border']}; }} QLabel {{ color: {Theme.DARK['text_main']}; }}")
        self.layout = QVBoxLayout(self); self.layout.setSpacing(10)
        
        header = QHBoxLayout()
        self.title = QLabel(f"<b>{fn_metadata['display_name']}</b>"); self.title.setStyleSheet("font-size: 13px;")
        self.btn_paste_meta = QToolButton(); self.btn_paste_meta.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)); self.btn_paste_meta.setToolTip("Paste Parameters from Voxel Viewer"); self.btn_paste_meta.setStyleSheet("border: none; background: transparent;"); self.btn_paste_meta.clicked.connect(lambda: self.request_viewer_metadata.emit(self))
        self.btn_run = QToolButton(); self.btn_run.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)); self.btn_run.setToolTip("Run this function only (isolated)"); self.btn_run.setStyleSheet("border: none; background: transparent;"); self.btn_run.clicked.connect(lambda: self.run_requested.emit(self))
        self.btn_del = QToolButton(); self.btn_del.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton)); self.btn_del.setToolTip("Delete Function"); self.btn_del.setStyleSheet("border: none; background: transparent;"); self.btn_del.clicked.connect(lambda: self.delete_requested.emit(self))
        header.addWidget(self.title); header.addStretch(); header.addWidget(self.btn_paste_meta); header.addWidget(self.btn_run); header.addWidget(self.btn_del); self.layout.addLayout(header)

        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet(f"color: {Theme.DARK['border']};"); self.layout.addWidget(line)

        self.inputs = {}
        self.params_layout = QGridLayout(); self.params_layout.setVerticalSpacing(8); self.params_layout.setHorizontalSpacing(15)
        sorted_params = sorted(fn_metadata['parameters'], key=lambda x: x['order'])
        row, col = 0, 0
        for param in sorted_params:
            label = QLabel(param['display_name']); label.setStyleSheet(f"color: {Theme.DARK['text_dim']}; font-size: 11px;"); label.setToolTip(param.get('tooltip', ''))
            widget = self.create_input_widget(param); self.inputs[param['code_name']] = widget
            is_full_width = isinstance(widget, FileSelector)
            if is_full_width:
                if col == 1: row += 1; col = 0
                self.params_layout.addWidget(label, row, 0); self.params_layout.addWidget(widget, row + 1, 0, 1, 2); row += 2; col = 0
            else:
                self.params_layout.addWidget(label, row, col); self.params_layout.addWidget(widget, row + 1, col); col += 1
                if col > 1: col = 0; row += 2
        self.layout.addLayout(self.params_layout)

        self.return_var = var_name_out; 
        if not self.return_var and fn_metadata.get('return_value'): self.return_var = f"res_{fn_metadata['id']}_{str(uuid.uuid4())[:4]}"
        if self.return_var:
            self.output_basket = QHBoxLayout(); self.output_basket.setContentsMargins(0, 5, 0, 0); lbl = QLabel("Output:"); lbl.setStyleSheet(f"color: {Theme.DARK['text_dim']}; font-size: 11px;")
            self.basket_item = DraggableOutput(self.return_var, fn_metadata['return_value']['type']); self.output_basket.addWidget(lbl); self.output_basket.addWidget(self.basket_item); self.output_basket.addStretch(); self.layout.addLayout(self.output_basket)

        for w in self.inputs.values():
            if isinstance(w, FileSelector): w.textChanged.connect(self.validate_and_emit)
            elif hasattr(w, 'textChanged'): w.textChanged.connect(self.validate_and_emit)
            if hasattr(w, 'valueChanged'): w.valueChanged.connect(self.validate_and_emit)
            if hasattr(w, 'stateChanged'): w.stateChanged.connect(self.validate_and_emit)

    def create_input_widget(self, param):
        if param.get('is_constant'): w = QLineEdit(str(param['constant_value'])); w.setReadOnly(True); w.setStyleSheet(f"background: transparent; border: none; color: {Theme.DARK['text_dim']};"); return w
        dtype = param['datatype']; p_info = param.get('path_info', None); is_image_data = dtype in ['bytearray', 'ushort_array', 'uint_array']
        name_lower = param['code_name'].lower(); is_string_path = False
        if not p_info and dtype == 'string':
             if any(k in name_lower for k in ['path', 'file', 'dir', 'folder', 'filename']): is_string_path = True
        if is_image_data or is_string_path or p_info:
            if not p_info: p_info = {}
            if 'folder' in name_lower or 'dir' in name_lower: p_info['path_type'] = 'folder'
            else:
                p_info['path_type'] = 'file'
                if is_image_data: p_info['file_filter'] = "RAW Files (*.raw);;All Files (*.*)"
                else:
                    if 'file_filter' not in p_info: p_info['file_filter'] = "All Files (*.*)"
            if param.get('is_output') or any(k in name_lower for k in ['out', 'save', 'write', 'res']): p_info['direction'] = 'output'
            else: p_info['direction'] = 'input'
            return FileSelector(p_info)
        if dtype == 'int': w = QSpinBox(); w.setRange(0, 99999999); w.setStyleSheet(f"background-color: {Theme.DARK['input_bg']}; border: 1px solid {Theme.DARK['border']}; padding: 4px; border-radius: 4px; color: white;"); 
        elif dtype == 'float': w = QDoubleSpinBox(); w.setRange(0.0, 99999999.0); w.setStyleSheet(f"background-color: {Theme.DARK['input_bg']}; border: 1px solid {Theme.DARK['border']}; padding: 4px; border-radius: 4px; color: white;")
        elif dtype == 'bool': w = QCheckBox()
        else: w = DropInput()
        if param.get('default') is not None:
            try:
                if isinstance(w, QSpinBox): w.setValue(int(param['default']))
                if isinstance(w, QDoubleSpinBox): w.setValue(float(param['default']))
                if isinstance(w, QCheckBox): w.setChecked(bool(param['default']))
            except: pass
        return w

    def apply_viewer_metadata(self, meta):
        if not meta: return
        for param in self.metadata['parameters']:
            code_name = param['code_name']; w = self.inputs[code_name]
            if code_name == 'dimx' and 'dimx' in meta: (w.setValue(int(meta['dimx'])) if hasattr(w,'setValue') else w.setText(str(meta['dimx'])))
            elif code_name == 'dimy' and 'dimy' in meta: (w.setValue(int(meta['dimy'])) if hasattr(w,'setValue') else w.setText(str(meta['dimy'])))
            elif code_name == 'dimz' and 'dimz' in meta: (w.setValue(int(meta['dimz'])) if hasattr(w,'setValue') else w.setText(str(meta['dimz'])))
            elif isinstance(w, FileSelector) and w.path_info.get('direction') == 'input':
                if 'filename' in meta: w.line_edit.setText(meta['filename'])

    def get_validation_status(self):
        for param in self.metadata['parameters']:
            w = self.inputs[param['code_name']]
            if param.get('required', False):
                val = ""
                if isinstance(w, FileSelector): val = w.text()
                elif isinstance(w, (QLineEdit, DropInput)): val = w.text()
                if (isinstance(w, (FileSelector, QLineEdit, DropInput)) and not val.strip()): return False, f"Parameter '{param['display_name']}' is required.", param['display_name'], "Empty"
        return True, None, None, None

    def validate_and_emit(self): self.code_changed.emit()

    def generate_python_code(self):
        code_lines = []
        args = []
        sorted_params = sorted(self.metadata['parameters'], key=lambda x: x['order'])
        dims = {}
        for p in sorted_params:
            if p['code_name'] in ['dimx', 'dimy', 'dimz']:
                w = self.inputs[p['code_name']]
                if isinstance(w, (QSpinBox, QDoubleSpinBox)): dims[p['code_name']] = int(w.value())
                elif isinstance(w, QLineEdit) and w.text().isdigit(): dims[p['code_name']] = int(w.text())

        for param in sorted_params:
            widget = self.inputs[param['code_name']]; val = ""
            if isinstance(widget, FileSelector) and widget.path_info.get('direction') == 'output':
                if not widget.text().strip():
                    safe_name = re.sub(r'\W+', '', param['display_name'])
                    fname = f"{safe_name}_{str(uuid.uuid4())[:6]}.raw"
                    full_path = session.get_path(fname)
                    widget.setText(full_path)
            
            # --- FIX: FORCE READER FOR ANY ARRAY INPUT ---
            is_array_type = param['datatype'] in ['bytearray', 'ushort_array', 'uint_array']
            if is_array_type:
                raw_input = ""
                if isinstance(widget, FileSelector): raw_input = widget.text()
                elif isinstance(widget, QLineEdit): raw_input = widget.text()
                
                if raw_input and (os.path.exists(raw_input) or "/" in raw_input or "\\" in raw_input):
                    var_name = f"data_{param['code_name']}_{str(uuid.uuid4())[:4]}"
                    clean_path = raw_input.replace("\\", "\\\\")
                    reader_func = "p3dFiltPy.py_p3dReadRaw8" 
                    if param['datatype'] == 'ushort_array': reader_func = "p3dFiltPy_16.py_p3dReadRaw16"
                    elif param['datatype'] == 'uint_array': reader_func = "p3dFiltPy.py_p3dReadRaw8"
                    
                    dim_args = f"{dims.get('dimx',0)}, {dims.get('dimy',0)}, dimz={dims.get('dimz',0)}"
                    code_lines.append(f"# Load Input: {param['display_name']}")
                    code_lines.append(f"{var_name} = {reader_func}(r'{clean_path}', {dim_args})")
                    code_lines.append(f"if {var_name} is None: raise ValueError('Failed to load {clean_path}')")
                    # NO CASTING - Pass Swig Object Directly
                    val = var_name
                else:
                    val = raw_input if raw_input else "None"
            
            elif isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox): val = str(widget.value())
            elif isinstance(widget, QCheckBox): val = "True" if widget.isChecked() else "False"
            elif isinstance(widget, FileSelector): val = f"r'{widget.text().replace(os.sep, '/')}'" 
            elif isinstance(widget, QLineEdit) or isinstance(widget, DropInput):
                txt = widget.text()
                if param['datatype'] == 'string': val = f"'{txt}'"
                else: val = txt
            args.append(val)
        
        call_str = f"{self.metadata['function_call']}({', '.join(args)})"
        if self.return_var:
            code_lines.append(f"{self.return_var} = {call_str}")
            ret_type = self.metadata.get('return_value', {}).get('type', '')
            if ret_type in ['bytearray', 'ushort_array', 'uint_array']:
                timestamp = datetime.datetime.now().strftime("%H%M%S")
                out_fname = f"Result_{self.metadata['display_name'].replace(' ','')}_{timestamp}.raw"
                out_path = session.get_path(out_fname)
                writer_func = "p3dFiltPy.py_p3dWriteRaw8"
                if ret_type == 'ushort_array': writer_func = "p3dFiltPy_16.py_p3dWriteRaw16"
                dim_str = f"{dims.get('dimx',0)}, {dims.get('dimy',0)}, {dims.get('dimz',0)}"
                code_lines.append(f"# Auto-Save Output: {out_fname}")
                clean_out = out_path.replace("\\", "\\\\")
                code_lines.append(f"{writer_func}({self.return_var}, r'{clean_out}', {dim_str})")
                if hasattr(self, 'basket_item'): self.basket_item.set_output_file(out_path)
        else:
            code_lines.append(call_str)
        return "\n".join(code_lines)

    def populate_from_ast_call(self, call_node):
        sorted_params = sorted(self.metadata['parameters'], key=lambda x: x['order'])
        for i, arg_node in enumerate(call_node.args):
            if i >= len(sorted_params): break
            self._set_widget_value(sorted_params[i]['code_name'], arg_node)
        for kw in call_node.keywords: self._set_widget_value(kw.arg, kw.value)

    def _set_widget_value(self, param_name, ast_value_node):
        if param_name not in self.inputs: return
        widget = self.inputs[param_name]; val = None
        if isinstance(ast_value_node, ast.Constant): val = ast_value_node.value
        elif isinstance(ast_value_node, ast.Name): val = ast_value_node.id
        elif isinstance(ast_value_node, ast.Str): val = ast_value_node.s
        elif isinstance(ast_value_node, ast.Num): val = ast_value_node.n
        if val is None: return
        
        # Block Signals to prevent feedback loop
        widget.blockSignals(True)
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            try: widget.setValue(float(val))
            except: pass
        elif isinstance(widget, QCheckBox): widget.setChecked(bool(val))
        elif isinstance(widget, FileSelector): widget.setText(str(val))
        elif isinstance(widget, (QLineEdit, DropInput)): widget.setText(str(val))
        widget.blockSignals(False)

class SubroutineWidget(QFrame):
    sync_request = pyqtSignal(); delete_requested = pyqtSignal(object); ai_help_requested = pyqtSignal(str, object)
    request_viewer_metadata = pyqtSignal(object)

    def __init__(self, name="Subroutine", parent=None):
        super().__init__(parent); self.setStyleSheet(f"SubroutineWidget {{ background-color: {Theme.DARK['sub_bg']}; border-radius: 12px; border: 1px solid #3e3e42; }}")
        self.functions = []; layout = QVBoxLayout(self); layout.setContentsMargins(15, 15, 15, 15); layout.setSpacing(10)
        self.header = QHBoxLayout(); self.name_label = QLabel(f"{name}"); self.name_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Theme.DARK['accent']};")
        self.note_field = QLineEdit(); self.note_field.setPlaceholderText("Add description..."); self.note_field.setStyleSheet(f"background: transparent; border: none; color: {Theme.DARK['text_dim']}; font-style: italic;")
        self.btn_add = QPushButton(" + Func"); self.btn_add.setStyleSheet(f"background-color: {Theme.DARK['panel_bg']}; color: {Theme.DARK['text_main']}; border-radius: 4px; padding: 4px 8px;"); self.btn_add.clicked.connect(self.request_add_function)
        self.btn_run = QToolButton(); self.btn_run.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)); self.btn_run.setToolTip("Run this entire subroutine (isolated)"); self.btn_run.setStyleSheet("border: none;"); self.btn_run.clicked.connect(self.run_subroutine)
        self.btn_del = QToolButton(); self.btn_del.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton)); self.btn_del.setStyleSheet(f"border: none;"); self.btn_del.clicked.connect(lambda: self.delete_requested.emit(self))
        self.header.addWidget(self.name_label); self.header.addWidget(self.note_field); self.header.addStretch(); self.header.addWidget(self.btn_add); self.header.addWidget(self.btn_run); self.header.addWidget(self.btn_del); layout.addLayout(self.header)
        self.func_container = QVBoxLayout(); self.func_container.setSpacing(10); layout.addLayout(self.func_container)
        self.console = ConsoleOverlayWidget(); self.console.help_requested.connect(self.handle_console_help); layout.addWidget(self.console)

    def handle_console_help(self, text, _):
        # Pass signal up with this widget as context
        self.ai_help_requested.emit(text, self)

    def add_function_card(self, fn_metadata, var_out=None):
        card = FunctionCard(fn_metadata, var_out); card.code_changed.connect(self.propagate_change); card.delete_requested.connect(self.remove_function); card.run_requested.connect(self.run_single_function)
        card.request_viewer_metadata.connect(self.request_viewer_metadata.emit)
        self.func_container.addWidget(card); self.functions.append(card); self.propagate_change(); return card

    def remove_function(self, card_widget):
        if card_widget in self.functions: self.functions.remove(card_widget); card_widget.setParent(None); card_widget.deleteLater(); self.propagate_change()
    def request_add_function(self): 
        dlg = FunctionSelectionDialog(global_library); 
        if dlg.exec(): self.add_function_card(dlg.selected_function)
    def propagate_change(self): self.sync_request.emit()
    def to_clst_block(self):
        name = self.name_label.text(); lines = [f"# <CLST_SUBROUTINE name=\"{name}\">"]
        if self.note_field.text(): lines.append(f"# <CLST_NOTE>{self.note_field.text()}</CLST_NOTE>")
        for fn in self.functions: lines.append(f"# <CLST_FUNC id=\"{fn.metadata['id']}\">"); lines.append(fn.generate_python_code()); lines.append(f"# </CLST_FUNC>")
        lines.append("# </CLST_SUBROUTINE>"); return "\n".join(lines)
    
    def _generate_imports(self):
        imports = ["import os", "import sys", "import numpy as np", "import pypore3d"]; 
        # Import common modules
        imports.append("from pypore3d import p3dFiltPy, p3dFiltPy_16, p3dBlobPy, p3dSkelPy, p3dSITKPy, p3dSITKPy_16")
        return "\n".join(imports) + "\n\n"
    
    def run_single_function(self, card): self.console.append(f"Running single function: {card.metadata['display_name']}..."); self._execute_isolated(self._generate_imports() + "# Isolated Function Run\n" + card.generate_python_code())
    def run_subroutine(self): 
        self.console.append(f"Running Subroutine: {self.name_label.text()}..."); code = self._generate_imports() + f"# Isolated Run: {self.name_label.text()}\n"; 
        for fn in self.functions: code += fn.generate_python_code() + "\n"
        self._execute_isolated(code)
    def _execute_isolated(self, code_str):
        try:
            # Use Session Folder for Script
            fname = f"script_{str(uuid.uuid4())[:6]}.py"
            fpath = session.get_path(fname)
            with open(fpath, 'w', encoding='utf-8') as f: f.write(code_str)
            self.runner = PythonRunner("", script_path=fpath); self.runner.output_signal.connect(self.append_console); self.runner.error_signal.connect(self.append_console_error); self.runner.finished.connect(lambda: self.append_console(" >> Execution Finished.")); self.runner.start()
        except Exception as e: self.console.append(f"Execution Setup Error: {e}")
    def append_console(self, text): self.console.append(text.strip()); sb = self.console.verticalScrollBar(); sb.setValue(sb.maximum())
    def append_console_error(self, text): self.console.append(f"ERR: {text.strip()}"); sb = self.console.verticalScrollBar(); sb.setValue(sb.maximum())

# --- 6. FUNCTION SELECTION DIALOG (Standard) ---
class FunctionSelectionDialog(QDialog):
    def __init__(self, library, parent=None):
        super().__init__(parent); self.library = library; self.selected_function = None; self.setWindowTitle("Select Function"); self.resize(900, 500); self.setStyleSheet(f"background-color: {Theme.DARK['panel_bg']}; color: {Theme.DARK['text_main']};")
        layout = QHBoxLayout(self); col1 = QVBoxLayout(); self.cb_sort = QComboBox(); self.cb_sort.addItems(["Sort By : ", "Module", "Category"]); self.cb_sort.setStyleSheet(f"background-color: {Theme.DARK['input_bg']}; padding: 5px; border: 1px solid {Theme.DARK['border']}; color: white;")
        self.cat_list = QListWidget(); self.cat_list.setStyleSheet(f"background-color: {Theme.DARK['input_bg']}; border: none;"); self.cb_sort.currentTextChanged.connect(self.populate_categories); self.cat_list.itemClicked.connect(self.populate_functions)
        col1.addWidget(self.cb_sort); col1.addWidget(self.cat_list)
        col2 = QVBoxLayout(); self.fn_list = QListWidget(); self.fn_list.setStyleSheet(f"background-color: {Theme.DARK['input_bg']}; border: none;"); self.fn_list.itemClicked.connect(self.show_description); col2.addWidget(QLabel("Functions:")); col2.addWidget(self.fn_list)
        col3 = QVBoxLayout(); self.desc_label = QLabel("Select a function..."); self.desc_label.setWordWrap(True); self.desc_label.setStyleSheet("font-size: 14px; padding: 10px;")
        btn_layout = QHBoxLayout(); self.btn_ok = QPushButton("Add Function"); self.btn_ok.setStyleSheet(f"background-color: {Theme.DARK['accent']}; color: white; padding: 8px; border-radius: 4px;"); self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel"); self.btn_cancel.setStyleSheet(f"background-color: {Theme.DARK['danger']}; color: white; padding: 8px; border-radius: 4px;"); self.btn_cancel.clicked.connect(self.reject); btn_layout.addWidget(self.btn_ok); btn_layout.addWidget(self.btn_cancel)
        col3.addWidget(QLabel("Description:")); col3.addWidget(self.desc_label); col3.addStretch(); col3.addLayout(btn_layout); layout.addLayout(col1, 2); layout.addLayout(col2, 3); layout.addLayout(col3, 5)
    def populate_categories(self, sort_mode): self.cat_list.clear(); self.cat_list.addItems(sorted(list(self.library.modules)) if sort_mode == "Module" else sorted(list(self.library.categories)))
    def populate_functions(self, item): self.fn_list.clear(); funcs = self.library.get_filtered_functions(item.text()); self.current_func_map = {fn['display_name']: fn for fn in funcs}; self.fn_list.addItems(self.current_func_map.keys())
    def show_description(self, item): fn = self.current_func_map[item.text()]; self.desc_label.setText(fn['description']); self.selected_function = fn

# --- 7. MAIN WIDGET ---
class SmartIDEWidget(QWidget):
    ai_help_requested = pyqtSignal(str) 

    def __init__(self):
        super().__init__()
        self.viewer_metadata = {} 
        self.load_library(); self.is_dark_mode = True; self.is_syncing = False; self.subroutines = []
        self.sync_timer = QTimer(); self.sync_timer.setSingleShot(True); self.sync_timer.setInterval(2000); self.sync_timer.timeout.connect(self.sync_ide_to_visual); self.last_valid_code = ""
        self.init_ui(); self.apply_theme(); self.toast = ToastNotification(self)
        self.pre_ai_code = ""; self.post_ai_code = ""

    def cleanup_session(self): session.cleanup()
    def save_session_dialog(self):
        dest = QFileDialog.getExistingDirectory(self, "Select Folder to Save Session Files")
        if dest:
            if session.save_session_to(dest): self.toast.show_message(f"Session Saved to {os.path.basename(dest)}")
            else: self.toast.show_message("Save Failed", True)

    def load_library(self):
        global global_library; script_dir = os.path.dirname(os.path.abspath(__file__)); json_path = os.path.join(script_dir, 'pypore3d_function_reference.json')
        if not os.path.exists(json_path): QMessageBox.critical(self, "Error", "pypore3d_function_reference.json not found!"); sys.exit(1)
        with open(json_path, 'r') as f: data = json.load(f)
        global_library = FunctionLibrary(data)

    def init_ui(self):
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(0, 0, 0, 0); self.layout.setSpacing(0)
        self.tabs = QTabWidget(); self.tabs.setMovable(False); self.tabs.setDocumentMode(True) 
        self.toolbar_widget = QWidget(); self.toolbar_layout = QHBoxLayout(self.toolbar_widget); self.toolbar_layout.setContentsMargins(0, 5, 10, 5); self.toolbar_layout.setSpacing(10)
        
        self.btn_load = QPushButton("Load"); self.btn_save = QPushButton("Save"); self.btn_run = QPushButton("Run All"); self.btn_theme = QPushButton("Theme")
        self.toolbar_layout.addWidget(self.btn_load); self.toolbar_layout.addWidget(self.btn_save); self.toolbar_layout.addWidget(self.btn_run); self.toolbar_layout.addWidget(self.btn_theme)
        self.tabs.setCornerWidget(self.toolbar_widget, Qt.Corner.TopRightCorner)

        self.visual_tab = QWidget(); v_layout = QVBoxLayout(self.visual_tab); v_layout.setContentsMargins(20, 20, 20, 20); v_layout.setSpacing(15)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setStyleSheet("border: none; background: transparent;")
        self.subroutines_container = QWidget(); self.sub_layout = QVBoxLayout(self.subroutines_container); self.sub_layout.setContentsMargins(0,0,0,0); self.sub_layout.setSpacing(20); self.sub_layout.addStretch()
        self.scroll.setWidget(self.subroutines_container)
        self.btn_add_sub = QPushButton("  + Add New Subroutine  "); self.btn_add_sub.setFixedHeight(40); self.btn_add_sub.setStyleSheet(f"QPushButton {{ background-color: {Theme.DARK['accent']}; color: white; border-radius: 6px; font-size: 14px; font-weight: bold; }} QPushButton:hover {{ background-color: {Theme.DARK['accent_hover']}; }}"); self.btn_add_sub.clicked.connect(self.add_subroutine)
        v_layout.addWidget(self.btn_add_sub); v_layout.addWidget(self.scroll)
        
        self.btn_sub_ai = OverlayButton(self.visual_tab, "Check Validation (AI)", color="#9c27b0"); self.btn_sub_ai.clicked.connect(self.handle_subroutine_validation)

        self.editor_container = QWidget(); layout_e = QVBoxLayout(self.editor_container); layout_e.setContentsMargins(0,0,0,0); layout_e.setSpacing(0)
        self.editor = AdvancedEditor(); self.editor.textChanged.connect(self.on_code_typed); self.float_revert = FloatingRevertButton(self.editor); self.float_revert.clicked.connect(self.revert_code)
        self.status_bar = QFrame(); self.status_bar.setFixedHeight(35); self.status_layout = QHBoxLayout(self.status_bar); self.status_layout.setContentsMargins(15, 0, 15, 0) 
        self.lbl_stats = QLabel("Ln 1, Col 1"); self.lbl_err = QLabel("No Errors"); self.status_layout.addWidget(self.lbl_stats); self.status_layout.addStretch(); self.status_layout.addWidget(self.lbl_err)
        layout_e.addWidget(self.editor); layout_e.addWidget(self.status_bar)
        
        self.btn_code_ai = OverlayButton(self.editor_container, "Fix Syntax (AI)", color="#388e3c"); self.btn_code_ai.clicked.connect(self.handle_code_fix)
        self.ai_undo_hud = AIUndoRedoHUD(self.editor_container)
        self.ai_undo_hud.undo_requested.connect(self.undo_ai_fix)
        self.ai_undo_hud.redo_requested.connect(self.redo_ai_fix)

        self.tabs.addTab(self.visual_tab, "Subroutines"); self.tabs.addTab(self.editor_container, "IDE"); self.layout.addWidget(self.tabs)
        self.btn_load.clicked.connect(self.load_file); self.btn_save.clicked.connect(self.save_file); self.btn_run.clicked.connect(self.run_code); self.btn_theme.clicked.connect(self.toggle_theme)
        self.editor.cursorPositionChanged.connect(self.update_stats); self.editor.error_found.connect(lambda n, s: self.lbl_err.setText(f"âš  {n} Error(s)")); self.editor.errors_cleared.connect(lambda: self.lbl_err.setText("âœ” No Errors"))

    def resizeEvent(self, event): super().resizeEvent(event); self.btn_sub_ai.update_position(); self.btn_code_ai.update_position()

    def get_relevant_context(self, code_text):
        if not global_library: return ""
        used_functions = []
        for func_name, func_data in global_library.functions.items():
            if func_name in code_text: used_functions.append(func_data)
        if not used_functions: return ""
        return json.dumps(used_functions, indent=2)

    def handle_subroutine_validation(self):
        error_context = ""
        for sub in self.subroutines:
            for card in sub.functions:
                is_valid, msg, param, val = card.get_validation_status()
                if not is_valid: error_context = f"Validation Error in '{card.metadata['display_name']}': {msg} (Value: {val})"; break
            if error_context: break
        
        dialog = AIQueryDialog(self, error_context)
        if dialog.exec():
            user_input = dialog.get_text()
            context_json = self.get_relevant_context(self.editor.text()) 
            prompt = ""
            if user_input: prompt = f"User Query: {user_input}\n\nContext:\n{error_context}"
            elif error_context: prompt = f"Fix this validation error:\n{error_context}"
            else: prompt = "Review this subroutine configuration for logical errors or improvements."
            self.trigger_ai_request(prompt, context_json)

    def show_vision_overlay(self, pixmap, data): self.overlay = VisionOverlay(pixmap, data, self.window()); self.overlay.show(); self.toast.show_message("AI: Element located.", False)

    def handle_code_fix(self):
        error_context = ""
        if self.editor.current_errors:
            first_line = min(self.editor.current_errors.keys()); error_msg = self.editor.current_errors[first_line]
            error_context = f"Syntax Error at line {first_line+1}: {error_msg}"

        dialog = AIQueryDialog(self, error_context)
        if dialog.exec():
            user_input = dialog.get_text()
            code_text = self.editor.text()
            context_json = self.get_relevant_context(code_text)
            
            prompt = ""
            if user_input: prompt = f"User Query: {user_input}\n\nCode Segment:\n{code_text}\n\nError Context:\n{error_context}"
            elif error_context: prompt = f"Fix this syntax error:\n{error_context}\n\nCode:\n{code_text}"
            else: prompt = f"Analyze this code for logical or semantic errors. Explain what it does and suggest improvements:\n\n{code_text}"

            self.trigger_ai_request(prompt, context_json, mode="code_fix")

    def trigger_ai_request(self, prompt, context_json, mode="chat"):
        if not GeminiWorker: self.toast.show_message("AI Client not available.", True); return
        self.toast.show_message("AI: Analyzing...", False)
        
        full_prompt = f"{prompt}\n\n[Relevant Function Documentation]\n{context_json}\n\n{PARSING_RULES}"
        use_case = "code_fix" if mode == "code_fix" else "chat"
        
        if mode == "code_fix": self.pre_ai_code = self.editor.text()

        self.worker = GeminiWorker(full_prompt, use_case=use_case)
        self.worker.response_received.connect(self.show_ai_response)
        if mode == "code_fix": self.worker.code_fix_received.connect(self.apply_code_fix)
        self.worker.start()

    def show_ai_response(self, text): self.bubble = AIBubble(self.window(), text)

    def apply_code_fix(self, fix_obj):
        if hasattr(fix_obj, 'fixed_code'):
            self.post_ai_code = fix_obj.fixed_code
            self.editor.setText(self.post_ai_code) 
            self.ai_undo_hud.show_undo()
            self.toast.show_message(f"AI: Code Updated. {getattr(fix_obj, 'explanation', '')}")
        else:
            self.show_ai_response(str(fix_obj))

    def undo_ai_fix(self):
        self.editor.setText(self.pre_ai_code)
        self.toast.show_message("Reverted to pre-AI state.")

    def redo_ai_fix(self):
        self.editor.setText(self.post_ai_code)
        self.toast.show_message("Redone AI changes.")

    def receive_metadata(self, meta):
        self.viewer_metadata = meta
        self.toast.show_message(f"Metadata Captured: {os.path.basename(meta.get('filename',''))}")

    def fill_card_metadata(self, card_widget):
        if not self.viewer_metadata: self.toast.show_message("No Viewer Data. Open a file in 3D Viewer first.", True); return
        card_widget.apply_viewer_metadata(self.viewer_metadata); self.toast.show_message("Parameters Pasted.")

    def add_subroutine(self):
        sub = SubroutineWidget(f"Subroutine {len(self.subroutines)+1}"); sub.sync_request.connect(self.sync_visual_to_ide); sub.delete_requested.connect(self.remove_subroutine); sub.ai_help_requested.connect(self.handle_console_help)
        sub.request_viewer_metadata.connect(self.fill_card_metadata)
        self.sub_layout.insertWidget(len(self.subroutines), sub); self.subroutines.append(sub); self.sync_visual_to_ide()

    def handle_console_help(self, text, sub_widget):
        context_json = self.get_relevant_context(self.editor.text())
        dialog = AIQueryDialog(self, f"Console Error: {text[:100]}...")
        if dialog.exec():
            user_input = dialog.get_text()
            prompt = f"Console Error:\n{text}\n\nUser Query: {user_input}"
            self.trigger_ai_request(prompt, context_json, mode="chat") 

    def remove_subroutine(self, sub_widget):
        if sub_widget in self.subroutines: self.subroutines.remove(sub_widget); sub_widget.setParent(None); sub_widget.deleteLater(); self.sync_visual_to_ide()
    def sync_visual_to_ide(self):
        if self.is_syncing: return
        self.is_syncing = True; full_code = ["# GENERATED BY SMART IDE", "import os", "import numpy as np", "import pypore3d"]; 
        for mod in global_library.modules: full_code.append(f"from pypore3d import {mod}")
        full_code.append("")
        for sub in self.subroutines: full_code.append(sub.to_clst_block()); full_code.append("")
        code_str = "\n".join(full_code); self.editor.setText(code_str); self.last_valid_code = code_str; self.is_syncing = False
    def on_code_typed(self):
        if self.is_syncing: return
        self.sync_timer.start()
        self.ai_undo_hud.hide()
    
    # --- FIX 3: NON-DESTRUCTIVE SYNC (PRESERVES UI STATE) ---
    def sync_ide_to_visual(self):
        code = self.editor.text()
        if "<CLST_SUBROUTINE" in code and "</CLST_SUBROUTINE>" not in code: self.show_sync_error("Broken Subroutine Tags"); return
        self.hide_sync_error(); self.is_syncing = True
        
        # Parse Code
        import ast
        sub_pattern = re.compile(r'# <CLST_SUBROUTINE name="(.*?)">(.*?)(# <CLST_NOTE>(.*?)</CLST_NOTE>)?(.*?)(?=# </CLST_SUBROUTINE>)', re.DOTALL)
        func_pattern = re.compile(r'# <CLST_FUNC id="(.*?)">\n(.*?)\n# </CLST_FUNC>', re.DOTALL)
        
        matches = list(sub_pattern.finditer(code))
        
        # 1. Adjust Subroutine Count (Keep existing widgets if possible)
        while len(self.subroutines) > len(matches):
            rem = self.subroutines.pop()
            rem.setParent(None); rem.deleteLater()
        
        while len(self.subroutines) < len(matches):
            new_sub = SubroutineWidget(f"Subroutine {len(self.subroutines)+1}")
            new_sub.sync_request.connect(self.sync_visual_to_ide)
            new_sub.delete_requested.connect(self.remove_subroutine)
            new_sub.ai_help_requested.connect(self.handle_console_help)
            new_sub.request_viewer_metadata.connect(self.fill_card_metadata)
            self.subroutines_container.layout().insertWidget(len(self.subroutines), new_sub)
            self.subroutines.append(new_sub)
            
        # 2. Update Content Non-Destructively
        for i, match in enumerate(matches):
            sub = self.subroutines[i]
            sub_name = match.group(1)
            if sub.name_label.text() != sub_name: sub.name_label.setText(sub_name)
            
            content = match.group(0)
            f_matches = list(func_pattern.finditer(content))
            
            # Adjust Card Count
            while len(sub.functions) > len(f_matches):
                rem = sub.functions.pop()
                rem.setParent(None); rem.deleteLater()
            
            while len(sub.functions) < len(f_matches):
                # Placeholder, will be morphed below
                dummy_meta = list(global_library.functions.values())[0]
                sub.add_function_card(dummy_meta, None)
                
            for j, fm in enumerate(f_matches):
                card = sub.functions[j]
                fn_id = fm.group(1); code_line = fm.group(2)
                
                # Check for ID Mismatch (Function Changed in Code?)
                if card.metadata['id'] != fn_id:
                    # In this case, we MUST replace the card because layout differs
                    new_meta = global_library.id_map.get(fn_id)
                    if new_meta:
                        # Remove old
                        old_card = sub.functions[j]
                        sub.func_container.removeWidget(old_card)
                        old_card.deleteLater()
                        # Insert new
                        new_card = FunctionCard(new_meta, None)
                        new_card.code_changed.connect(sub.propagate_change)
                        new_card.delete_requested.connect(sub.remove_function)
                        new_card.run_requested.connect(sub.run_single_function)
                        new_card.request_viewer_metadata.connect(sub.request_viewer_metadata.emit)
                        sub.func_container.insertWidget(j, new_card)
                        sub.functions[j] = new_card
                        card = new_card

                # Update Values from Code AST
                try:
                    tree = ast.parse(code_line)
                    call_node = None
                    for node in tree.body:
                        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call): call_node = node.value
                        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call): 
                            call_node = node.value
                            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                                card.return_var = node.targets[0].id
                                card.basket_item.setText(f"ðŸ“„ {card.return_var}" if card.basket_item.var_type.endswith("array") else f"x= {card.return_var}")
                    
                    if call_node: 
                        # Use blockSignals to prevent loop
                        card.blockSignals(True)
                        card.populate_from_ast_call(call_node)
                        card.blockSignals(False)
                except: pass

        self.last_valid_code = code; self.is_syncing = False

    def show_sync_error(self, msg): self.visual_tab.setEnabled(False); self.lbl_err.setText(f"Error: {msg}"); self.float_revert.show_animated(); self.toast.show_message(f"Sync Error: {msg}", True)
    def hide_sync_error(self): self.visual_tab.setEnabled(True); self.lbl_err.setText(""); self.float_revert.hide()
    def revert_code(self): self.is_syncing = True; self.editor.setText(self.last_valid_code); self.hide_sync_error(); self.is_syncing = False; self.toast.show_message("Code reverted to last valid state.")
    def update_stats(self, line, index): line, col = self.editor.getCursorPosition(); self.lbl_stats.setText(f"Ln {line+1}, Col {col+1} | Python")
    def run_code(self): self.btn_run.setEnabled(False); self.runner = PythonRunner(self.editor.text()); self.runner.output_signal.connect(lambda s: self.toast.show_message("Execution Started")); self.runner.error_signal.connect(lambda s: self.toast.show_message(f"Error: {s}", True)); self.runner.finished.connect(lambda: self.btn_run.setEnabled(True)); self.runner.start()
    def load_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open", "", "Code (*.py *.txt)")
        if fname:
            with open(fname, 'r', encoding='utf-8') as f: content = f.read(); self.editor.setText(content); self.sync_ide_to_visual()
            self.tabs.setCurrentIndex(1); self.toast.show_message(f"Loaded: {os.path.basename(fname)}")
    def save_file(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Save", "", "Code (*.py *.txt)")
        if fname:
            with open(fname, 'w') as f: f.write(self.editor.text())
            self.toast.show_message(f"Saved to: {os.path.basename(fname)}")
    def toggle_theme(self): self.is_dark_mode = not self.is_dark_mode; self.apply_theme()
    def apply_theme(self):
        t = Theme.DARK 
        self.setStyleSheet(f"QWidget {{ background-color: {t['app_bg']}; color: {t['text_main']}; font-family: 'Segoe UI'; }} QTabWidget::pane {{ border: none; }} QTabBar::tab {{ background: {t['panel_bg']}; color: {t['text_dim']}; padding: 8px 12px; margin-right: 2px; }} QTabBar::tab:selected {{ background: {t['card_bg']}; color: {t['text_main']}; border-bottom: 2px solid {t['accent']}; }} QScrollBar:vertical {{ background: {t['app_bg']}; width: 10px; }} QScrollBar::handle:vertical {{ background: #555; border-radius: 5px; }}")
        self.editor.setPaper(QColor(t['app_bg'])); self.editor.setColor(QColor(t['text_main'])); self.editor.setCaretForegroundColor(QColor(t['accent'])); self.editor.setSelectionBackgroundColor(QColor(t['accent']+"44")); self.editor.setMarginsBackgroundColor(QColor(t['panel_bg'])); self.editor.setMarginsForegroundColor(QColor(t['text_dim']))
        self.status_bar.setStyleSheet(f"background-color: {Theme.DARK['accent']}; color: white;")

if __name__ == "__main__":
    app = QApplication(sys.argv); ide = SmartIDEWidget(); ide.resize(1100, 800); ide.setWindowTitle("Pypore3D Mirror Studio"); ide.show(); sys.exit(app.exec())