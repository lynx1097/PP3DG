#!/bin/bash
# =====================================================
# CubeLab - macOS Build Script
# Creates standalone DMG installers
# =====================================================

set -e

echo ""
echo "========================================================"
echo "  CUBE LAB - macOS INSTALLER BUILD"
echo "========================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check Python
if ! command -v python3 &> /dev/null; then
    log_error "Python3 is not installed"
    echo "        Install with: brew install python3"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    log_info "[1/8] Creating virtual environment..."
    python3 -m venv venv
fi

log_info "[2/8] Activating virtual environment..."
source venv/bin/activate

log_info "[3/8] Upgrading pip..."
pip install --upgrade pip --quiet

log_info "[4/8] Installing dependencies..."
pip install -r requirements.txt --quiet

log_info "[5/8] Installing pypore3d from TestPyPI..."
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ pypore3d 2>/dev/null || {
    log_warn "pypore3d installation had issues - continuing anyway"
}

log_info "[6/8] Verifying imports..."
python3 -c "import PyQt6; import pyvista; import vtk; print('Core OK')"
python3 -c "import pypore3d; print('pypore3d OK')" 2>/dev/null || log_warn "pypore3d not available"

log_info "[7/8] Building app bundles with PyInstaller..."
echo ""
echo "        Building CubeLab..."
pyinstaller --clean --noconfirm cubelab.spec

echo "        Building CubeLab-UserTesting..."
pyinstaller --clean --noconfirm cubelab-usertesting.spec

log_info "[8/8] Creating DMG installers..."

mkdir -p installers

# Function to create DMG
create_dmg_installer() {
    local APP_NAME=$1
    local DMG_NAME=$2
    local VOLUME_NAME=$3
    
    if [ -d "dist/${APP_NAME}.app" ]; then
        echo "        Creating ${DMG_NAME}..."
        
        # Check if create-dmg is available
        if command -v create-dmg &> /dev/null; then
            create-dmg \
                --volname "${VOLUME_NAME}" \
                --volicon "src/resources/images/Icon.icns" \
                --window-pos 200 120 \
                --window-size 600 400 \
                --icon-size 100 \
                --icon "${APP_NAME}.app" 150 185 \
                --hide-extension "${APP_NAME}.app" \
                --app-drop-link 450 185 \
                --no-internet-enable \
                "installers/${DMG_NAME}" \
                "dist/${APP_NAME}.app" 2>/dev/null || {
                    # Fallback to simple DMG
                    hdiutil create -volname "${VOLUME_NAME}" -srcfolder "dist/${APP_NAME}.app" -ov -format UDZO "installers/${DMG_NAME}"
                }
        else
            # Use hdiutil directly
            hdiutil create -volname "${VOLUME_NAME}" -srcfolder "dist/${APP_NAME}.app" -ov -format UDZO "installers/${DMG_NAME}"
        fi
        
        echo "        Created: installers/${DMG_NAME}"
    else
        log_warn "${APP_NAME}.app not found in dist/"
    fi
}

# Create DMGs
create_dmg_installer "CubeLab" "CubeLab-1.0.0-macOS.dmg" "Cube Lab"
create_dmg_installer "CubeLab-UserTesting" "CubeLab-UserTesting-1.0.0-macOS.dmg" "Cube Lab - User Testing"

echo ""
echo "========================================================"
echo "  BUILD COMPLETE!"
echo "========================================================"
echo ""
echo "  Outputs in: installers/"
echo ""
ls -la installers/*.dmg 2>/dev/null || echo "  (No DMG files found)"
echo ""
echo "  Users can now:"
echo "    1. Double-click the DMG"
echo "    2. Drag app to Applications folder"
echo "    3. Done! No dependencies needed."
echo ""
