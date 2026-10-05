# Lokivolt Migration Engine

A read-only-first Android migration, verification and recovery platform intended to become the foundation for the future Lokivolt OS and JARVIS integration.

## Current release

**v1 — Discovery / Vault / Planning**

This release:

- fingerprints the Android device using observed system properties;
- records raw evidence and normalized inventory;
- detects capabilities without assuming a particular partition layout;
- creates immutable baseline and enriched Vault states;
- journals the discovery transaction;
- produces a deterministic dry-run migration plan;
- produces a recovery plan;
- validates future Lokivolt release manifests;
- runs a kill switch before discovery;
- refuses device mutation in v1.

No v1 command writes boot-critical Android partitions.

## Run

From an Android/Termux shell:

```bash
bash migration/master/master.sh --mode discover --vault "$HOME/LokivoltVault"
```

For deterministic fixture testing:

```bash
export LOKIVOLT_GETPROP_FILE=/path/to/getprop.fixture
bash migration/master/master.sh --mode discover --vault ./LokivoltVault
```

The engine preserves the raw properties and uses null for unavailable values.

## Safety model

The engine treats discovery and migration as a finite-state machine and records transaction events.

The v1 policy intentionally refuses:

- bootloader bypass;
- FRP bypass;
- signature forgery;
- partition flashing;
- partition erase/format;
- raw block-device overwrite.

A kill switch file containing `enabled=true` aborts the run before discovery.

## Verification

Run the full local gate:

```bash
bash migration/tests/selfcheck.sh
```

Or run the Python and shell suites independently:

```bash
python3 migration/tests/python/run_tests.py
bash migration/tests/shell/test_master.sh
```

## Project structure

```text
migration/
  master/
  modules/
  lib/
  profiles/
  policies/
  tests/
```

## Repository strategy

This repository, `japaguimarassi-create/J`, was selected as the clean base for Lokivolt because its main branch contained only a minimal README. The existing `Cursed-Collision` repository remains independent Roblox code and is not mixed into the Android/ROM codebase.

## Roadmap

Phase A: discovery, Vault, journal, capability analysis and dry-run planning.

Phase B: device profiles, signed Lokivolt release manifests and compatibility tooling.

Phase C: AOSP/Lokivolt ROM build and image verification.

Phase D: controlled flashing through the device's supported, explicitly authorized bootloader/recovery path.

Phase E: Lokivolt runtime services, System UI, launcher and JARVIS integration.


## Termux bridge

The repository includes:
- `bin/lokivolt` for discovery/version commands;
- `termux/bootstrap.sh` for installing the current branch into the user's Termux home directory;
- `docs/termux.md` for the Android-side workflow.

The first physical-device action is discovery. It creates evidence and a Vault; it does not replace Android or modify boot-critical partitions.

## Moto G04s

The device research dossier is at `docs/device-research/moto-g04s.md`. Public firmware sources currently point to Brazilian XT2421-6/Lion variants, while independent reports show variant differences. The engine deliberately requires live device evidence before a ROM profile is selected.


## Final Termux command

The complete first-run command is:

```bash
curl -fsSL 'https://raw.githubusercontent.com/japaguimarassi-create/J/lokivolt/migration-engine-v1/termux/bootstrap.sh' -o "$PREFIX/tmp/lokivolt-bootstrap.sh" && bash "$PREFIX/tmp/lokivolt-bootstrap.sh" && lokivolt doctor
```

This installs the current engine and immediately performs read-only discovery.

To start the control plane later:

```bash
lokivolt start
```

The OS source is under os/. The generic AOSP build recipe is under os/build/. The Moto g04s hardware target remains gated until device-specific evidence is complete.
