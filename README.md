# Cube Lab - Standalone Installer Build System

Creates **fully standalone installers** that require **zero user interaction** with dependencies.

## 🎯 What This Creates

| Platform | Output | User Experience |
|----------|--------|-----------------|
| **Windows** | `CubeLab-1.0.0-Windows-Setup.exe` | Double-click → Install → Done |
| **macOS** | `CubeLab-1.0.0-macOS.dmg` | Open → Drag to Applications → Done |
| **Linux** | `CubeLab-x86_64.AppImage` | Download → Run (no install needed) |

**No Python, no pip, no dependencies for users!**

---

## 📁 Project Structure

```
cubelab_final/
├── src/                          # Your source code
│   ├── GUI.py                    # Main entry point
│   ├── User-Testing.py           # SUS testing entry point
│   ├── IDE.py, VoxelRenderer.py, etc.
│   ├── .env                      # API keys (bundled)
│   └── resources/images/         # ⚠️ ADD YOUR ICONS HERE
│       ├── Icon.ico              # Windows (required)
│       ├── Icon.icns             # macOS (required)
│       ├── Icon.png              # Linux (required)
│       ├── Splash.jpg
│       └── loading.gif
├── hooks/                        # PyInstaller hooks
│   ├── hook-pypore3d.py          # Bundles SWIG extensions
│   ├── hook-vtkmodules.py        # Bundles VTK
│   ├── hook-pyvista.py
│   └── hook-pyvistaqt.py
├── installers/                   # Inno Setup scripts
│   ├── cubelab-setup.iss
│   └── cubelab-usertesting-setup.iss
├── cubelab.spec                  # PyInstaller spec (main)
├── cubelab-usertesting.spec      # PyInstaller spec (testing)
├── build_windows.bat             # Windows build script
├── build_macos.sh                # macOS build script
├── build_linux.sh                # Linux build script
└── requirements.txt
```

---

## 🚀 Quick Start

### Step 1: Add Your Icons

Copy your icon files to `src/resources/images/`:
- `Icon.ico` (Windows) - 256x256 recommended
- `Icon.icns` (macOS) - Use `iconutil` to create
- `Icon.png` (Linux) - 256x256
- `Splash.jpg` - Splash screen
- `loading.gif` - Loading animation

### Step 2: Build

#### Windows
```batch
build_windows.bat
```
**Requirements:**
- Python 3.9+
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (optional, for .exe installer)

#### macOS
```bash
chmod +x build_macos.sh
./build_macos.sh
```
**Requirements:**
- Python 3.9+
- Xcode Command Line Tools
- `create-dmg` (optional): `brew install create-dmg`

#### Linux
```bash
chmod +x build_linux.sh
./build_linux.sh
```
**Requirements:**
- Python 3.9+
- System packages: `sudo apt install libgl1-mesa-dev libxcb-xinerama0 libxkbcommon-x11-0`

### Step 3: Distribute

Find your installers in the `installers/` folder:

| File | Size (approx) | Target Users |
|------|---------------|--------------|
| `CubeLab-1.0.0-Windows-Setup.exe` | ~400-600 MB | General users |
| `CubeLab-UserTesting-1.0.0-Windows-Setup.exe` | ~400-600 MB | Alpha testers |
| `CubeLab-1.0.0-macOS.dmg` | ~400-600 MB | macOS users |
| `CubeLab-x86_64.AppImage` | ~400-600 MB | Linux users |

---

## 📦 What's Bundled

Everything your users need is included:
- ✅ Python runtime
- ✅ PyQt6 + QScintilla
- ✅ PyVista + VTK (3D rendering)
- ✅ pypore3d (with SWIG extensions)
- ✅ Google GenAI (AI features)
- ✅ All configuration files
- ✅ API keys (.env)

---

## 🔧 pypore3d & SWIG

pypore3d is installed from **TestPyPI** during build:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ pypore3d
```

The SWIG-compiled extensions (`.pyd` on Windows, `.so` on Linux/macOS) are automatically bundled by the custom hook in `hooks/hook-pypore3d.py`.

---

## 🛠️ Customization

### Change App Name/Version
Edit the spec files:
```python
APP_NAME = "CubeLab"
APP_VERSION = "1.0.0"
```

### Reduce Package Size
Edit the spec files and add to `excludes`:
```python
excludes = [
    'matplotlib',
    'scipy',
    # etc.
]
```

### Add More Files
Edit the spec files `datas` section:
```python
datas = [
    ('path/to/file', 'destination'),
]
```

---

## ❓ Troubleshooting

### "pypore3d not found" warning
The build continues without pypore3d. Image processing won't work but the app will run.

### Icons not showing
Ensure icons exist in `src/resources/images/` with correct names.

### Windows: "ISCC not found"
Install [Inno Setup 6](https://jrsoftware.org/isinfo.php). The script will create ZIP files as fallback.

### macOS: Code signing errors
For distribution, you need an Apple Developer certificate. For testing, users can right-click → Open.

### Linux: OpenGL errors
```bash
sudo apt install libgl1-mesa-dev libglu1-mesa-dev
```

### AppImage doesn't run
```bash
chmod +x CubeLab-x86_64.AppImage
./CubeLab-x86_64.AppImage
```

---

## 📤 Distribution Checklist

Before sending to alpha testers:

- [ ] Icons added to `src/resources/images/`
- [ ] .env contains valid API keys
- [ ] Build completed without errors
- [ ] Tested installer on clean machine
- [ ] Uploaded to file sharing service

---

## 📄 License

MIT License
