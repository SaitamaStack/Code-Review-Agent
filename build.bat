@echo off
REM ============================================================================
REM Build script for Code Review Agent (Windows)
REM 
REM This script builds a standalone .exe using PyInstaller
REM 
REM Prerequisites:
REM   - Python 3.8+ installed
REM   - Virtual environment activated (recommended)
REM   - pip install pyinstaller
REM 
REM Usage:
REM   build.bat
REM ============================================================================

echo.
echo ============================================
echo  Code Review Agent - Windows Build Script
echo ============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to your PATH
    pause
    exit /b 1
)

echo [1/5] Checking Python version...
python --version

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo.
    echo [2/5] Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller
        pause
        exit /b 1
    )
) else (
    echo [2/5] PyInstaller is already installed
)

REM Install project dependencies
echo.
echo [3/5] Installing project dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

REM Clean previous builds
echo.
echo [4/5] Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Run PyInstaller
echo.
echo [5/5] Building executable with PyInstaller...
echo This may take a few minutes...
echo.
pyinstaller code_review_agent.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ============================================
    echo [ERROR] Build failed!
    echo ============================================
    echo.
    echo Common issues:
    echo   - Missing dependencies: pip install -r requirements.txt
    echo   - Antivirus blocking: Add exclusion for build folder
    echo   - Permission denied: Run as Administrator
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build Complete!
echo ============================================
echo.
echo Executable location:
echo   dist\CodeReviewAgent.exe
echo.
echo To run the application:
echo   1. Make sure Ollama is installed and running
echo   2. Pull required model: ollama pull qwen3:14b
echo   3. Double-click CodeReviewAgent.exe
echo.
echo ============================================

REM Open the dist folder
explorer dist

pause
