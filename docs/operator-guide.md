# Operator Guide

## Discovery

Run the master entrypoint in discovery mode and point it at a Vault directory.

Discovery is read-only with respect to device partitions.

## Fixture mode

Set `LOKIVOLT_GETPROP_FILE` to a property fixture for deterministic tests. The engine stores the raw fixture as evidence and does not infer missing fields.

## Kill switch

A file passed through `--kill-switch` containing exactly `enabled=true` causes safe abort before discovery.

## Mutation

v1 mutation is intentionally refused with the authorization-required exit code. No partition flashing is part of this release.

## Exit codes

0 success
10 unsupported
20 missing prerequisite
30 verification failure
40 authorization required
50 safe abort
60 recovery required
70 internal engine error
