# Lokivolt Migration Engine v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a read-only-first Android/Termux migration engine with device discovery, immutable Vault state, transaction journaling, capability analysis, deterministic dry-run planning, recovery metadata, fixtures, and automated tests.

**Architecture:** The implementation is split into shell modules with a small shared library layer. The master engine orchestrates a finite-state machine and treats all device-changing work as a separate, authorization-gated phase; v1 never flashes or alters boot-critical partitions.

**Tech Stack:** POSIX/Bash shell, Android/Termux utilities when available, Python 3 for deterministic fixture tests, canonical JSON generated through Python stdlib, SHA-256 via `sha256sum` or Python fallback, GitHub Actions for CI.

**Spec:** `docs/superpowers/specs/2026-10-05-lokivolt-migration-engine-design.md`

## Global Constraints

- Default mode is read-only discovery.
- No bootloader bypass, AVB bypass, FRP bypass, signature forgery, or covert persistence.
- Never assume A/B, dynamic partitions, slots, or Motorola-specific partition names.
- All state-changing work is transaction-identified and authorization-gated.
- Vault data must never contain credentials.
- Rollback metadata must distinguish user-data restore from bootable firmware restore.
- JARVIS is a planner/observer and cannot override safety gates.
- v1 must run without root.
- A failed invariant must stop the state machine.
- Exit codes are 0, 10, 20, 30, 40, 50, 60, 70 as defined in the spec.

## Review Focus

- Incomplete Android properties must produce a safe partial inventory, not fabricated values.
- Corrupted Vault metadata must be detected before reuse.
- Hash mismatches must block promotion.
- Interrupted transactions must be recoverable from the journal.
- Unknown device capabilities must force a safe planning result rather than a guessed action.

---

### Task 1: Establish the repository shell project

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `.gitignore`
- Create: `migration/master/master.sh`
- Create: `migration/lib/exit_codes.sh`
- Create: `migration/lib/log.sh`
- Create: `migration/lib/locks.sh`
- Create: `migration/tests/shell/test_master.sh`

**Interfaces:**
- `master.sh --mode discover --vault PATH`
- `log_info()`, `log_warn()`, `log_error()`
- `acquire_lock()`, `release_lock()`
- Exit code constants from `exit_codes.sh`

- [ ] **Step 1: Write failing shell tests for master help, discover dispatch, and lock behavior.**
- [ ] **Step 2: Run `bash migration/tests/shell/test_master.sh` and verify failure because the engine files do not yet exist.**
- [ ] **Step 3: Implement the smallest master/utility shell layer needed for those tests.**
- [ ] **Step 4: Run `bash migration/tests/shell/test_master.sh` and verify PASS.**
- [ ] **Step 5: Commit `chore: scaffold Lokivolt migration engine`.**

### Task 2: Implement device discovery

**Files:**
- Create: `migration/modules/device.sh`
- Create: `migration/modules/preflight.sh`
- Create: `migration/lib/capabilities.sh`
- Create: `migration/tests/shell/test_device_discovery.sh`
- Create: `migration/tests/fixtures/properties/`

**Interfaces:**
- `collect_device_properties OUTPUT_DIR`
- `collect_boot_properties OUTPUT_DIR`
- `collect_runtime_architecture OUTPUT_DIR`
- `detect_capabilities OUTPUT_JSON`
- `run_preflight OUTPUT_JSON`

- [ ] **Step 1: Add fixtures for complete, partial, and missing-property Android environments and write failing tests for normalized discovery output.**
- [ ] **Step 2: Run the targeted shell tests and verify expected failures.**
- [ ] **Step 3: Implement property collection using observed `getprop` output when available and fixture injection during tests.**
- [ ] **Step 4: Verify the targeted tests pass and that missing properties stay null/unknown rather than being guessed.**
- [ ] **Step 5: Commit `feat: add device discovery and capabilities`.**

### Task 3: Implement Vault state creation and hashing

**Files:**
- Create: `migration/modules/vault.sh`
- Create: `migration/modules/verify.sh`
- Create: `migration/lib/hash.sh`
- Create: `migration/lib/json.sh`
- Create: `migration/tests/shell/test_vault.sh`
- Create: `migration/tests/fixtures/vault/`

**Interfaces:**
- `vault_init ROOT STATE_ID`
- `vault_write_state ROOT STATE_ID INPUT_DIR`
- `vault_hash_tree ROOT STATE_ID`
- `vault_verify_state ROOT STATE_ID`
- `canonical_json INPUT OUTPUT`

