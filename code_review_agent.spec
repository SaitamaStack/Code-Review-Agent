# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Local Code Review & Fix Agent

This spec file configures the build process for creating a standalone
executable of the Code Review Agent application.

Build commands:
    Windows: pyinstaller code_review_agent.spec
    Linux/Mac: pyinstaller code_review_agent.spec

The resulting executable will be in the dist/ folder.
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Application metadata
APP_NAME = "CodeReviewAgent"
APP_VERSION = "1.0.0"

# Collect all submodules for packages that PyInstaller often misses
# LangGraph and LangChain have complex import structures

hidden_imports = [
    # LangGraph imports
    'langgraph',
    'langgraph.graph',
    'langgraph.graph.state',
    'langgraph.prebuilt',
    'langgraph.checkpoint',
    'langgraph.channels',
    
    # LangChain imports
    'langchain',
    'langchain.schema',
    'langchain.schema.messages',
    'langchain_core',
    'langchain_core.messages',
    'langchain_core.language_models',
    'langchain_core.language_models.chat_models',
    'langchain_core.output_parsers',
    'langchain_core.prompts',
    'langchain_core.runnables',
    'langchain_core.runnables.base',
    'langchain_core.runnables.config',
    
    # LangChain Ollama
    'langchain_ollama',
    'langchain_ollama.chat_models',
    
    # Pydantic (required for structured outputs)
    'pydantic',
    'pydantic.fields',
    'pydantic.main',
    'pydantic_core',
    
    # CustomTkinter and Tkinter
    'customtkinter',
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.ttk',
    
    # Standard library modules that might be missed
    'json',
    'logging',
    're',
    'difflib',
    'threading',
    'subprocess',
    'tempfile',
    'ast',
    'dataclasses',
    'datetime',
    'typing',
    'urllib.request',
    'urllib.error',
    'webbrowser',
    
    # HTTP and networking (used by langchain_ollama)
    'httpx',
    'httpcore',
    'anyio',
    'sniffio',
    'certifi',
    'h11',
    
    # Other potential dependencies
    'packaging',
    'packaging.version',
    'tenacity',
    
    # Local project modules
    'agents',
    'agents.graph',
    'agents.prompts',
    'models',
    'models.schemas',
    'tools',
    'tools.executor',
    'tools.linter',
    'utils',
    'utils.helpers',
    'config',
]

# Collect all submodules for complex packages
hidden_imports += collect_submodules('langchain_core')
hidden_imports += collect_submodules('langgraph')
hidden_imports += collect_submodules('pydantic')
hidden_imports += collect_submodules('pydantic_core')
hidden_imports += collect_submodules('customtkinter')

# Collect data files (themes, assets, etc.)
datas = []
datas += collect_data_files('customtkinter')

# Add local packages - these must be included for the app to work
datas += [
    ('agents', 'agents'),
    ('models', 'models'),
    ('tools', 'tools'),
    ('utils', 'utils'),
    ('config.py', '.'),
]

# Analysis configuration
a = Analysis(
    ['app.py'],  # Main script
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'torch',
        'tensorflow',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Create the PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create the executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression if available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Hide console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Icon configuration - uncomment and set path when icon is available
    # icon='assets/app.ico',  # Windows icon (.ico)
    # icon='assets/app.icns',  # macOS icon (.icns)
)

# Note about icons:
# -----------------
# To add an application icon:
# 1. Create or obtain an icon file:
#    - Windows: app.ico (256x256 recommended, multi-resolution)
#    - macOS: app.icns (use iconutil to create from iconset)
#    - Linux: app.png (usually 256x256 or 512x512)
#
# 2. Place the icon in an 'assets' folder at the project root
#
# 3. Uncomment the appropriate icon line above:
#    - Windows: icon='assets/app.ico'
#    - macOS: icon='assets/app.icns'
#
# 4. Rebuild the executable
#
# For a professional code review tool, consider:
# - A magnifying glass with code brackets
# - A document with checkmark/gear
# - Abstract code symbols with review indicators
