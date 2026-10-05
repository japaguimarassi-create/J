# Lokivolt Phase B — Device Evidence to ROM Compatibility

## Objective

Turn a real Moto G04s discovery Vault into a device-specific compatibility record for a future Lokivolt ROM without guessing firmware details.

## Stage 1 — Physical evidence

Run the current CLI on the actual phone from Termux and preserve the generated Vault.

Required evidence:
- product/model/SKU
- product/device/codename when exposed
- board and SoC when exposed
- Android release and build fingerprint
- security patch
- bootloader state
- verified-boot state
- slot/A-B state
- dynamic partition evidence
- available storage
- Termux capability/runtime evidence

## Stage 2 — Device identity

Normalize the evidence into a stable device identity document.

Candidate fields are evidence-derived only:
- manufacturer
- model
- hardware SKU
- product
- device
- board
- platform
- architecture
- boot mode capabilities

Unknown values remain null.

## Stage 3 — Compatibility profile

Create a profile containing:
- supported Android base
- required boot image format
- required vendor boot/recovery components when observed
- AVB requirements
- partition topology
- A/B or Virtual A/B strategy when verified
- release artifact constraints
- rollback policy metadata

No flashing commands are included in the profile.

## Stage 4 — ROM source research

Look for existing open-source device trees and kernel/vendor evidence for the exact hardware identity.

A candidate external repository is never copied into the production tree without:
1. license check;
2. provenance record;
3. device identity match;
4. build reproducibility check;
5. inspection for unsafe scripts.

A UMS9230 device tree from another handset is treated as a reference only, never automatically reused.

## Stage 5 — Lokivolt ROM skeleton

Generate the minimal AOSP/Lokivolt device configuration required for a build experiment.

The first artifact is a buildability target, not a flashable release.

## Stage 6 — Release gate

A ROM becomes a Lokivolt candidate only when:
- exact device identity matches;
- all images have deterministic hashes;
- AVB configuration is internally consistent;
- rollback metadata is valid;
- build artifacts are reproducible;
- recovery plan exists;
- physical device testing has passed without destructive automation.

## Hard stop

If the live device disagrees with any public firmware report, the live device wins and the public report is marked stale/variant-specific.