- [ ] **Step 1: Write failing tests covering state creation, deterministic hashes, and corruption detection.**
- [ ] **Step 2: Run the targeted tests and verify they fail for missing functions.**
- [ ] **Step 3: Implement Vault layout creation and deterministic SHA-256 manifests.**
- [ ] **Step 4: Verify creation, repeatability, and corruption detection tests pass.**
- [ ] **Step 5: Commit `feat: add immutable Vault state records`.**

### Task 4: Implement transaction journal and state machine

**Files:**
- Create: `migration/modules/transaction.sh`
- Create: `migration/lib/state.sh`
- Create: `migration/tests/shell/test_transactions.sh`

**Interfaces:**
- `tx_begin OPERATION PARENT_STATE`
- `tx_record_precondition TX_ID KEY VALUE`
- `tx_record_action TX_ID ACTION`
- `tx_record_result TX_ID RESULT`
- `tx_commit TX_ID`
- `tx_abort TX_ID CODE`
- `state_transition FROM TO`

- [ ] **Step 1: Write failing tests for transaction creation, journal durability, invalid transitions, and interrupted transactions.**
- [ ] **Step 2: Run them and verify failure.**
- [ ] **Step 3: Implement append-only journal records and the finite-state transition table.**
- [ ] **Step 4: Verify tests pass, including recovery after a simulated interruption.**
- [ ] **Step 5: Commit `feat: add transactional migration state machine`.**

### Task 5: Implement partition and AVB inspection adapters

**Files:**
- Create: `migration/modules/partitions.sh`
- Create: `migration/modules/avb.sh`
- Create: `migration/tests/shell/test_platform_inspection.sh`
- Create: `migration/tests/fixtures/platform/`

**Interfaces:**
- `inspect_block_devices OUTPUT_JSON`
- `inspect_dynamic_partitions OUTPUT_JSON`
- `inspect_slots OUTPUT_JSON`
- `inspect_verified_boot OUTPUT_JSON`

- [ ] **Step 1: Write failing fixture-driven tests for static partitions, dynamic partitions, A/B, and unknown cases.**
- [ ] **Step 2: Run and verify failure.**
- [ ] **Step 3: Implement read-only parsers that use only observed platform data.**
- [ ] **Step 4: Verify all platform inspection tests pass.**
- [ ] **Step 5: Commit `feat: add platform topology and AVB inspection`.**

### Task 6: Add device profile resolution

**Files:**
- Create: `migration/profiles/generic/profile.json`
- Create: `migration/profiles/motorola/profile.json`
- Create: `migration/modules/profile.sh`
- Create: `migration/tests/shell/test_profiles.sh`

**Interfaces:**
- `resolve_profile INVENTORY_JSON OUTPUT_JSON`
- `profile_capability PROFILE KEY`

- [ ] **Step 1: Write failing tests proving unknown devices resolve to generic rules and Motorola devices resolve to the Motorola rule set.**
- [ ] **Step 2: Run and verify failure.**
- [ ] **Step 3: Implement profile matching without hard-coding a specific handset model into execution logic.**
- [ ] **Step 4: Verify tests pass.**
- [ ] **Step 5: Commit `feat: add device profile resolution`.**

### Task 7: Implement deterministic dry-run planner

**Files:**
- Create: `migration/modules/plan.sh`
- Create: `migration/policies/safety.json`
- Create: `migration/policies/supported-actions.json`
- Create: `migration/tests/shell/test_planner.sh`

**Interfaces:**
- `build_plan INVENTORY_JSON PROFILE_JSON OUTPUT_JSON`
- `plan_requires_authorization PLAN_JSON`
- `plan_is_safe PLAN_JSON`

- [ ] **Step 1: Write failing tests for unsupported, missing-prerequisite, and discovery-only plans.**
- [ ] **Step 2: Run and verify failure.**
- [ ] **Step 3: Implement capability-driven plan generation and authorization requirements.**
- [ ] **Step 4: Verify every test fixture yields the expected plan category.**
- [ ] **Step 5: Commit `feat: add capability-driven migration planner`.**

### Task 8: Implement recovery metadata

**Files:**
- Create: `migration/modules/recovery.sh`
- Create: `migration/tests/shell/test_recovery.sh`

**Interfaces:**
- `build_recovery_plan STATE_JSON PLAN_JSON OUTPUT_JSON`
- `classify_restore_strategy STATE_JSON OUTPUT_JSON`
- `validate_recovery_plan RECOVERY_JSON`

- [ ] **Step 1: Write failing tests separating user-data recovery, Lokivolt recovery, and OEM firmware recovery.**
- [ ] **Step 2: Run and verify failure.**
- [ ] **Step 3: Implement recovery-plan generation with explicit image/firmware requirements.**
- [ ] **Step 4: Verify corrupted or incompatible recovery plans are rejected.**
- [ ] **Step 5: Commit `feat: add recovery planning`.**

