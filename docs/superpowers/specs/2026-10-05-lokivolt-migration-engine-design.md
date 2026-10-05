# Lokivolt Migration Engine v1 — Design Specification

**Status:** Design review
**Date:** 2026-10-05
**Repository:** japaguimarassi-create/J
**Branch:** lokivolt/migration-engine-v1

## Goal

Build a modular, transaction-oriented migration platform that can inspect an Android device from a controlled Android/Termux environment, preserve a cryptographically verifiable record of its pre-migration state, prepare and validate a future Lokivolt OS installation path, and provide deterministic recovery/rollback planning without attempting to bypass Android Verified Boot or an OEM bootloader security boundary.

## Product boundary

The Migration Engine is not an exploit, bootloader unlock bypass, FRP bypass, signature forgery system, or covert persistence mechanism.

The supported path is:

1. Observe and fingerprint the device.
2. Create a durable Vault containing device state, manifests, hashes, and recovery metadata.
3. Determine the device's supported boot/update architecture.
4. Generate a device-specific migration plan.
5. Stop before any destructive operation unless the required official unlock/flash path is available.
6. When a legitimate unlocked/flashable target exists, validate Lokivolt images offline before installation.
7. Install through the device's supported flashing/recovery interface.
8. Perform first-boot health checks.
9. Promote the new state only after verification.
10. Retain a recovery path and the previous-state manifest.

## Success criteria

- No destructive command is executed implicitly by the master engine.
- The device is fingerprinted before any device-specific action is selected.
- Every mutating transaction has a transaction ID, preconditions, journal entry, verification step, and recovery state.
- Vault metadata is integrity-protected with SHA-256 hashes and canonical JSON.
- The engine never assumes A/B, dynamic partitions, a specific slot layout, or a specific Motorola partition map.
- Recovery planning distinguishes logical user-data backup from bootable firmware restoration.
- Unsupported or ambiguous hardware states fail closed.
- JARVIS can observe and plan but cannot override migration safety gates.
- The system can run in a read-only discovery mode entirely inside Termux.
- Flashing remains a separate explicitly authorized execution phase.

## Authoritative platform constraints

Android Verified Boot cryptographically verifies boot-critical and system partitions and can refuse to boot when verification fails. Rollback protection can also reject older software states. Therefore, a Lokivolt rollback is valid only when the corresponding bootable images and trust model are compatible with the device's current boot state.

Device state is either LOCKED or UNLOCKED from the Android bootloader model. LOCKED devices reject unauthorized software; changing state through the standard fastboot unlock flow requires device confirmation and wipes protected user data.

Dynamic partitions may be stored inside the physical super partition. On applicable A/B devices, target-slot metadata and partition mappings must be handled using the device's actual update architecture rather than guessed partition names.

These constraints are derived from the Android Open Source Project documentation and are treated as hard platform requirements.

## Architecture

```
migration/
  master/
    master.sh
  modules/
    preflight.sh
    device.sh
    storage.sh
    boot.sh
    avb.sh
    partitions.sh
    vault.sh
    transaction.sh
    recovery.sh
    verify.sh
    health.sh
  lib/
    log.sh
    json.sh
    hash.sh
    state.sh
    locks.sh
    capabilities.sh
  profiles/
    generic/
    motorola/
  policies/
    safety.json
    supported-actions.json
  tests/
    shell/
    fixtures/
  docs/
    architecture.md
    recovery.md
```

The architecture is intentionally split so a failure in one subsystem does not require trusting a monolithic script.

## Execution model

The engine is a finite-state machine:

```
INIT
  -> PREFLIGHT
  -> INVENTORY
  -> VAULT_CREATE
  -> CAPABILITY_ANALYSIS
  -> PLAN
  -> WAITING_FOR_AUTHORIZATION
  -> PREPARE
  -> EXECUTE
  -> VERIFY
  -> HEALTH_CHECK
  -> COMMIT

Any state after VAULT_CREATE can transition to:

  -> RECOVERY_PLAN
  -> ABORTED
```

