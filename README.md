# Stereopsis contributions by TBSmike

Additional Swarm formations, guitar-reactive tuning, and browser-control changes
for **Stereopsis, created by Mark / FreeMark**.

Original project: https://github.com/FreeMark/eyesy-stereopsis

This repository is a contributor source handoff for Mark to review and integrate.
It contains source contributions, not a firmware image or official upstream release.
Download this repository using **Code → Download ZIP**.

## What is included

- `Modes/`: 145 curated mode source folders: 20 Swarms, 94 Critter & Guitari
  modes, 28 community modes, and 3 additional Stereopsis/derived modes.
- `THIRD-PARTY-NOTICES.md`: original authors, source links and license mapping.
- `licenses/` and per-mode `ATTRIBUTION.md`: applicable third-party terms.
- `ORIGINAL-DOWNLOADS.md`: links only for eight modes with unresolved permissions.
- `engine-changes/`: modified Stereopsis `preview.py`, `eyesy.py`, and the detached
  restart helper, for upstream review rather than blind replacement.
- `snapshot.json`: source basis and validation limitations.
- `SHA256SUMS`: file integrity hashes.

Highlights: graph-traveling waves through Tesseract and Icosa Cages; stronger
24 Cell edge deformation; Orb spectrum spread around the sphere; reduced/removed
hard pulses in Tunnel, Ribbon, Orb, and Nebula; fixed-black backgrounds and K5
Audio Strength where K5 formerly controlled background/scatter; Persist support;
mode-order UI; knob labels; and independent optional second/third text lines.
Morph, nesting, and arm-twist controls remain on their applicable formations.
Soundfield Galaxy and Soundfield Splats 2 use fixed black and K5 Audio Strength (0x / 1x / 2x),
applied after automatic level normalization; manual Trigger remains independent.

## Using the files

These changes were developed against Stereopsis 0.11 on EYESY OS 3.1. They are
not promised compatible with other releases. Back up the original folders first.

For Mark: merge the native renderer changes as one shared implementation and
review the browser/engine changes against your current branch. The 3D modes use
4096 particles and the same native ABI/style IDs; **do not mix old/new kernels**.
Round and triangle modes intentionally have different particle rasterizers.

For experienced users already running a compatible Stereopsis: the `Modes/`
folders are laid out for uploading via EYESY's Wi-Fi web editor. Keep each folder
complete. Compilation happens on EYESY; `.so` files are deliberately not included.
The transition helper lives in `Swarm - Terrain Back to Front`, so keep that folder
available. Existing numerically named upstream folders are not automatically
renamed or removed by this source download. Do not overwrite your own modes.

**Do not blindly copy `engine-changes/` over another Stereopsis version.** These
are reviewable full-source modifications, not a version-aware installation patch.
Restart controls use a detached `systemd-run` task; device reboot remains less
tested than video restart. No personal mode-order file is included. Engine
integration is needed to enable custom saved ordering and the new text controls.

## Font and personal content

`Swarm - Text` includes `Futura_Heavy_Oblique.otf`, supplied by TBSmike, who
explicitly confirmed permission to redistribute it. The font is not relicensed
under the source-code MIT license. See `FONT-NOTICE.md`.

Personal saved texts, scenes, network addresses, mode-order preferences, settings,
compiled binaries, native crash guards, and device backups are excluded.

## Snapshot limitations

The curated source was exported from the live device on 2026-10-19. Python
syntax and file hashes were checked; this exact consolidated download still
needs a clean-device integration test. This is not a complete device backup.
Community modes may include TBSmike guitar-response tuning; they are not claimed
to be byte-identical to their authors' current downloads. The optional VCR font
is omitted; that mode retains its existing default-font fallback.
No one-click installation or guaranteed recovery is claimed.

Matrix Rain, both Swarm Kaleidoscope variants, Spiral Alley, Spirograph and
Nested Ellipses - Outlines are intentionally excluded at TBSmike's request.
Kaleid-O-Tron and Nested Ellipses - Filled are retained.

## Attribution

Stereopsis and the original Swarm implementation: **Mark / FreeMark**.
Additional formations, tuning, and interface contributions: **TBSmike**.
Original source comments and notices are preserved. This is independent personal
work, not an official TBS product or a Critter & Guitari release.

Critter & Guitari and community authors retain ownership of their modes.
This collection is **not all MIT licensed**: retain the separate licenses,
credits, and original source notices when sharing it. See THIRD-PARTY-NOTICES.md.
