@echo off
REM =====================================================
REM CubeLab - Windows Build Script
REM Creates standalone installers (no user deps needed)
REM =====================================================

setlocal enabledelayedexpansion

echo.
echo ========================================================
echo   CUBE LAB - WINDOWS INSTALLER BUILD
echo ========================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo         Download from: https://python.org
    pause
    exit /b 1
)

REM Create virtual environment
if not exist "venv" (
    echo [1/8] Creating virtual environment...
    python -m venv venv
)

echo [2/8] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/8] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo [4/8] Installing dependencies...
pip install -r requirements.txt --quiet

echo [5/8] Installing pypore3d from TestPyPI...
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ pypore3d
if errorlevel 1 (
    echo [WARNING] pypore3d installation had issues - continuing anyway
)

echo [6/8] Verifying imports...
python -c "import PyQt6; import pyvista; import vtk; print('Core OK')"
if errorlevel 1 (
    echo [ERROR] Core dependencies not working
    pause
    exit /b 1
)

python -c "import pypore3d; print('pypore3d OK')" 2>nul
if errorlevel 1 (
    echo [WARNING] pypore3d not available - image processing may not work
)

echo [7/8] Building executables with PyInstaller...
echo.
echo        Building CubeLab...
pyinstaller --clean --noconfirm cubelab.spec
if errorlevel 1 (
    echo [ERROR] CubeLab build failed
    pause
    exit /b 1
)

echo        Building CubeLab-UserTesting...
pyinstaller --clean --noconfirm cubelab-usertesting.spec
if errorlevel 1 (
    echo [ERROR] CubeLab-UserTesting build failed
    pause
    exit /b 1
)

echo [8/8] Creating Windows installers...

REM Check for Inno Setup
set ISCC_PATH=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if defined ISCC_PATH (
    echo        Found Inno Setup, creating installers...
    
    if not exist "installers" mkdir installers
    
    "%ISCC_PATH%" installers\cubelab-setup.iss
    if errorlevel 1 (
        echo [WARNING] CubeLab installer creation failed
    ) else (
        echo        Created: installers\CubeLab-1.0.0-Windows-Setup.exe
    )
    
    "%ISCC_PATH%" installers\cubelab-usertesting-setup.iss
    if errorlevel 1 (
        echo [WARNING] CubeLab-UserTesting installer creation failed
    ) else (
        echo        Created: installers\CubeLab-UserTesting-1.0.0-Windows-Setup.exe
    )
) else (
    echo [INFO] Inno Setup not found - creating ZIP archives instead
    echo        Download Inno Setup from: https://jrsoftware.org/isinfo.php
    
    if not exist "installers" mkdir installers
    
    powershell Compress-Archive -Path "dist\CubeLab\*" -DestinationPath "installers\CubeLab-1.0.0-Windows-Portable.zip" -Force
    powershell Compress-Archive -Path "dist\CubeLab-UserTesting\*" -DestinationPath "installers\CubeLab-UserTesting-1.0.0-Windows-Portable.zip" -Force
    
    echo        Created: installers\CubeLab-1.0.0-Windows-Portable.zip
    echo        Created: installers\CubeLab-UserTesting-1.0.0-Windows-Portable.zip
)

echo.
echo ========================================================
echo   BUILD COMPLETE!
echo ========================================================
echo.
echo   Outputs in: installers\
echo.
dir /b installers\*.exe installers\*.zip 2>nul
echo.
echo   Users can now double-click the installer to install.
echo   No dependencies, no configuration needed!
echo.
pause
