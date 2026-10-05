# Lokivolt Migration Engine v1 Architecture

The engine is deliberately read-only-first. The master process coordinates small shell modules; Python is used only where deterministic JSON or hashing is easier to implement safely.

## Flow

INIT -> PREFLIGHT -> INVENTORY -> VAULT_CREATE -> CAPABILITY_ANALYSIS -> PLAN -> WAITING_FOR_AUTHORIZATION

Discovery may abort at any point. v1 has no partition-writing executor.

## Evidence

Raw `getprop` output is preserved. Normalized inventory records model, manufacturer, Android release, security patch, ABI, boot state, verified-boot state, slot, dynamic-partition and A/B evidence where observable.

Unknown data stays null.

## Vault

STATE-000 is the first baseline. STATE-001 is an enriched pre-migration state after capability analysis. State records are content-addressed through SHA-256 digests of their non-metadata artifacts.

## Transactions

Each discovery run creates a transaction ID and records begin, precondition, action, result and commit/abort events in an append-only JSONL journal.

## Safety

v1 has no fastboot flash, erase, format, dd-to-device, sgdisk, parted or wipefs operations. The policy scanner enforces that invariant.

## JARVIS boundary

Future JARVIS integration may inspect state and request operations, but the migration engine remains the authority for preconditions and authorization.
