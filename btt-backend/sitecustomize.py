"""
Windows runtime bootstrap for GeoDjango native libraries.

Python imports `sitecustomize` automatically (if present on sys.path),
which makes this a reliable place to register DLL directories before
pytest-django initializes Django.

Prefer the GDAL/GEOS DLLs shipped with the rasterio wheel (same Python/ABI
as the venv). A standalone ``C:\\Program Files\\GDAL\\gdal.dll`` is often
ABI-incompatible and triggers WinError 127 when Django ctypes-loads GDAL.
"""
from __future__ import annotations

import os
from pathlib import Path


def _apply_rasterio_wheel_libs() -> bool:
    """Return True if GDAL/GEOS env paths were set from rasterio.libs."""
    try:
        import rasterio
    except ImportError:
        return False

    libs = Path(rasterio.__file__).resolve().parent.parent / "rasterio.libs"
    if not libs.is_dir():
        return False

    gdal_dlls = sorted(libs.glob("gdal-*.dll"))
    geos_dlls = sorted(libs.glob("geos_c-*.dll"))
    if not gdal_dlls or not geos_dlls:
        return False

    # Respect explicit env (e.g. CI or a known-good system GDAL).
    if not os.environ.get("GDAL_LIBRARY_PATH"):
        os.environ["GDAL_LIBRARY_PATH"] = str(gdal_dlls[0])
    if not os.environ.get("GEOS_LIBRARY_PATH"):
        os.environ["GEOS_LIBRARY_PATH"] = str(geos_dlls[0])

    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(libs))
    os.environ["PATH"] = f"{libs}{os.pathsep}{os.environ.get('PATH', '')}"

    proj_data = Path(rasterio.__file__).resolve().parent / "proj_data"
    if proj_data.is_dir():
        os.environ.setdefault("PROJ_LIB", str(proj_data))
    return True


def _legacy_dll_dirs() -> list[Path]:
    explicit_gdal = os.getenv("GDAL_LIBRARY_PATH")
    explicit_geos = os.getenv("GEOS_LIBRARY_PATH")
    candidates = [
        explicit_gdal,
        explicit_geos,
        r"C:\Program Files\GDAL\gdal.dll",
        r"C:\Program Files\GDAL\geos_c.dll",
        r"C:\OSGeo4W\bin\gdal311.dll",
        r"C:\OSGeo4W\bin\geos_c.dll",
    ]
    return [Path(p) for p in candidates if p]


if os.name == "nt":
    if not _apply_rasterio_wheel_libs():
        dll_dirs = {str(p.parent) for p in _legacy_dll_dirs() if p.exists()}
        for dll_dir in dll_dirs:
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(dll_dir)
            os.environ["PATH"] = f"{dll_dir};{os.environ.get('PATH', '')}"

        gdal_default = Path(r"C:\Program Files\GDAL\gdal.dll")
        geos_default = Path(r"C:\Program Files\GDAL\geos_c.dll")
        if gdal_default.exists():
            os.environ.setdefault("GDAL_LIBRARY_PATH", str(gdal_default))
            proj_dir = gdal_default.parent / "projlib"
            if proj_dir.exists():
                os.environ.setdefault("PROJ_LIB", str(proj_dir))
        if geos_default.exists():
            os.environ.setdefault("GEOS_LIBRARY_PATH", str(geos_default))
