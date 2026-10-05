# Termux Quick Start

The supported entry point for the current engine is the read-only discovery pipeline.

## Install

The bootstrap script downloads the selected Git branch archive and places only the migration engine, CLI and documentation under the user's Termux home directory.

## Run

Use the CLI with:

- `bash ~/.local/share/lokivolt/bin/lokivolt version`
- `bash ~/.local/share/lokivolt/bin/lokivolt discover`

For deterministic testing, set `LOKIVOLT_GETPROP_FILE` to a fixture file.

## What it changes

The bootstrap only writes under `~/.local/share/lokivolt`. The migration engine writes its Vault under the path supplied with `--vault`.

The current engine does not flash partitions, unlock the bootloader, erase userdata, or change AVB state.

## Real-device next step

Run discovery on the physical phone and preserve the generated Vault. The actual device evidence determines whether the Moto G04s is A/B, whether dynamic partitions are present, what AVB exposes, and what bootloader capabilities are available.

Do not infer those properties from an online firmware report. Independent public reports for Moto G04/Moto G04s variants are inconsistent about exact device identifiers, so the engine intentionally trusts live evidence over model guesses.
