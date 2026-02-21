# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/spreadsheet_qa/web/launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('src/spreadsheet_qa/resources', 'spreadsheet_qa/resources'), ('src/spreadsheet_qa/web/static', 'spreadsheet_qa/web/static')],
    hiddenimports=['spreadsheet_qa.core.rules.allowed_values', 'spreadsheet_qa.core.rules.case_rule', 'spreadsheet_qa.core.rules.content_type', 'spreadsheet_qa.core.rules.duplicates', 'spreadsheet_qa.core.rules.forbidden_chars', 'spreadsheet_qa.core.rules.hygiene', 'spreadsheet_qa.core.rules.length', 'spreadsheet_qa.core.rules.list_items', 'spreadsheet_qa.core.rules.multiline', 'spreadsheet_qa.core.rules.nakala_rules', 'spreadsheet_qa.core.rules.pseudo_missing', 'spreadsheet_qa.core.rules.rare_values', 'spreadsheet_qa.core.rules.regex_rule', 'spreadsheet_qa.core.rules.required', 'spreadsheet_qa.core.rules.similar_values', 'spreadsheet_qa.core.rules.soft_typing', 'uvicorn.loops.asyncio', 'uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.http.httptools_impl', 'uvicorn.protocols.websockets.websockets_impl', 'uvicorn.protocols.websockets.wsproto_impl', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off', 'anyio._backends._asyncio', 'h11', 'starlette.routing', 'starlette.staticfiles', 'starlette.responses', 'starlette.middleware.cors'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6', 'PyQt5', 'PyQt6', 'tkinter', '_tkinter', 'IPython', 'matplotlib', 'scipy'],
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
    name='tablerreur-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
