from PyInstaller.utils.hooks import collect_submodules
import os
hiddenimports = collect_submodules('PyQt5')

# Read version number from file (choose one method)
version_file = 'version.txt'
if os.path.exists(version_file):
    with open(version_file) as f:
        app_version = f.read().strip()
else:
    app_version = "1.2.0"  # Default 

a = Analysis(
    ['main.py', 'database.py', 'dict_help.py', 'duplicates.py','import_export.py','pdf_export_tool.py','settings.py','undo_commands.py'],
    pathex=[],
    binaries=[],
    datas=[
    ('icons/*.svg', 'icons'),
    ('icons/*.png', 'icons'),
    ('themes/*.qss', 'themes'),
    ('translations/*.qm', 'translations'),
    ('dict_help.html', '.')
    ],
    hiddenimports=['PyQt5', 'PyQt5.QtWidgets', 'PyQt5.QtGui', 'PyQt5.QtCore'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'UriDictmaker-{app_version}',
    icon='icons/app_icon.png',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
