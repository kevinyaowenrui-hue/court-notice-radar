# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# 项目根路径
project_dir = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(project_dir, 'frontend', 'dist'), os.path.join('frontend', 'dist')),
    (os.path.join(project_dir, 'data', 'court_notices.db'), 'data'),
    (os.path.join(project_dir, 'assets'), 'assets'),
]

hiddenimports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'httptools',
    'httptools.parser',
    'h11',
    'anyio',
    'anyio._backends',
    'anyio._backends._asyncio',
    'starlette',
    'starlette.routing',
    'starlette.middleware',
    'starlette.middleware.cors',
    'starlette.staticfiles',
    'starlette.responses',
    'fastapi',
    'fastapi.staticfiles',
    'fastapi.responses',
    'pydantic',
    'sqlalchemy',
    'sqlalchemy.orm',
    'sqlalchemy.dialects.sqlite',
    'apscheduler',
    'apscheduler.schedulers.background',
    'apscheduler.triggers.interval',
    'apscheduler.executors.pool',
    'playwright',
    'playwright.async_api',
    'webview',
    'webview.platforms.winforms',
    'clr_loader',
    'pythonnet',
    'backend',
    'backend.app',
    'backend.models',
    'backend.database',
    'backend.utils',
    'backend.config',
    'backend.mock_data',
    'backend.clean_and_migrate_db',
    'backend.engine',
    'backend.engine.scheduler',
    'backend.engine.rule_matcher',
    'backend.engine.webhook',
    'backend.crawlers',
    'backend.crawlers.ali_crawler',
    'backend.crawlers.jd_crawler',
    'backend.crawlers.rmfyb_crawler',
    'backend.crawlers.caa_crawler',
    'backend.crawlers.ggzy_crawler',
    'backend.crawlers.local_paper_crawler',
    'backend.crawlers.seed_53bk',
    'backend.crawlers.rmfysszc_crawler'
]

a = Analysis(
    ['desktop_app.py'],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter', 'scipy', 'numpy.testing', 'IPython'],
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
    name='法拍雷达',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 桌面应用原生独立窗口，无黑色控制台
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_dir, 'assets', 'radar_icon.ico')
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='法拍雷达'
)
