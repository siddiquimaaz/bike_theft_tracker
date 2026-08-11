# vendor/ — for installing without internet

`install.bat` normally downloads two archives (~410 MB total). Put them in this
folder and it uses them instead, never touching the network.

This is for the case where the machine you are installing on has no internet, or
metered internet — a lab PC, or a supervisor's laptop during a demo.

## What to put here

Download these on a machine that *does* have internet, then copy them into this
folder (a USB stick is fine — they are read in place, so a read-only stick works):

| Filename — must match exactly | Size | Where from |
|---|---|---|
| `postgresql-15-binaries.zip` | ~290 MB | https://get.enterprisedb.com/postgresql/postgresql-15.12-1-windows-x64-binaries.zip |
| `postgis-bundle.zip` | ~120 MB | https://download.osgeo.org/postgis/windows/pg15/postgis-bundle-pg15-3.6.2x64.zip |

**Rename them to the names in the first column.** The download links end in
different filenames (`postgis-bundle-pg15-3.6.2x64.zip`), and the installer
looks for the exact names above.

If the PostGIS link 404s, that release has rolled over — the previous build stays
reachable under `archive/`:
https://download.osgeo.org/postgis/windows/pg15/archive/postgis-bundle-pg15-3.5.3x64.zip

## How to tell it worked

`install.bat` prints this at steps 4 and 5 instead of a download progress bar:

```
[ OK ]  Using the copy shipped in vendor\ (postgresql-15-binaries.zip) - no download needed
```

## What this does not cover

Python 3.12+ and Node.js 18+. If the target machine has neither, `install.bat`
fetches them via winget, which needs internet. Check first — most machines
already have both, and then this folder is enough for a fully offline install.

If they are missing and you cannot get online there, install them by hand first:

- https://www.python.org/downloads/ — tick **Add python.exe to PATH** during setup
- https://nodejs.org — the LTS installer, default options

## Note

The archives themselves are git-ignored; only this README is tracked. They are
large, and everyone should fetch them from the official sources above rather
than from the repo.