The master script may call modules, but modules return machine-readable status and never silently continue after a failed invariant.

Required result codes:

- 0: success
- 10: unsupported device
- 20: missing prerequisite
- 30: verification failure
- 40: authorization required
- 50: safe abort
- 60: recovery required
- 70: internal engine error

## Transaction model

Every state-changing operation receives a transaction record:

```json
{
  "transaction_id": "TX-000001",
  "parent_state": "STATE-000",
  "operation": "prepare",
  "device_fingerprint_sha256": "...",
  "preconditions": [],
  "planned_actions": [],
  "started_at": "...",
  "result": "pending",
  "verification": [],
  "recovery": {
    "state_id": "STATE-000",
    "strategy": "restore-or-reflash"
  }
}
```

Journal writes happen before the mutation, then verification updates the record.

The engine must never label an operation committed merely because the underlying command returned zero. A postcondition must also be true.

## Vault model

The Vault is an immutable state record plus references to restore material.

```
LokivoltVault/
  vault.json
  states/
    STATE-000/
      state.json
      hashes.sha256
      device-properties.json
      partition-map.json
      boot-info.json
      avb-info.json
      recovery.json
  firmware/
    manifests/
    hashes/
    references/
  transactions/
  logs/
  keys/
```

Each state contains:

- exact device identifiers needed for compatibility decisions
- Android build and security-patch information
- bootloader state if exposed
- active slot if exposed
- AVB/verified-boot state if exposed
- partition inventory
- dynamic-partition metadata if exposed
- available storage
- installed application/package inventory where permission permits
- selected user-data backup manifests
- references to official firmware artifacts
- SHA-256 digests for every Vault artifact

The Vault must not store passwords, private keys, access tokens, recovery codes, or other credentials.

## Important backup limitation

Termux without elevated privileges cannot be assumed to read every protected Android partition.

Therefore:

- user-accessible files are backed up normally;
- protected-partition information is recorded when exposed through supported system interfaces;
- complete bootable firmware is represented by verified firmware artifacts or official restore packages, not by pretending an incomplete file copy is a complete image backup.

## Device abstraction

The engine uses a capability matrix instead of hard-coding the Moto G04s.

Example capability flags:

```
CAN_QUERY_PROPERTIES
CAN_QUERY_BOOT_STATE
CAN_QUERY_AVB_STATE
CAN_QUERY_SLOT
HAS_FASTBOOT_INTERFACE
HAS_RECOVERY_INTERFACE
HAS_DYNAMIC_PARTITIONS
HAS_AB_SLOTS
CAN_UNLOCK_OFFICIALLY
CAN_FLASH_BOOT
CAN_FLASH_SYSTEM
CAN_RESTORE_OFFICIAL_FIRMWARE
```

An action is legal only when its required capabilities are present.

## Generic discovery

The first implementation phase will gather evidence such as:

- ro.product.* properties
- ro.build.* properties
- ro.boot.* properties
- ABI/architecture
- Android API level
- kernel version
- security patch
- verified-boot properties
- current slot when exposed
- block-device topology when readable
- storage statistics
- Termux package/runtime availability

No hard-coded partition names are treated as facts until observed.

## Motorola handling

Motorola-specific handling lives in a profile layer.

The profile may contain rules for:

- supported official unlock flow references
- fastboot naming conventions
- firmware-package metadata
- A/B or non-A/B detection
- dynamic-partition detection
- known recovery entry mechanisms

The profile must not contain a destructive flash sequence unless all required image compatibility checks are passed.

The user's Moto G04s is therefore a target candidate, not a hard-coded assumption.

## Lokivolt image validation

A future Lokivolt release is represented by a signed release manifest:

