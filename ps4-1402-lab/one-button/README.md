# JBherePS4

Single-button offline host for PS4 browser diagnostics and firmware evidence.

## What the button does

1. Caches the host's static files using Service Worker/Cache Storage where available.
2. Declares an HTML Application Cache fallback for legacy browsers that still support it.
3. On the next browser launch, automatically resumes a small, non-invasive browser capability report.
4. Reads the local evidence file and stops at the firmware compatibility gate.
5. Stores the report locally in browser storage.

## What it does not do

This is not a jailbreak payload. It does not trigger WebKit memory corruption, spray/reclaim objects, invoke syscalls, read/write privileged memory, patch kernel text, run ELF/BIN payloads, install PKGs, downgrade firmware, hide activity from Sony, or load GoldHEN.

The requested target is PS4 14.02. The public Afterglow project lists firmwares through 14.00 and does not list 14.02. The project therefore refuses to guess 14.02 offsets or execute a 14.00 chain against a different kernel build.

## Payload architecture reviewed

The public Afterglow technical documentation separates a browser-side userland primitive from the kernel stage. The kernel stage depends on a firmware-specific layout and patch set. A payload loader then maps and starts a payload, and GoldHEN expects the appropriate kernel patches to have been applied first.

This is why an exploit cannot be created by guessing offsets: a valid target build, a reproducible vulnerability, verified primitives, exact offsets and hardware validation are required. A browser API check does not provide kernel access.

## GoldHEN status

The official GoldHEN releases repository was checked on 2026-11-13. The latest listed public beta was 2.4b18 (2024-10-28), whose supported-firmware list ends at 11.00. The latest stable release listed was 2.3. Neither release lists 14.02. The site does not download or load either binary.

Sources:
- https://github.com/well0nez/afterglow-web
- https://github.com/well0nez/afterglow-web/blob/main/TECHNICAL.md
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://consolemods.org/wiki/PS4:Exploit_Chart
- https://github.com/GoldHEN/GoldHEN/releases

## Deployment

Repository: japaguimarassi-create/J
Root directory: ps4-1402-lab/one-button
Framework: Other
Build/install command: none
Output directory: .

## Offline notes

The first visit must be through HTTPS to install Service Worker/Cache Storage. The HTML Application Cache fallback is included because the public Afterglow host uses that legacy mechanism for the PS4 browser. Support depends on the exact browser build; the page reports capabilities rather than claiming offline support without confirmation.

The app sends no telemetry. Reports are stored only in local browser storage.
