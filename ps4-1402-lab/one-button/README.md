# JBherePS4 v1.6.0

PS4 14.02 safe browser diagnostics, experimental claim audit, temporary-session reporting, and private report storage.

## Current conclusion

This project does not contain a verified jailbreak for PS4 14.02. The public experimental repository audited below claims partial kernel access, but its own test notes report a kernel panic when launching games and HEN/GoldHEN threads dying during initialization. That is not a usable or independently reproduced HEN.

## What v1.6.0 does

- Performs a browser capability inventory without invoking exploits or privileged interfaces.
- Uses small, deterministic tests for typed arrays, empty WebAssembly module validation, local storage, and browser API availability.
- Labels firmware parsed from User-Agent as a non-authoritative hint.
- Prepares a static cache where the browser supports it.
- Saves a local JSON report and offers download/copy controls.
- Tests private report storage before attempting an upload.
- Preserves a local report when offline or when the backend is unavailable.
- Keeps the session non-destructive and does not persist changes to the PS4 system.

## What it does not do

- It does not activate HEN or jailbreak the console.
- It does not execute memory corruption, kernel syscalls, kernel read/write, or exploit chains.
- It does not modify firmware, install payloads, load ELF/BIN files, or inject GoldHEN.
- It does not establish whether a CVE exists merely from browser API support.
- It does not treat browser User-Agent strings as proof of firmware version.

## Experimental 14.02 claim audited on 2026-11-13

Repository: https://github.com/Jfkkfjzkz/A

The repository's CHAIN.txt snapshot dated 2026-11-11 claims:
- uid 0
- kernel read/write
- 15/15 patch stubs applied
- Debug Settings patch applied

The same file records:
- launching a game on the patched kernel causes a kernel panic
- HEN/GoldHEN payload threads die during initialization
- installer init #1 reportedly survives, while init #2 is untested
- a working game-launching HEN is not demonstrated

The source does not independently validate the full chain:
- README.md still documents the Afterglow exploit for firmware 14.00.
- afterglow-g.js identifies its base as firmware 14.00 and says the code has never executed in that host.
- ps4_offsets.js creates the 14.02 table by copying PS4["14.00"], while its status text says WebKit is assumed identical to 13.52 and kernel offsets are from 14.00 plus shiftfit.

Assessment: UNVERIFIED_PARTIAL_KERNEL_CHAIN_NOT_A_USABLE_JAILBREAK.

Do not run that experimental build on the user's console as if it were a completed jailbreak. This project does not copy its exploit code or binaries.

## Previous Akatsuki variant

Repository: https://github.com/Jfkkfjzkz/ps4-akatsuki-jailbreak

This variant makes similar 14.02 assumptions and has an always-true password condition in its landing page. It is not independently validated.

## Browser report received from the PS4

Reports received on 2026-11-13 indicated:
- Firmware hint: 14.02
- WebKit hint: 605.1.15
- Browser class: ps4-browser
- 11 of 18 browser APIs available
- 10 of 16 safe checks passed
- Service Worker, WebAssembly, IndexedDB, WebGL and WebGL2 unavailable in the observed profile
- Cache Storage, Application Cache, BigInt, Atomics, LocalStorage, WebCrypto, Fetch and typed arrays available

These observations describe browser compatibility only. They do not prove or disprove a specific WebKit vulnerability.

## Backend and privacy

- Private store: jbhereps4-reports-private-02
- Access: private
- Region: gru1
- Folder: metadata/reports/
- Uploads are normalized server-side and verified by reading the private object back.
- The server-side self-test creates a temporary private JSON object, reads it, and deletes it.
- Report listing and self-test require METADATA_READ_TOKEN; unauthenticated GET requests return HTTP 401.
- Four historic reports were migrated into the private store and the public copies were deleted.
- The old public store is empty and no longer used by the current backend.

The client report intentionally excludes cookies, credentials, full User-Agent, and account content. Hosting infrastructure still receives normal connection metadata.

## Validation limits

A successful browser test only establishes that a browser API was available and behaved as expected in that test. It is not evidence of code execution outside the browser sandbox, kernel access, or jailbreak capability.

## Sources

- https://consolemods.org/wiki/PS4:FAQ
- https://consolemods.org/wiki/PS4:Exploit_Chart
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://github.com/Jfkkfjzkz/A
- https://github.com/Jfkkfjzkz/ps4-akatsuki-jailbreak
- https://github.com/well0nez/afterglow-web
- https://github.com/GoldHEN/GoldHEN/releases
- https://github.com/GoldHEN/GoldHEN/issues/422