```json
{
  "release": "lokivolt-0.1.0",
  "device_family": "...",
  "android_base": "...",
  "required_bootloader_state": "UNLOCKED",
  "images": [
    {"name":"boot","sha256":"..."},
    {"name":"vendor_boot","sha256":"..."},
    {"name":"system","sha256":"..."}
  ],
  "rollback_index_policy": {},
  "min_engine_version": 1
}
```

The engine verifies:

- device-family compatibility
- image hashes
- required image set
- expected Android base
- rollback constraints
- required flashing interface
- enough storage
- recovery plan presence

No unsigned or hash-mismatched image may enter the execute phase.

## First-boot health gate

After a migration, the health engine checks:

- device reaches the intended OS
- boot completes
- package manager responds
- storage mounts correctly
- core system services respond
- required Lokivolt components start
- JARVIS core starts independently
- networking is functional when expected
- no critical repeated boot errors are detected

A failed health gate prevents promotion to STABLE.

## JARVIS integration

JARVIS is an observer/planner with a constrained tool interface:

```
JARVIS
  -> inspect_state()
  -> explain_state()
  -> build_plan()
  -> request_safe_operation()
  -> verify_result()
  -> summarize_recovery()
```

JARVIS cannot:

- override a failed precondition
- disable verification
- invent a missing image
- bypass an authorization gate
- erase Vault state
- silently change policy files

The low-level recovery engine remains functional even if JARVIS fails.

## Security model

Default policy is fail-closed.

A state-changing operation requires:

1. known target device
2. matching transaction
3. complete preflight
4. recovery strategy
5. verified inputs
6. explicit authorization
7. postcondition verification

The engine records all commands and normalized results without storing secrets.

## Rollback model

Three levels exist:

### Level 1 — application/user state

Restore user-accessible files and application configuration from backups where supported.

### Level 2 — Lokivolt state

Restore the previous verified Lokivolt release using the supported update/recovery mechanism.

### Level 3 — OEM recovery

Reflash the exact official firmware package appropriate to the device variant and current bootloader constraints.

A rollback is rejected when the desired older image is incompatible with the device's rollback policy or trust state.

## Test strategy

Tests run without a phone using fixtures that emulate:

- LOCKED device
- UNLOCKED device
- A/B device
- non-A/B device
- dynamic partitions
- static partitions
- missing fastboot
- incomplete properties
- corrupted Vault
- hash mismatch
- insufficient storage
- interrupted transaction
- first-boot failure
- successful migration

Device-facing tests are read-only first.

Destructive flashing tests are never performed against the user's phone automatically.

## Repository strategy

The existing repository `japaguimarassi-create/J` is used as the clean base because its current main branch contains only a minimal README. No unrelated Roblox code is imported into the migration engine.

The repository is intentionally kept separate from `Cursed-Collision`; that project remains a Roblox codebase and is not repurposed as the Android/ROM source tree.

## Phase boundaries

### Phase A — discovery and Vault

Read-only Termux engine, capability detection, Vault creation, hashes, journal, fixtures and tests.

### Phase B — planning

Device profiles, compatibility matrix, Lokivolt release manifests, dry-run plan generation and recovery planning.

### Phase C — ROM preparation

AOSP/Lokivolt build integration, image packaging, signing and offline validation.

### Phase D — controlled installation

Fastboot/recovery integration after legitimate bootloader authorization, with transactional checks.

### Phase E — Lokivolt runtime

Lokivolt System UI, launcher, services and JARVIS integration.

## Non-goals

- Exploiting vulnerabilities to bypass bootloader locking.
- Bypassing Factory Reset Protection.
- Forging OEM signatures.
- Disabling Android security mechanisms through an exploit.
- Concealing persistent privileged access.
- Automatically wiping the device without an explicit authorization gate.

## Acceptance bar

The engine is considered ready for the next phase only when the current phase has fresh verification evidence, all mandatory tests pass, and every destructive transition has a tested recovery path.
