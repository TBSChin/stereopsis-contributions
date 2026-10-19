# Stereopsis contributor installer — development build

Stereopsis is Mark / FreeMark's project: https://github.com/FreeMark/eyesy-stereopsis.
TBSmike is contributing additional formations, guitar tuning, and interface enhancements.
This is an unofficial contributor installer prototype, not a separate replacement
project or a claim of upstream endorsement. Preserve upstream attribution and
license notices in any future distribution.

This is personal EYESY work. No Lamb Chops integration.

## Windows portable app

Development preview only: download the Windows ZIP, extract the entire folder,
and double-click `Stereopsis-Contributor-Installer.exe`. Python is bundled.
The launcher opens the artistic interface in your default browser. Keep its
small launcher window open while using the interface; close it to stop the app.
The live Check EYESY action is read-only. Installation/recovery are not yet
implemented, and the install button stays disabled. This is for Mark's review,
not a public production installer. Unsigned Windows builds may show warnings.

Build from source on Windows:

```
python -m pip install pyinstaller==6.22.3
powershell -ExecutionPolicy Bypass -File build-windows.ps1
```

Only the installer directory is intended for the GitHub repository. Do not
publish the surrounding personal workspace, saved device backups, or settings.

## Run the read-only compatibility check

Requires Python 3.9 or newer; no extra packages.

```
python install.py 192.168.50.4 --check
```

The default is also read-only. `--install` is deliberately blocked, even on a
recognized firmware. No force flag bypasses the checks. No network write,
restart, reboot, firmware flash, partition, or boot-file operations exist here.

The stock OS 3.1 fingerprint comes from the upstream installer. A matching
fingerprint is identification evidence, NOT clean-install validation. Stereopsis
installation metadata alone is likewise not sufficient to approve an update.

## Remaining implementation and release gates

- Capture and reconcile the current Swarm sources into reproducible components.
  Exclude personal text, user fonts, scenes, compiled caches, and removed modes.
- Resolve upstream licenses and attribution before redistributing code/assets.
- Pin an upstream Stereopsis commit and verify every downloaded file hash.
  Do not run upstream `--force` or silently pull latest main.
- Separate custom modes, optional stock-mode guitar tuning, and UI enhancements.
- Approve exact stock and existing-Stereopsis baseline fingerprints; reject
  user-modified files instead of overwriting them silently.
- Implement staged uploads, space checks, verified original backups, a durable
  transaction journal, readback verification, and conflict-aware uninstall.
- Recovery must not require the video engine. A disconnected installer cannot
  promise automatic recovery without a separately tested on-device watchdog.
- Test clean stock, existing Stereopsis, updates, disconnects, power loss,
  insufficient storage, failed engine startup, recovery, and uninstall on a spare
  SD card before enabling production writes.

No claim of zero risk or public-release readiness is made.
