# Lokivolt OS / Migration Engine

Lokivolt is an Android-based operating system architecture built around the Linux kernel, with Android framework/runtime components and a dedicated Lokivolt fusion layer for native services, update orchestration, recovery planning and JARVIS.

## Acceptance model

Lokivolt separates acceptance of a plan from permission to execute it.

ACCEPTED_100 means the observed state and proposed architecture are completely accepted by the planner.

ACCEPTED_GATED means a capability is understood and accepted, but Android or the device currently gates its execution.

ACCEPTED_LIMITED means a known limitation is accepted as explicit state instead of being treated as an undefined failure.

A locked bootloader is therefore not a planning rejection. It remains an execution boundary.

## Android + Linux fusion

Android already uses a Linux-based kernel architecture. Lokivolt extends that foundation with its own native fusion services while retaining Android compatibility, Binder/AIDL service boundaries, SELinux policy and Verified Boot.

The intended stack is:

1. Linux LTS / Android Common Kernel / GKI
2. Vendor kernel modules and hardware HALs
3. Android native libraries and daemons
4. Android Framework and system services
5. Lokivolt Fusion Services
6. Lokivolt System UI and Setup
7. JARVIS policy-constrained orchestration

The architecture definition is stored in os/config/fusion-architecture.json and documented in os/docs/lokivolt-fusion.md.

## Current acceptance result

The current engine can report:

Plan: ACCEPTED 100%
Plan score: 100%
Execution: GATED
Execution gate: BOOTLOADER_LOCKED

This is intentional. The planner accepts the work completely, while Android still controls whether a destructive operation may execute.

## Safety

The migration engine remains read-only in v1.

It never:
- bypasses a bootloader;
- bypasses FRP;
- forges signatures;
- disables AVB;
- erases or writes boot-critical partitions.

Android Verified Boot and rollback protection are treated as platform invariants. citeturn432857search10

## Update architecture

Lokivolt is designed to use A/B or Virtual A/B update semantics and dynamic partitions when the target device exposes them. The Moto G04s discovery exposed A/B and dynamic partitions, so those facts are recorded as device evidence rather than guessed partition layout.

## Build targets

- cf: AOSP Cuttlefish ARM64 phone
- generic-arm64: AOSP generic ARM64
- moto-g04s: intentionally gated until exact device kernel, vendor, AVB and partition sources are validated

A generic AOSP build is not considered a valid Moto G04s ROM.

## Termux

Install and start:

lokivolt start

The current flow creates a Vault, records capabilities, generates a recovery plan and produces the 100% accepted dry-run plan without modifying device partitions.
