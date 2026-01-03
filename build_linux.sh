#!/bin/bash
# =====================================================
# CubeLab - Linux Build Script
# Creates standalone AppImage executables
# =====================================================

set -e

echo ""
echo "========================================================"
echo "  CUBE LAB - LINUX APPIMAGE BUILD"
echo "========================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check system dependencies
log_info "[0/9] Checking system dependencies..."

MISSING_DEPS=""
for pkg in libgl1-mesa-dev libxcb-xinerama0 libxkbcommon-x11-0; do
    if ! dpkg -l | grep -q "$pkg"; then
        MISSING_DEPS="$MISSING_DEPS $pkg"
    fi
done

if [ -n "$MISSING_DEPS" ]; then
    log_warn "Missing packages:$MISSING_DEPS"
    echo "        Install with: sudo apt install$MISSING_DEPS"
    echo ""
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    log_error "Python3 is not installed"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    log_info "[1/9] Creating virtual environment..."
    python3 -m venv venv
fi

log_info "[2/9] Activating virtual environment..."
source venv/bin/activate

log_info "[3/9] Upgrading pip..."
pip install --upgrade pip --quiet

log_info "[4/9] Installing dependencies..."
pip install -r requirements.txt --quiet

log_info "[5/9] Installing pypore3d from TestPyPI..."
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ pypore3d 2>/dev/null || {
    log_warn "pypore3d installation had issues - continuing anyway"
}

log_info "[6/9] Verifying imports..."
python3 -c "import PyQt6; import pyvista; import vtk; print('Core OK')"
python3 -c "import pypore3d; print('pypore3d OK')" 2>/dev/null || log_warn "pypore3d not available"

log_info "[7/9] Building executables with PyInstaller..."
echo ""
echo "        Building CubeLab..."
pyinstaller --clean --noconfirm cubelab.spec

echo "        Building CubeLab-UserTesting..."
pyinstaller --clean --noconfirm cubelab-usertesting.spec

log_info "[8/9] Downloading AppImage tools..."

mkdir -p installers
cd installers

# Download appimagetool if not present
if [ ! -f "appimagetool-x86_64.AppImage" ]; then
    echo "        Downloading appimagetool..."
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" -O appimagetool-x86_64.AppImage
    chmod +x appimagetool-x86_64.AppImage
fi

cd ..

log_info "[9/9] Creating AppImages..."

# Function to create AppImage
create_appimage() {
    local APP_NAME=$1
    local DISPLAY_NAME=$2
    local EXEC_NAME=$3
    local ICON_NAME=$4
    
    if [ ! -d "dist/${APP_NAME}" ]; then
        log_warn "${APP_NAME} not found in dist/"
        return
    fi
    
    echo "        Creating ${APP_NAME}.AppImage..."
    
    # Create AppDir structure
    APPDIR="AppDir-${APP_NAME}"
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR/usr/bin"
    mkdir -p "$APPDIR/usr/lib"
    mkdir -p "$APPDIR/usr/share/applications"
    mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
    
    # Copy application
    cp -r "dist/${APP_NAME}"/* "$APPDIR/usr/bin/"
    
    # Create desktop file
    cat > "$APPDIR/usr/share/applications/${ICON_NAME}.desktop" << EOF
[Desktop Entry]
Name=${DISPLAY_NAME}
Exec=${EXEC_NAME}
Icon=${ICON_NAME}
Type=Application
Categories=Science;Education;Development;
Comment=3D Image Processing IDE for pypore3d
Terminal=false
EOF
    
    # Copy to AppDir root (required)
    cp "$APPDIR/usr/share/applications/${ICON_NAME}.desktop" "$APPDIR/"
    
    # Copy icon
    if [ -f "src/resources/images/Icon.png" ]; then
        cp "src/resources/images/Icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/${ICON_NAME}.png"
        cp "src/resources/images/Icon.png" "$APPDIR/${ICON_NAME}.png"
    else
        # Create placeholder icon
        echo "        [Note] Icon.png not found, using placeholder"
        convert -size 256x256 xc:navy -fill white -gravity center -pointsize 48 -annotate 0 "CL" "$APPDIR/${ICON_NAME}.png" 2>/dev/null || true
    fi
    
    # Create AppRun
    cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${HERE}/usr/bin:${LD_LIBRARY_PATH}"
export QT_PLUGIN_PATH="${HERE}/usr/bin/PyQt6/Qt6/plugins"
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS}"
cd "${HERE}/usr/bin"
EOF
    echo "exec \"\${HERE}/usr/bin/${EXEC_NAME}\" \"\$@\"" >> "$APPDIR/AppRun"
    chmod +x "$APPDIR/AppRun"
    
    # Build AppImage
    ARCH=x86_64 ./installers/appimagetool-x86_64.AppImage --no-appstream "$APPDIR" "installers/${APP_NAME}-x86_64.AppImage" 2>/dev/null || {
        log_warn "AppImage creation failed for ${APP_NAME}"
        # Fallback to tarball
        cd dist
        tar -czvf "../installers/${APP_NAME}-Linux-x86_64.tar.gz" "${APP_NAME}/"
        cd ..
        echo "        Created fallback: installers/${APP_NAME}-Linux-x86_64.tar.gz"
    }
    
    # Cleanup
    rm -rf "$APPDIR"
    
    if [ -f "installers/${APP_NAME}-x86_64.AppImage" ]; then
        chmod +x "installers/${APP_NAME}-x86_64.AppImage"
        echo "        Created: installers/${APP_NAME}-x86_64.AppImage"
    fi
}

# Create AppImages
create_appimage "CubeLab" "Cube Lab" "CubeLab" "cubelab"
create_appimage "CubeLab-UserTesting" "Cube Lab - User Testing" "CubeLab-UserTesting" "cubelab-usertesting"

echo ""
echo "========================================================"
echo "  BUILD COMPLETE!"
echo "========================================================"
echo ""
echo "  Outputs in: installers/"
echo ""
ls -la installers/*.AppImage installers/*.tar.gz 2>/dev/null || echo "  (No files found)"
echo ""
echo "  Users can now:"
echo "    1. Download the .AppImage file"
echo "    2. chmod +x CubeLab-x86_64.AppImage (or right-click > Properties > Executable)"
echo "    3. Double-click to run!"
echo "    No installation, no dependencies needed."
echo ""
