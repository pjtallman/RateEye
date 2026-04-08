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
    ('INSTALL_GUIDE.txt', '.'),
    ('COPYRIGHT.txt', '.'),
]

a = Analysis(
    ['launcher.py'],
    pathex=['src'],
    binaries=[],
    datas=data_files,
    hiddenimports=[
        # Web Server & Framework
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'uvicorn.lifespan.auto',
        'fastapi',
        'starlette',
        'starlette.middleware.sessions',
        'anyio.backends._asyncio',
        'multipart',
        'itsdangerous',
        'httpx',
        
        # Authentication & Security
        'authlib',
        'authlib.integrations',
        'authlib.integrations.starlette_client',
        'passlib',
        'passlib.handlers.bcrypt',
        'jose',
        'jose.backends',
        'jose.backends.cryptography_backend',
        'cryptography',
        'bcrypt',
        
        # Database
        'sqlalchemy',
        'sqlalchemy.sql.default_comparator',
        'sqlalchemy.dialects.sqlite',
        
        # Data & Finance
        'pandas',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.base',
        'numpy',
        'pytz',
        'yfinance',
        'curl_cffi',
        
        # Internal App Modules
        'rateeye.core.paths',
        'rateeye.core.utils',
        'rateeye.core.logging_config',
        'rateeye.database',
        'rateeye.i18n',
        'rateeye.auth.service',
        'rateeye.auth.dependencies',
        'rateeye.security.service',
        'rateeye.data_mgmt.export_import',
        'rateeye.routers.public',
        'rateeye.routers.settings',
        'rateeye.routers.admin',
        
        # System Utilities
        'webbrowser',
        'threading',
        'multiprocessing',
        'pkg_resources.py2_warn',
        'importlib_metadata'
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
    [],
    exclude_binaries=True,
    name='RateEye',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=os.environ.get('PYI_ARCH'),
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RateEye',
)

# Standard macOS Bundle Configuration
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='RateEye.app',
        icon=None,
        bundle_identifier='com.rateeye.app',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
            'NSAppleEventsUsageDescription': 'RateEye needs permission to show startup alerts and open your browser.',
            'CFBundleShortVersionString': '1.0.6',
            'CFBundleVersion': '1.0.6',
            'NSLocalNetworkUsageDescription': 'RateEye runs a local web server to provide the dashboard.',
        },
    )
