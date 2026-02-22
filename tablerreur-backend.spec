# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/hsmy/Dev/Tablerreur/src/spreadsheet_qa/web/launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('/Users/hsmy/Dev/Tablerreur/src/spreadsheet_qa/resources', 'spreadsheet_qa/resources'), ('/Users/hsmy/Dev/Tablerreur/src/spreadsheet_qa/web/static', 'spreadsheet_qa/web/static')],
    hiddenimports=['spreadsheet_qa.core.rules.allowed_values', 'spreadsheet_qa.core.rules.case_rule', 'spreadsheet_qa.core.rules.content_type', 'spreadsheet_qa.core.rules.duplicates', 'spreadsheet_qa.core.rules.forbidden_chars', 'spreadsheet_qa.core.rules.hygiene', 'spreadsheet_qa.core.rules.length', 'spreadsheet_qa.core.rules.list_items', 'spreadsheet_qa.core.rules.multiline', 'spreadsheet_qa.core.rules.nakala_rules', 'spreadsheet_qa.core.rules.pseudo_missing', 'spreadsheet_qa.core.rules.rare_values', 'spreadsheet_qa.core.rules.regex_rule', 'spreadsheet_qa.core.rules.required', 'spreadsheet_qa.core.rules.similar_values', 'spreadsheet_qa.core.rules.soft_typing', 'uvicorn.loops.asyncio', 'uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.http.httptools_impl', 'uvicorn.protocols.websockets.websockets_impl', 'uvicorn.protocols.websockets.wsproto_impl', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off', 'anyio._backends._asyncio', 'h11', 'h11._connection', 'h11._events', 'h11._readers', 'h11._writers', 'starlette.routing', 'starlette.staticfiles', 'starlette.responses', 'starlette.middleware.cors'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6', 'PyQt5', 'PyQt6', 'PyQt4', 'tkinter', '_tkinter', 'IPython', 'ipykernel', 'notebook', 'matplotlib', 'scipy', 'PIL', 'Pillow', 'pytest', '_pytest', 'setuptools', 'pip', 'wheel', 'pdb', 'profile', 'pstats', 'cProfile', 'curses'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='tablerreur-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=False,
    upx_exclude=[],
    name='tablerreur-backend',
)