### Task 9: Add orchestration for read-only Phase A

**Files:**
- Modify: `migration/master/master.sh`
- Create: `migration/modules/storage.sh`
- Create: `migration/modules/health.sh`
- Create: `migration/tests/shell/test_discovery_pipeline.sh`

**Interfaces:**
- `run_discovery_pipeline VAULT_ROOT`
- `run_discovery_pipeline` must only transition through INIT, PREFLIGHT, INVENTORY, VAULT_CREATE, CAPABILITY_ANALYSIS, PLAN, and ABORTED/WAITING_FOR_AUTHORIZATION.

- [ ] **Step 1: Write a failing end-to-end fixture test that expects a complete Vault and dry-run plan.**
- [ ] **Step 2: Run it and verify failure.**
- [ ] **Step 3: Connect the already-tested modules into the master pipeline.**
- [ ] **Step 4: Run the complete shell test suite and verify it is green.**
- [ ] **Step 5: Commit `feat: complete read-only discovery pipeline`.**

### Task 10: Add Python-based fixture and schema verification

**Files:**
- Create: `migration/tests/python/test_manifests.py`
- Create: `migration/tests/python/test_state_machine.py`
- Create: `migration/tests/python/test_hashes.py`
- Create: `migration/tests/python/run_tests.py`

- [ ] **Step 1: Write failing Python tests for JSON schemas, deterministic manifests, and valid state transitions.**
- [ ] **Step 2: Run `python3 migration/tests/python/run_tests.py` and verify failure.**
- [ ] **Step 3: Implement schema/fixture checks using only Python stdlib.**
- [ ] **Step 4: Verify the Python suite passes.**
- [ ] **Step 5: Commit `test: add deterministic fixture validation`.**

### Task 11: Add CI and operator documentation

**Files:**
- Create: `.github/workflows/test.yml`
- Create: `docs/architecture.md`
- Create: `docs/recovery.md`
- Create: `docs/operator-guide.md`
- Modify: `README.md`

- [ ] **Step 1: Write CI configuration that fails on shell or Python test failure.**
- [ ] **Step 2: Run the complete local verification commands before pushing the workflow.**
- [ ] **Step 3: Add documentation for discovery, Vault layout, recovery semantics, and safety boundaries.**
- [ ] **Step 4: Run all repository tests and inspect the Git diff for accidental destructive commands.**
- [ ] **Step 5: Commit `ci: add migration engine verification`.**

### Task 12: Final v1 verification gate

**Files:**
- Modify only when failures require fixes.

- [ ] **Step 1: Run `bash migration/tests/shell/test_master.sh`.**
- [ ] **Step 2: Run every shell test under `migration/tests/shell`.**
- [ ] **Step 3: Run `python3 migration/tests/python/run_tests.py`.**
- [ ] **Step 4: Run a repository-wide search for prohibited operations and fail if unauthorized flashing/wipe logic is present in v1.**
- [ ] **Step 5: Verify the final branch diff and GitHub Actions result.**
- [ ] **Step 6: Commit any required verification-only fixes and record the evidence.**

## Execution order

Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5 -> Task 6 -> Task 7 -> Task 8 -> Task 9 -> Task 10 -> Task 11 -> Task 12.

Each task is independently testable before the next task begins. The repository is never given a production flashing command in v1; installation integration becomes a later phase after the ROM artifacts, device unlock state, and recovery path are independently validated.


## v1.1 hardening decisions

- The engine has an explicit `--read-only` default and refuses to enter any execute phase unless a future version explicitly enables it.
- Every device observation is stored with an evidence source and a collection timestamp; unknown values are represented as `null`, never guessed.
- Vault manifests use schema versioning and deterministic key ordering so state verification remains stable across upgrades.
- A Vault state is content-addressed by a SHA-256 digest of its canonical manifest plus artifact hashes.
- A kill-switch file can force an immediate safe abort before any mutating command is considered.
- The master engine checks host/platform identity and refuses to treat a non-Android/non-Termux test host as a real device.
- Recovery plans are generated even for discovery-only runs, but contain only non-destructive restore metadata until the corresponding official artifact is present.
- The planner emits a machine-readable reason for every blocked action.
- Test fixtures model adversarial and incomplete inputs: malformed JSON, duplicate keys, whitespace variance, missing properties, corrupted hashes, stale transactions, and unsupported capability combinations.
- CI runs shell syntax checks, shell tests, Python tests, and a policy scan that fails when v1 introduces destructive flashing/wipe commands.
- The v1 implementation deliberately contains no commands that write to boot-critical device partitions. This is a scope invariant, not an omission.
