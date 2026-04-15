"""
Windows runtime bootstrap for GeoDjango native libraries.

Python imports `sitecustomize` automatically (if present on sys.path),
which makes this a reliable place to register DLL directories before
pytest-django initializes Django.
"""
from __future__ import annotations

import os
from pathlib import Path


def _candidate_paths() -> list[Path]:
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
    dll_dirs = {str(p.parent) for p in _candidate_paths() if p.exists()}
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
