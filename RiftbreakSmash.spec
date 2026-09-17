# -*- mode: python ; coding: utf-8 -*-
# Build the shareable .exe:
#   pip install pygame websocket-client pyinstaller
#   pyinstaller RiftbreakSmash.spec
# Ship dist/RiftbreakSmash.exe + relay_url.txt (optional override).
# The exe reads relay_url.txt next to itself first, so a downloaded copy
# works without env vars as long as the relay service URL is correct.

a = Analysis(
    ['pc_build/main.py'],
    pathex=['pc_build'],
    binaries=[],
    datas=[
        ('pc_build/assets', 'assets'),
        # Fighter modules are code (bundled via hiddenimports), but keep any
        # future fighter data files if present.
    ],
    hiddenimports=[
        'netplay',
        'netrelay',
        'fighters',
        'fighters.cinder',
        'fighters.disc',
        'fighters.arc',
        'fighters.bulwark',
        'fighters.glass',
        'fighters.null',
        'fighters.blink',
        'fighters.tecton',
        'fighters.echo',
        'fighters.leech',
        # websocket-client is a runtime import inside netrelay.py; PyInstaller
        # cannot see it statically, so list it explicitly or online play
        # silently reports "online support is missing" in the downloaded exe.
        'websocket',
        'websocket._app',
        'websocket._core',
        'websocket._url',
        'websocket._handshake',
        'websocket._http',
        'websocket._socket',
        'websocket._ssl_compat',
        'websocket._utils',
    ],
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
    name='RiftbreakSmash',
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
