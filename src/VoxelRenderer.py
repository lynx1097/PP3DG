import sys , os , re , traceback , datetime , vtk, json
import numpy as np
import pyvista as pv

from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QDialog, QFormLayout, 
    QComboBox, QSpinBox, QCheckBox, QSlider, QMessageBox, 
    QGroupBox, QLineEdit, QFrame, QStyle, QSizePolicy, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QSize, QEvent, QPoint, QUrl
from PyQt6.QtGui import QPainter, QPixmap, QColor, QImage, QMovie, QDesktopServices
from pyvistaqt import QtInteractor
from PIL import Image 

# --- 1. CONFIGURATION ---

LOADING_GIF_PATH = str(Path(__file__).parent.parent / 'resources' / 'images' / 'loading.gif')

# CONSTANT STYLES
BTN_STYLE_DEFAULT = "background-color: #3d3d3d; border: 1px solid #555; padding: 5px; border-radius: 4px; color: #fff;"
BTN_STYLE_SUCCESS = "background-color: #2e7d32; border: 1px solid #1b5e20; padding: 5px; border-radius: 4px; color: #fff;"
BTN_STYLE_ACTIVE  = "background-color: #007acc; border: 1px solid #005c99; padding: 5px; border-radius: 4px; color: #fff;"

def configure_rendering_device():
    if "LIBGL_ALWAYS_SOFTWARE" in os.environ:
        del os.environ["LIBGL_ALWAYS_SOFTWARE"]
    os.environ["MESA_GL_VERSION_OVERRIDE"] = "4.5"
    os.environ["MESA_GLSL_VERSION_OVERRIDE"] = "450"
    pv.global_theme.volume_mapper = 'smart'
    pv.global_theme.allow_empty_mesh = True

STYLESHEET = f"""
QWidget {{ font-size: 9pt; color: #f0f0f0; font-family: Segoe UI, Arial; }}
QGroupBox {{ border: 1px solid #444; border-radius: 6px; margin-top: 12px; font-weight: bold; background-color: #2b2b2b; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #aaa; }}
QGroupBox#ControlsGroup > QWidget, QGroupBox#ControlsGroup > QLabel, 
QGroupBox#ControlsGroup > QSlider {{ border: none; background: transparent; }}
QFrame#LoadingFrame, QFrame#LoadingFrame > QLabel {{ border: none; background: transparent; }}
QPushButton {{ {BTN_STYLE_DEFAULT} }}
QPushButton:hover {{ background-color: #505050; border-color: #666; }}
QPushButton:pressed {{ background-color: #007acc; border-color: #007acc; }}
QPushButton:disabled {{ background-color: #2a2a2a; color: #555; border-color: #333; }}
QLineEdit, QSpinBox, QComboBox {{ background-color: #1e1e1e; border: 1px solid #555; padding: 3px; color: #fff; border-radius: 3px; }}
QSlider::groove:horizontal {{ border: 1px solid #3d3d3d; height: 6px; background: #202020; margin: 2px 0; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: #007acc; border: 1px solid #007acc; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
QSlider::groove:vertical {{ border: 1px solid #3d3d3d; width: 6px; background: #202020; margin: 0 2px; border-radius: 3px; }}
QSlider::handle:vertical {{ background: #007acc; border: 1px solid #007acc; height: 14px; width: 14px; margin: 0 -5px; border-radius: 7px; }}
QLabel {{ color: #d0d0d0; }}
"""

