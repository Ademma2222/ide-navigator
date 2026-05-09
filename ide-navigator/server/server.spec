# PyInstaller spec for IDE Navigator LSP server
# Builds a standalone binary that bundles:
#   - pygls + lsprotocol
#   - tree_sitter + all language grammars (.pyd + queries/)
#   - local languages/ package
#
# Build: pyinstaller server.spec --clean --noconfirm
# Output: dist/ide-navigator-server/ide-navigator-server(.exe)

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# Collect tree-sitter grammar packages (each has a _binding.pyd/.so and queries/)
_grammar_packages = [
    "tree_sitter",
    "tree_sitter_python",
    "tree_sitter_java",
    "tree_sitter_cpp",
    "tree_sitter_go",
    "tree_sitter_javascript",
    "tree_sitter_typescript",
]
for pkg in _grammar_packages:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        # Grammar not installed on this platform — skip
        pass

# pygls + lsprotocol must be fully collected (pygls uses dynamic feature registration)
for pkg in ("pygls", "lsprotocol"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Our own languages/ package — include every submodule explicitly so PyInstaller
# doesn't miss anything referenced only via LANGUAGE_MAP.
hiddenimports += collect_submodules("languages")


a = Analysis(
    ["server.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "PIL", "pytest"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ide-navigator-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
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
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ide-navigator-server",
)
