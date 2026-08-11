# vendor/ — for installing without internet

`install.bat` normally downloads two archives (~410 MB total). Put them in this
folder and it uses them instead, never touching the network.

This is for the case where the machine you are installing on has no internet, or
metered internet — a lab PC, or a supervisor's laptop during a demo.

## What to put here

Download these on a machine that *does* have internet, then copy them into this
folder (a USB stick is fine — they are read in place, so a read-only stick works).

Only the ones you need: Python and Node are skipped when the target machine
already has them. The two database archives are always needed on a first install.

| Filename — must match exactly | Size | Where from |
|---|---|---|
| `postgresql-15-binaries.zip` | ~290 MB | https://get.enterprisedb.com/postgresql/postgresql-15.12-1-windows-x64-binaries.zip |
| `postgis-bundle.zip` | ~120 MB | https://download.osgeo.org/postgis/windows/pg15/postgis-bundle-pg15-3.6.2x64.zip |
| `python-3.13.9-amd64.exe` | ~28 MB | https://www.python.org/ftp/python/3.13.9/python-3.13.9-amd64.exe |
| `node-v24.19.0-win-x64.zip` | ~36 MB | https://nodejs.org/dist/v24.19.0/node-v24.19.0-win-x64.zip |

All four together are about **475 MB**.

**Rename to the names in the first column.** Two of the links end in a different
filename (`postgis-bundle-pg15-3.6.2x64.zip`), and the installer looks for the
exact names above.

If the PostGIS link 404s, that release has rolled over — the previous build stays
reachable under `archive/`:
https://download.osgeo.org/postgis/windows/pg15/archive/postgis-bundle-pg15-3.5.3x64.zip

## How to tell it worked

`install.bat` prints this instead of a download progress bar:

```
[ OK ]  Using the copy shipped in vendor\ (postgresql-15-binaries.zip) - no download needed
```

## How Python and Node get installed

Neither needs administrator rights, and neither depends on winget:

- **Python** — the official installer, run silently with `InstallAllUsers=0`, so
  it goes into your user profile only. Skipped entirely if the machine already
  has Python 3.12+.
- **Node** — the portable zip, unpacked into `.runtime\node` inside this repo.
  Nothing is installed on the machine, the system PATH is untouched, and any
  Node already there is left alone. It disappears when you delete the repo
  folder. Also used when the machine's Node is older than 18, which vite needs.

## Note

The archives themselves are git-ignored; only this README is tracked. They are
large, and everyone should fetch them from the official sources above rather
than from the repo.
