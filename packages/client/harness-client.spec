# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Harness Client.

Build command:
    pyinstaller harness-client.spec

Output:
    dist/HarnessClient.exe
"""

import sys
from pathlib import Path

# Get project root
project_root = Path(SPECPATH).parent.parent
sdk_src = project_root / "packages" / "sdk" / "src"

a = Analysis(
    ['src/harness_client/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        # Include SDK source if not installed as package
        (str(sdk_src), 'harness'),
    ],
    hiddenimports=[
        # Core dependencies
        'qasync',
        'asyncio',
        # PyQt6 SVG support
        'PyQt6.QtSvg',
        # SDK modules
        'harness',
        'harness.sdk',
        'harness.core',
        'harness.llm',
        'harness.tools',
        'harness.memory',
        'harness.skills',
        'harness.mcp',
        'harness.security',
        'harness.testing',
        # LLM providers
        'anthropic',
        'openai',
        # Utilities
        'pydantic',
        'aiohttp',
        'tiktoken',
        'jsonschema',
        'yaml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unused modules to reduce size
        'tkinter',
        'unittest',
        'pydoc',
        'doctest',
        'distutils',
        'setuptools',
        'pip',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HarnessClient',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Note: PyInstaller requires .ico format for Windows EXE icon.
    # SVG icons are used inside the app via QIcon, not for the EXE itself.
    # Use generate_ico.py to create app.ico from icon.svg
    icon='resources/icons/app.ico',
)