# --- NEW: FLOATING BUTTON FOR METADATA SHARE ---
class FloatingButton(QPushButton):
    def __init__(self, parent, icon_name="SP_FileDialogDetailedView"):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(QApplication.style().standardIcon(getattr(QStyle.StandardPixmap, icon_name)))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #007acc;
                border-radius: 20px;
                border: 2px solid #333;
            }}
            QPushButton:hover {{ background-color: #0098ff; }}
            QPushButton:pressed {{ background-color: #005a9e; }}
        """)
        shadow = QGraphicsOpacityEffect(self)
        shadow.setOpacity(0.9)
        self.setGraphicsEffect(shadow)

    def update_position(self):
        if self.parent():
            w, h = self.parent().width(), self.parent().height()
            self.move(w - 50, h - 50) # Bottom right

# --- 2. DATA STRUCTURES ---

class FileMetadata:
    def __init__(self, path, dims, dtype, size):
        self.path = path; self.dim_x = dims[0]; self.dim_y = dims[1]; self.dim_z = dims[2]
        self.dtype = dtype; self.size_bytes = size

# --- 3. WORKERS ---

class LoadWorker(QThread):
    finished = pyqtSignal(object, tuple); error = pyqtSignal(str)
    def __init__(self, metadata): super().__init__(); self.meta = metadata
    def run(self):
        try:
            data = np.fromfile(self.meta.path, dtype=self.meta.dtype)
            try: data = data.reshape((self.meta.dim_z, self.meta.dim_y, self.meta.dim_x))
            except: raise ValueError("Dims mismatch")
            self.finished.emit(data, (float(np.min(data)), float(np.max(data))))
        except Exception: self.error.emit(traceback.format_exc())

class ThresholdWorker(QThread):
    finished = pyqtSignal(object); error = pyqtSignal(str)
    def __init__(self, grid, val): super().__init__(); self.grid = grid; self.val = val
    def run(self):
        try:
            if self.grid is None: return
            target = 150; dims = self.grid.dimensions; mx = max(dims)
            if mx > target:
                s = int(np.ceil(mx/target))
                voi = vtk.vtkExtractVOI(); voi.SetInputData(self.grid); voi.SetSampleRate(s,s,s)
                voi.SetVOI(0,dims[0]-1,0,dims[1]-1,0,dims[2]-1); voi.Update()
                pg = pv.wrap(voi.GetOutput())
            else: pg = self.grid
            mesh = pg.contour([self.val])
            if mesh.n_points>0: mesh = mesh.decimate(0.5)
            mesh.clear_data(); self.finished.emit(mesh)
        except Exception: self.error.emit(traceback.format_exc())

class DynamicChunkWorker(QThread):
    finished = pyqtSignal(object)
    def __init__(self, grid, val, bounds): super().__init__(); self.grid=grid; self.val=val; self.b=bounds
    def run(self):
        try:
            ex = vtk.vtkExtractVOI(); ex.SetInputData(self.grid); ex.SetSampleRate(1,1,1)
            ex.SetVOI(self.b[0],self.b[1],self.b[2],self.b[3],self.b[4],self.b[5]); ex.Update()
            m = pv.wrap(ex.GetOutput()).contour([self.val]); m.clear_data(); self.finished.emit(m)
        except: pass

# --- 4. FLOATING CONTROL PANEL ---

class FloatingControlPanel(QDialog):
    def __init__(self, parent_top_level_window, viewer_ref):
        super().__init__(parent_top_level_window)
        self.viewer = viewer_ref
        self.is_open = True
        self.panel_width = 165
        
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.init_ui()
        self.setStyleSheet(STYLESHEET)

    def init_ui(self):
        self.main_layout = QHBoxLayout(self); self.main_layout.setContentsMargins(0,0,0,0); self.main_layout.setSpacing(0)

        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background-color: rgba(30, 30, 30, 245); border: 1px solid #555; border-radius: 8px;")
        self.content_frame.setFixedWidth(self.panel_width)
        
        self.panel_layout = QVBoxLayout(self.content_frame); self.panel_layout.setContentsMargins(5,10,5,10)

        gb_file = QGroupBox("File"); l_file = QVBoxLayout()
        self.btn_open = QPushButton("Open sample")
        self.btn_open.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.btn_open.setToolTip("Select Raw Data File")
        self.btn_open.clicked.connect(self.viewer.open_unified_dialog)
        l_file.addWidget(self.btn_open); gb_file.setLayout(l_file); self.panel_layout.addWidget(gb_file)

        gb_mode = QGroupBox("Rendering Mode"); l_mode = QVBoxLayout()
        self.combo_mode = QComboBox()
        self.combo_mode.setToolTip("Switch Visualization Method")
        self.combo_mode.addItems(["Vol-XRay", "Vol-CT", "Faces-Low", "Faces-High"])
        self.combo_mode.currentIndexChanged.connect(self.viewer.change_mode)
        l_mode.addWidget(self.combo_mode); gb_mode.setLayout(l_mode); self.panel_layout.addWidget(gb_mode)

        gb_ctrl = QGroupBox("Controls"); gb_ctrl.setObjectName("ControlsGroup"); l_ctrl = QVBoxLayout()
        l1 = QLabel("Opacity / Density:"); l1.setToolTip("Adjust visual density"); l_ctrl.addWidget(l1)
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal); self.slider_opacity.setRange(0, 100); self.slider_opacity.setValue(30)
        self.slider_opacity.setToolTip("Adjust Opacity"); self.slider_opacity.valueChanged.connect(self.viewer.update_opacity_live)
        l_ctrl.addWidget(self.slider_opacity)
        
        self.lbl_thresh = QLabel("Threshold:"); self.lbl_thresh.setToolTip("Surface Threshold")
        self.slider_threshold = QSlider(Qt.Orientation.Horizontal); self.slider_threshold.setRange(0, 100); self.slider_threshold.setValue(50)
        self.slider_threshold.setToolTip("Set Iso-value"); self.slider_threshold.valueChanged.connect(self.viewer.on_thresh_slide)
        self.lbl_thresh_val = QLabel("Val: N/A"); self.lbl_thresh_val.setToolTip("Current Value")
        self.chk_edges = QCheckBox("Show Edges"); self.chk_edges.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_CommandLink))
        self.chk_edges.setToolTip("Toggle Wireframe"); self.chk_edges.toggled.connect(self.viewer.toggle_edges)
        
        self.thresh_widgets = [self.lbl_thresh, self.slider_threshold, self.lbl_thresh_val, self.chk_edges]
        l_ctrl.addWidget(self.lbl_thresh); l_ctrl.addWidget(self.slider_threshold); l_ctrl.addWidget(self.lbl_thresh_val); l_ctrl.addWidget(self.chk_edges)
        gb_ctrl.setLayout(l_ctrl); self.panel_layout.addWidget(gb_ctrl)

        gb_tools = QGroupBox("Tools"); l_tools = QVBoxLayout()
        self.btn_slice = QPushButton("Slicing Mode: OFF"); self.btn_slice.setCheckable(True); self.btn_slice.setToolTip("Toggle 3D Slicing and Locking")
        self.btn_slice.clicked.connect(self.viewer.toggle_slicing_mode)
        l_tools.addWidget(self.btn_slice)

        self.btn_save_slice = QPushButton("Save Slice"); self.btn_save_slice.setVisible(False)
        self.btn_save_slice.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)); self.btn_save_slice.setToolTip("Export current slice to Image")
        self.btn_save_slice.clicked.connect(self.viewer.export_slice_image)
        l_tools.addWidget(self.btn_save_slice)

        self.btn_reset = QPushButton("Reset Cam"); self.btn_reset.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_reset.setToolTip("Reset Camera View"); self.btn_reset.clicked.connect(self.viewer.reset_view)
        self.btn_snap = QPushButton("Snapshot"); self.btn_snap.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
        self.btn_snap.setToolTip("Capture Screen"); self.btn_snap.clicked.connect(self.viewer.take_screenshot)
        l_tools.addWidget(self.btn_reset); l_tools.addWidget(self.btn_snap)
        gb_tools.setLayout(l_tools); self.panel_layout.addWidget(gb_tools)

        self.panel_layout.addStretch()
        
        # --- NEW: OPEN FOLDER BUTTON ---
        self.btn_open_folder = QPushButton("  Output Folder")
        self.btn_open_folder.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        self.btn_open_folder.clicked.connect(self.viewer.open_output_folder)
        self.panel_layout.addWidget(self.btn_open_folder)

        self.loading_frame = QFrame(); self.loading_frame.setObjectName("LoadingFrame")
        l_load = QVBoxLayout(self.loading_frame)
        self.lbl_loading_gif = QLabel(); self.lbl_loading_gif.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movie = QMovie(LOADING_GIF_PATH); self.movie.setScaledSize(QSize(25, 25)); self.lbl_loading_gif.setMovie(self.movie)
        lbl_lt = QLabel("Rendering..."); lbl_lt.setStyleSheet("color: orange; font-weight: bold; font-size: 8pt;"); lbl_lt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_load.addWidget(self.lbl_loading_gif); l_load.addWidget(lbl_lt); self.loading_frame.hide()
        self.panel_layout.addWidget(self.loading_frame)

        self.btn_toggle = QPushButton(); self.btn_toggle.setObjectName("toggleBtn"); self.btn_toggle.setFixedWidth(20); self.btn_toggle.setFixedHeight(60)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor); self.btn_toggle.clicked.connect(self.toggle_panel)
        self.update_icon()

        l_btn = QVBoxLayout(); l_btn.addStretch(); l_btn.addWidget(self.btn_toggle); l_btn.addStretch()
        self.main_layout.addWidget(self.content_frame); self.main_layout.addLayout(l_btn); self.main_layout.addStretch()
        self.toggle_threshold_controls(False)

    def update_icon(self):
        icon = QStyle.StandardPixmap.SP_ArrowLeft if self.is_open else QStyle.StandardPixmap.SP_ArrowRight
        self.btn_toggle.setIcon(self.style().standardIcon(icon))

    def toggle_panel(self):
        w_start = self.content_frame.width(); w_end = 0 if self.is_open else self.panel_width
        self.anim = QPropertyAnimation(self.content_frame, b"maximumWidth"); self.anim.setDuration(250)
        self.anim.setStartValue(w_start); self.anim.setEndValue(w_end); self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(lambda: self.content_frame.setFixedWidth(w_end))
        self.anim.start(); self.is_open = not self.is_open; self.update_icon()

    def toggle_threshold_controls(self, show):
        for w in self.thresh_widgets: w.setVisible(show)

    def set_loading(self, busy):
        self.content_frame.setEnabled(not busy)
        if busy: self.loading_frame.show(); self.movie.start(); QApplication.processEvents()
        else: self.movie.stop(); self.loading_frame.hide()

# --- 5. UNIFIED DIALOG ---
class UnifiedLoadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Import Data"); self.setModal(True); self.setMinimumWidth(400)
        self.dtypes = { "Uint8": np.uint8, "Int8": np.int8, "Uint16": np.uint16, "Int16": np.int16, "Int32": np.int32, "Uint32": np.uint32, "Float32": np.float32 }
        self.selected_file_size = 0; self.init_ui()
    def init_ui(self):
        l = QVBoxLayout(self); f = QFormLayout(); self.txt = QLineEdit(); self.txt.setReadOnly(True)
        btn = QPushButton("Browse..."); btn.clicked.connect(self.browse)
        h = QHBoxLayout(); h.addWidget(self.txt); h.addWidget(btn); f.addRow("File:", h)
        self.sx=self._s(); self.sy=self._s(); self.sz=self._s()
        h2 = QHBoxLayout(); h2.addWidget(QLabel("X:")); h2.addWidget(self.sx); h2.addWidget(QLabel("Y:")); h2.addWidget(self.sy); h2.addWidget(QLabel("Z:")); h2.addWidget(self.sz); f.addRow("Dims:", h2)
        self.cb = QComboBox(); self.cb.addItem("-"); self.cb.addItems(self.dtypes.keys()); self.cb.currentIndexChanged.connect(self.val); f.addRow("Type:", self.cb)
        self.st = QLabel(""); self.st.setFont(self.font()); f.addRow("", self.st); l.addLayout(f)
        h3 = QHBoxLayout(); self.b_ok = QPushButton("Load"); self.b_ok.setEnabled(False); self.b_ok.clicked.connect(self.accept)
        b_c = QPushButton("Cancel"); b_c.clicked.connect(self.reject); h3.addStretch(); h3.addWidget(b_c); h3.addWidget(self.b_ok); l.addLayout(h3)
    def _s(self): s = QSpinBox(); s.setRange(0,99999); s.valueChanged.connect(self.val); return s
    def browse(self): 
        f, _ = QFileDialog.getOpenFileName(self, "Raw", "", "*.raw")
        if f: self.txt.setText(f); self.selected_file_size = os.path.getsize(f); self.parse_filename(f); self.val()
    def parse_filename(self, path):
        name = os.path.basename(path)
        match = re.search(r'(\d+)[_x](\d+)[_x](\d+)', name)
        if match:
            dims = match.groups()
            self.sx.setValue(int(dims[0])); self.sy.setValue(int(dims[1])); self.sz.setValue(int(dims[2]))
    def val(self):
        if not self.txt.text() or self.cb.currentIndex()==0: self.b_ok.setEnabled(False); return
        sz = self.sx.value()*self.sy.value()*self.sz.value()*np.dtype(self.dtypes[self.cb.currentText()]).itemsize
        if sz != self.selected_file_size: self.b_ok.setEnabled(False); self.st.setText("Size Mismatch"); self.st.setStyleSheet("color: red; font-weight: bold;")
        else: self.b_ok.setEnabled(True); self.st.setText("OK"); self.st.setStyleSheet("color: #00ff00; font-weight: bold;")
    def get_metadata(self): return FileMetadata(self.txt.text(), (self.sx.value(), self.sy.value(), self.sz.value()), self.dtypes[self.cb.currentText()], self.selected_file_size)

# --- 6. VIEWER WIDGET (Main Logic) ---

class VoxelViewerWidget(QWidget):
    # NEW: Signal to share metadata (filename, dims, dtype)
    metadata_shared = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True) # ENABLE DROP
        self.grid = None; self.active_actor = None; self.slice_actor = None; self.current_mode_index = 0
        self.threshold_timer = QTimer(); self.threshold_timer.setSingleShot(True); self.threshold_timer.setInterval(200)
        self.threshold_timer.timeout.connect(self.trigger_threshold_worker)
        self.current_meta = {} # Store metadata
        
        self.slicing_active = False; self.slice_axis = 'x'
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(0,0,0,0)
        self.plotter = QtInteractor(self); self.plotter.set_background('white'); self.plotter.show_grid(color='navy')
        self.layout.addWidget(self.plotter)
        self.create_slice_sliders()
        self.plotter.interactor.AddObserver(vtk.vtkCommand.EndInteractionEvent, self.on_camera_stop)
        self.panel = None
        
        # NEW: Floating Share Button
        self.btn_share = FloatingButton(self.plotter, "SP_FileDialogDetailedView")
        self.btn_share.setToolTip("Pass File Metadata to Subroutine")
        self.btn_share.clicked.connect(self.share_metadata)

    def create_slice_sliders(self):
        self.frame_x = QFrame(self); self.frame_x.setStyleSheet("background: transparent;"); l_x = QHBoxLayout(self.frame_x)
        self.sl_x = QSlider(Qt.Orientation.Horizontal); self.sl_x.valueChanged.connect(lambda v: self.update_slice('x', v)); l_x.addWidget(QLabel("X:")); l_x.addWidget(self.sl_x); self.frame_x.hide()
        self.frame_y = QFrame(self); self.frame_y.setStyleSheet("background: transparent;"); l_y = QVBoxLayout(self.frame_y)
        self.sl_y = QSlider(Qt.Orientation.Vertical); self.sl_y.setInvertedAppearance(True); self.sl_y.valueChanged.connect(lambda v: self.update_slice('y', v)); l_y.addWidget(QLabel("Y:")); l_y.addWidget(self.sl_y); self.frame_y.hide()
        self.frame_z = QFrame(self); self.frame_z.setStyleSheet("background: transparent;"); l_z = QHBoxLayout(self.frame_z)
        self.sl_z = QSlider(Qt.Orientation.Horizontal); self.sl_z.valueChanged.connect(lambda v: self.update_slice('z', v)); l_z.addWidget(QLabel("Z:")); l_z.addWidget(self.sl_z); self.frame_z.hide()

    def resizeEvent(self, event):
        w, h = self.width(), self.height()
        self.frame_x.setGeometry(w//4, 10, w//2, 40)
        self.frame_y.setGeometry(w-50, h//4, 40, h//2)
        self.frame_z.setGeometry(w//4, h-50, w//2, 40)
        # Update Floating Button Pos
        self.btn_share.update_position()
        super().resizeEvent(event)

    def showEvent(self, event):
        if not self.panel:
            top = self.window()
            if top:
                self.panel = FloatingControlPanel(top, self)
                top.installEventFilter(self)
                self.panel.show(); self.update_panel_pos()
        super().showEvent(event)

    def eventFilter(self, source, event):
        if source == self.window():
            if event.type() == QEvent.Type.Move or event.type() == QEvent.Type.Resize: self.update_panel_pos()
            elif event.type() == QEvent.Type.WindowStateChange:
                if source.windowState() & Qt.WindowState.WindowMinimized: 
                    if self.panel: self.panel.hide()
                else: 
                    if self.panel and not self.panel.isVisible(): self.panel.show(); QTimer.singleShot(10, self.update_panel_pos)
        return super().eventFilter(source, event)

    def update_panel_pos(self):
        if not self.panel: return
        gp = self.mapToGlobal(QPoint(0, 0))
        self.panel.resize(self.panel.width(), int(self.height()*0.7))
        self.panel.move(gp.x(), gp.y()); self.panel.raise_()

    # --- HELPER: GET PATH FOR SAVING ---
    def get_save_path(self, category, filename_template):
        """
        Creates path: Documents/Cube-Lab/{category}/{YYYY-MM-DD}/{filename}
        """
        try:
            # 1. Base Documents/Cube-Lab
            base = Path(os.path.expanduser("~/Documents")) / "Cube-Lab"
            
            # 2. Date Subfolder
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            final_folder = base / category / date_str
            final_folder.mkdir(parents=True, exist_ok=True)
            
            # 3. Filename
            return final_folder / filename_template
        except Exception as e:
            self.on_error(f"Path Error: {e}")
            return None

    def open_output_folder(self):
        """Opens the current date folder in file explorer."""
        base = Path(os.path.expanduser("~/Documents")) / "Cube-Lab"
        # Try specific date folder, else base
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Check specific folders
        snap_dir = base / "screenshots" / date_str
        slide_dir = base / "slideshots" / date_str
        
        target = base
        if snap_dir.exists(): target = snap_dir
        elif slide_dir.exists(): target = slide_dir
        elif not base.exists():
            base.mkdir(parents=True, exist_ok=True)
            
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    # --- METADATA SHARING ---
    def share_metadata(self):
        if not self.current_meta:
            QMessageBox.warning(self, "No Data", "No file loaded to share.")
            return
        
        # Emit signal to GUI/IDE
        self.metadata_shared.emit(self.current_meta)
        
        # Visual feedback
        self.btn_share.setStyleSheet("background-color: #388e3c; border-radius: 20px; border: 2px solid #333;")
        QApplication.processEvents()
        QTimer.singleShot(300, lambda: self.btn_share.setStyleSheet("background-color: #007acc; border-radius: 20px; border: 2px solid #333;"))

    # --- DRAG & DROP HANDLERS ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-pypore3d-data"):
            event.accept()
        elif event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        # 1. From IDE (JSON Metadata)
        if event.mimeData().hasFormat("application/x-pypore3d-data"):
            data = event.mimeData().data("application/x-pypore3d-data")
            try:
                meta = json.loads(str(data, 'utf-8'))
                if 'filename' in meta and os.path.exists(meta['filename']):
                    dtype_guess = meta.get('dtype', 'uint8') 
                    self.load_raw_file(meta['filename'], meta.get('dimx',0), meta.get('dimy',0), meta.get('dimz',0), dtype_guess)
            except Exception as e:
                print(f"Drop Error: {e}")
        
        # 2. External File
        elif event.mimeData().hasUrls():
            path = event.mimeData().urls()[0].toLocalFile()
            if path.lower().endswith('.raw'):
                self.prompt_and_load(path)

    # --- LOGIC ---
    def toggle_slicing_mode(self):
        if self.grid is None: self.panel.btn_slice.setChecked(False); return
        if self.panel and not self.panel.content_frame.isEnabled(): self.panel.btn_slice.setChecked(False); return
        self.slicing_active = self.panel.btn_slice.isChecked(); btn = self.panel.btn_slice
        if self.slicing_active:
            btn.setText("Slicing Mode: ON"); btn.setStyleSheet(BTN_STYLE_ACTIVE); self.panel.btn_save_slice.setVisible(True); self.panel.btn_reset.setEnabled(False)
            dims = self.grid.dimensions
            self.sl_x.setRange(0, dims[0]-1); self.sl_x.setValue(dims[0]//2)
            self.sl_y.setRange(0, dims[1]-1); self.sl_y.setValue(dims[1]//2)
            self.sl_z.setRange(0, dims[2]-1); self.sl_z.setValue(dims[2]//2)
            self.frame_x.show(); self.frame_y.show(); self.frame_z.show()
            self.plotter.view_isometric(); self.plotter.disable()
            if self.active_actor:
                prop = self.active_actor.GetProperty()
                if self.current_mode_index < 2: 
                    try: prop.SetScalarOpacityUnitDistance(20.0)
                    except: pass
                else: prop.SetOpacity(0.5)
            self.update_slice('x', dims[0]//2)
        else:
            btn.setText("Slicing Mode: OFF"); btn.setStyleSheet(BTN_STYLE_DEFAULT); self.panel.btn_save_slice.setVisible(False); self.panel.btn_reset.setEnabled(True)
            self.frame_x.hide(); self.frame_y.hide(); self.frame_z.hide(); self.plotter.enable(); self.update_opacity_live()
            if self.slice_actor: self.plotter.remove_actor(self.slice_actor); self.slice_actor = None
    
    def update_slice(self, axis, index):
        if not self.slicing_active or self.grid is None: return
        self.slice_axis = axis; self.slice_index = index; dims = self.grid.dimensions
        if axis == 'x': i = min(max(index, 0), dims[0]-1); voi = (i, i, 0, dims[1]-1, 0, dims[2]-1)
        elif axis == 'y': j = min(max(index, 0), dims[1]-1); voi = (0, dims[0]-1, j, j, 0, dims[2]-1)
        else: k = min(max(index, 0), dims[2]-1); voi = (0, dims[0]-1, 0, dims[1]-1, k, k)
        slice_mesh = self.grid.extract_subset(voi)
        if self.slice_actor: self.plotter.remove_actor(self.slice_actor)
        current_cmap = "gray" if self.current_mode_index == 1 else "viridis"
        self.slice_actor = self.plotter.add_mesh(slice_mesh, cmap=current_cmap, clim=self.data_range, style='surface', opacity=1.0, lighting=False, show_scalar_bar=False)

    def export_slice_image(self):
        if self.grid is None: return
        try:
            arr = self.grid.active_scalars.reshape(self.grid.dimensions[::-1])
            if self.slice_axis == 'x': idx = min(self.slice_index, arr.shape[2]-1); img_data = arr[:, :, idx] 
            elif self.slice_axis == 'y': idx = min(self.slice_index, arr.shape[1]-1); img_data = arr[:, idx, :]
            else: idx = min(self.slice_index, arr.shape[0]-1); img_data = arr[idx, :, :]
            
            mn, mx = img_data.min(), img_data.max()
            img_norm = ((img_data - mn) / (mx - mn) * 255).astype(np.uint8) if mx > mn else img_data.astype(np.uint8)
            img = Image.fromarray(img_norm)
            
            # --- STRUCTURED SAVE ---
            raw_name = Path(self.current_meta.get('filename', 'Unknown')).stem
            time_str = datetime.datetime.now().strftime("%H-%M")
            fn_template = f"{time_str}-{raw_name}-slide-{self.slice_axis}-{self.slice_index}.png"
            
            save_path = self.get_save_path("slideshots", fn_template)
            if save_path:
                img.save(str(save_path))
                self.plotter.add_text(f"Saved: {save_path.name}", position='upper_right', color='green', font='courier', name='status')
                self.show_save_indicator(self.panel.btn_save_slice)
        except Exception as e: self.on_error(f"Slice Export Failed: {str(e)}")

    def open_unified_dialog(self): 
        d = UnifiedLoadDialog(self); 
        if d.exec(): self.load_data(d.get_metadata())
    
    def load_data(self, m): 
        if self.panel: self.panel.set_loading(True)
        # Store metadata for sharing later
        self.current_meta = {
            'filename': m.path, 'dimx': m.dim_x, 'dimy': m.dim_y, 'dimz': m.dim_z,
            'dtype': str(np.dtype(m.dtype)), 'filesize': m.size_bytes
        }
        self.lbl_info = self.findChild(QLabel) 
        # Trigger load
        self.loader = LoadWorker(m); self.loader.finished.connect(lambda d,r: self.on_loaded(d,r,m)); self.loader.error.connect(self.on_error); self.loader.start()
    
    def load_raw_file(self, fname, dx, dy, dz, dtype='uint8'):
        m = FileMetadata(fname, (dx, dy, dz), np.dtype(dtype), 0)
        self.load_data(m)

    def on_loaded(self, d, r, m): 
        if self.panel: self.panel.set_loading(False)
        self.grid = pv.wrap(d); self.data_range = r
        if self.panel: self.panel.lbl_thresh_val.setText(f"Range: {r[0]:.1f}-{r[1]:.1f}")
        self.update_view(reset=True)

    def change_mode(self):
        if not self.panel: return
        if self.slicing_active: self.panel.btn_slice.click()
        prev = self.current_mode_index; self.current_mode_index = self.panel.combo_mode.currentIndex()
        self.panel.toggle_threshold_controls(self.current_mode_index >= 2)
        if self.current_mode_index == 3:
            if QMessageBox.warning(self.panel, "Experimental", "High RAM usage. Continue?", QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
                self.panel.combo_mode.blockSignals(True); self.panel.combo_mode.setCurrentIndex(prev); self.panel.combo_mode.blockSignals(False); self.current_mode_index = prev; self.panel.toggle_threshold_controls(self.current_mode_index >= 2); return
        self.update_view(reset=False)

    def update_view(self, reset=False):
        if self.grid is None: return
        self.plotter.clear_actors(); self.active_actor = None; self.slice_actor = None; self.plotter.show_grid(color='navy')
        if self.panel: self.panel.set_loading(True)
        QApplication.processEvents()
        idx = self.current_mode_index
        if idx < 2: QTimer.singleShot(50, lambda: self._delayed_volume_render(idx == 1))
        else: self.trigger_threshold_worker()
        if reset: self.reset_view()

    def _delayed_volume_render(self, legacy): self.render_volume(legacy); 
    
    def render_volume(self, legacy):
        try:
            op = self.panel.slider_opacity.value()/100.0
            if legacy: self.active_actor = self.plotter.add_volume(self.grid, cmap="gray", opacity="sigmoid", clim=self.data_range, show_scalar_bar=False, mapper='smart')
            else: self.active_actor = self.plotter.add_volume(self.grid, cmap="viridis", mapper='smart', opacity=[0, op], clim=self.data_range, show_scalar_bar=True)
            self.update_opacity_live(); 
            if self.panel: self.panel.set_loading(False)
        except Exception as e: self.on_error(str(e))

    def update_opacity_live(self):
        if self.active_actor is None or not self.panel: return
        if self.slicing_active:
            prop = self.active_actor.GetProperty()
            if self.current_mode_index < 2: 
                try: prop.SetScalarOpacityUnitDistance(350.0) 
                except: pass
            else: prop.SetOpacity(0.35)
            self.plotter.render(); return
        val = self.panel.slider_opacity.value() / 100.0
        if self.current_mode_index < 2: 
            dist = (1.1 - val) * 10
            try: self.active_actor.GetProperty().SetScalarOpacityUnitDistance(dist)
            except: pass
        else: self.active_actor.GetProperty().SetOpacity(val)
        self.plotter.render()

    def on_thresh_slide(self):
        mn, mx = self.data_range; val = mn + (mx - mn) * (self.panel.slider_threshold.value() / 100.0)
        self.panel.lbl_thresh_val.setText(f"Thresh: {val:.2f}"); self.threshold_timer.start()

    def trigger_threshold_worker(self):
        if self.grid is None or self.current_mode_index < 2: return
        if self.panel: self.panel.set_loading(True)
        mn, mx = self.data_range; val = mn + (mx - mn) * (self.panel.slider_threshold.value() / 100.0)
        self.worker_th = ThresholdWorker(self.grid, val); self.worker_th.finished.connect(self.on_thresh_done); self.worker_th.error.connect(self.on_error); self.worker_th.start()

    def on_thresh_done(self, mesh):
        if self.panel: self.panel.set_loading(False)
        if self.current_mode_index == 3 and self.active_actor and getattr(self.active_actor, "_is_chunk", False): return
        self.plotter.clear_actors(); self.plotter.show_grid(color='navy')
        self.active_actor = self.plotter.add_mesh(mesh, color="orange", opacity=self.panel.slider_opacity.value()/100.0, show_edges=self.panel.chk_edges.isChecked(), show_scalar_bar=True)

    def toggle_edges(self):
        if self.active_actor and self.current_mode_index >= 2: self.active_actor.GetProperty().SetEdgeVisibility(self.panel.chk_edges.isChecked()); self.plotter.render()

    def on_camera_stop(self, obj, event):
        if self.slicing_active: return 
        if self.current_mode_index != 3 or self.grid is None: return
        cam = self.plotter.camera; dist = np.linalg.norm(np.array(cam.position) - np.array(cam.focal_point))
        if (dist / self.grid.length) < 0.4: self.update_high_res_chunk(np.array(cam.focal_point), dist)
        else:
            if self.active_actor and getattr(self.active_actor, "_is_chunk", False): self.trigger_threshold_worker()

    def update_high_res_chunk(self, focal, dist):
        r = dist * 0.6; bounds = [focal[0]-r, focal[0]+r, focal[1]-r, focal[1]+r, focal[2]-r, focal[2]+r]
        origin = np.array(self.grid.origin); spacing = np.array(self.grid.spacing); dims = np.array(self.grid.dimensions)
        idx_min = (np.array(bounds[::2]) - origin) / spacing; idx_max = (np.array(bounds[1::2]) - origin) / spacing
        imin, jmin, kmin = np.maximum(0, np.floor(idx_min)).astype(int); imax, jmax, kmax = np.minimum(dims-1, np.ceil(idx_max)).astype(int)
        if (imax-imin)*(jmax-jmin)*(kmax-kmin) > 50_000_000: return
        if self.panel: self.panel.set_loading(True)
        mn, mx = self.data_range; val = mn + (mx - mn) * (self.panel.slider_threshold.value() / 100.0)
        self.worker_lod = DynamicChunkWorker(self.grid, val, (imin, imax, jmin, jmax, kmin, kmax))
        self.worker_lod.finished.connect(self.on_chunk_ready); self.worker_lod.start()

    def on_chunk_ready(self, mesh):
        if self.panel: self.panel.set_loading(False)
        if self.current_mode_index != 3: return
        self.plotter.clear_actors(); self.plotter.show_grid(color='navy')
        self.active_actor = self.plotter.add_mesh(mesh, color="red", opacity=self.panel.slider_opacity.value()/100.0, show_edges=self.panel.chk_edges.isChecked())
        self.active_actor._is_chunk = True

    def reset_view(self): self.plotter.view_xy(); self.plotter.reset_camera()

    def take_screenshot(self):
        try:
            # --- STRUCTURED SAVE ---
            raw_name = Path(self.current_meta.get('filename', 'Unknown')).stem
            time_str = datetime.datetime.now().strftime("%H-%M")
            fn_template = f"{time_str}-{raw_name}-snap.png"
            
            save_path = self.get_save_path("screenshots", fn_template)
            if not save_path: return

            pix_l = self.panel.content_frame.grab(); arr = self.plotter.screenshot(None, return_img=True)
            h, w, _ = arr.shape; q_img = QImage(arr.copy().data, w, h, 3*w, QImage.Format.Format_RGB888); pix_r = QPixmap.fromImage(q_img)
            combined = QPixmap(pix_l.width()+pix_r.width(), max(pix_l.height(), pix_r.height()))
            combined.fill(QColor("white")); p = QPainter(combined); p.drawPixmap(0,0, pix_l); p.drawPixmap(pix_l.width(),0, pix_r); p.end()
            
            combined.save(str(save_path))
            
            self.show_save_indicator(self.panel.btn_snap)
        except Exception as e: self.on_error(str(e))

    def show_save_indicator(self, target_btn):
        if self.panel and target_btn:
            orig_text = target_btn.text(); target_btn.setText("Saved!"); target_btn.setStyleSheet(BTN_STYLE_SUCCESS)
            QTimer.singleShot(1000, lambda: self.reset_save_btn(target_btn, orig_text))
    
    def reset_save_btn(self, btn, text): btn.setText(text); btn.setStyleSheet(BTN_STYLE_DEFAULT)
    def on_error(self, msg): 
        print(msg);  
        if self.panel: self.panel.set_loading(False); QMessageBox.critical(self, "Error", msg)
    def prompt_and_load(self, fname):
        d_str, ok = QInputDialog.getText(self, "Dimensions", "Enter dims X,Y,Z (e.g. 512,512,100):")
        if ok and d_str:
            try:
                parts = [int(x.strip()) for x in d_str.split(',')]
                if len(parts) == 3: self.load_raw_file(fname, parts[0], parts[1], parts[2])
            except: pass
    
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Voxel Renderer"); self.resize(1280, 720); self.setCentralWidget(VoxelViewerWidget())

if __name__ == "__main__":
    configure_rendering_device()
    app = QApplication(sys.argv); app.setStyleSheet("QDialog { background-color: #2b2b2b; color: white; }"); win = MainWindow(); win.show(); sys.exit(app.exec())