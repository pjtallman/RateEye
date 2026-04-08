# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# We need to explicitly include all data folders from src/rateeye
data_files = [
    ('src/rateeye/static', 'rateeye/static'),
    ('src/rateeye/templates', 'rateeye/templates'),
    ('src/rateeye/locales', 'rateeye/locales'),
    ('src/rateeye/metadata', 'rateeye/metadata'),
    ('VERSION', '.'),
    ('INSTALL.md', '.'),
]


a = Analysis(
    ['src/rateeye/main.py'],
    pathex=['src'],
    binaries=[],
    datas=data_files,
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.lifespan.on',
        'sqlalchemy.sql.default_comparator',
        'jinja2.ext',
        'email.mime.text',
        'email.mime.multipart'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='rateeye',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=os.environ.get('PYI_ARCH'),
    codesign_identity=None,
    entitlements_file=None,
)
