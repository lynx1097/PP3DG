# 🚀 Cube Lab - Quick Start

## What You Get

| Platform | Users Download | Users Do |
|----------|---------------|----------|
| **Windows** | `CubeLab-Setup.exe` | Double-click → Install → Done! |
| **macOS** | `CubeLab.dmg` | Open → Drag to Applications → Done! |
| **Linux** | `CubeLab.AppImage` | Download → Run! (no install) |

**Zero dependencies for your users!** Everything is bundled.

---

## 🔨 Build Instructions

### 1. Add Your Icons

Copy to `src/resources/images/`:
```
Icon.ico      ← Windows (REQUIRED)
Icon.icns     ← macOS (REQUIRED)
Icon.png      ← Linux
Splash.jpg    ← Splash screen
loading.gif   ← Loading animation
```

### 2. Run Build Script

**Windows:**
```batch
build_windows.bat
```
→ Creates `installers/CubeLab-1.0.0-Windows-Setup.exe`

**macOS:**
```bash
./build_macos.sh
```
→ Creates `installers/CubeLab-1.0.0-macOS.dmg`

**Linux:**
```bash
./build_linux.sh
```
→ Creates `installers/CubeLab-x86_64.AppImage`

### 3. Distribute

Send the installer file to your alpha testers. That's it!

---

## 📋 Build Requirements

| Platform | You Need |
|----------|----------|
| Windows | Python 3.9+, [Inno Setup 6](https://jrsoftware.org/isinfo.php) (optional) |
| macOS | Python 3.9+, Xcode CLI Tools |
| Linux | Python 3.9+, `apt install libgl1-mesa-dev libxcb-xinerama0` |

---

## ✅ What's Bundled

- ✓ Python runtime
- ✓ All PyQt6/VTK/PyVista libraries
- ✓ pypore3d with SWIG extensions (from TestPyPI)
- ✓ Your API keys (.env)
- ✓ All config files

---

## 🎯 Two Packages

1. **CubeLab** (`GUI.py`) - Main application
2. **CubeLab-UserTesting** (`User-Testing.py`) - SUS testing with overlay

Both are built automatically by the scripts!
