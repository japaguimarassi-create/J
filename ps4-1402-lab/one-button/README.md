# JBherePS4 v1.5.1

PS4 14.02 diagnostics, experimental exploit-claim audit, and private report backend.

## Current conclusion

There is no independently verified, reproducible, complete jailbreak for PS4 14.02 in the public exploit chart. A public experimental repository now claims partial kernel access, but its own test notes say that launching a game causes a kernel panic and HEN/GoldHEN threads die during initialization. That is not a usable jailbreak.

## New experimental claim audited on 2026-11-13

Repository: https://github.com/Jfkkfjzkz/A

The repository's CHAIN.txt snapshot dated 2026-11-11 claims:
- uid 0
- kernel read/write
- 15/15 patch stubs applied
- Debug Settings patch applied

The same file explicitly records the following failures:
- launching a game on the patched kernel causes a kernel panic
- HEN/GoldHEN payload threads die during initialization
- installer init #1 reportedly survives, while init #2 is untested
- a working game-launching HEN is not demonstrated

The source does not independently validate the full chain:
- README.md still documents the Afterglow exploit for firmware 14.00.
- afterglow-g.js identifies its base as firmware 14.00 and its header says the code has never executed in that host.
- ps4_offsets.js creates the 14.02 table by copying PS4["14.00"], while its status text says WebKit is assumed identical to 13.52 and kernel offsets are from 14.00 plus shiftfit.

Assessment: UNVERIFIED_PARTIAL_KERNEL_CHAIN_NOT_A_USABLE_JAILBREAK.

Do not execute this experimental build on the user's console as if it were a completed jailbreak. The project does not copy its exploit code or binaries.

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

## Scope

This project does not execute the experimental Afterglow chain, memory corruption, kernel syscalls, kernel memory read/write, firmware modification, ELF/BIN payloads, or GoldHEN injection. It records evidence and verifies the backend without changing the console.

## Sources

- https://consolemods.org/wiki/PS4:FAQ
- https://consolemods.org/wiki/PS4:Exploit_Chart
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://github.com/Jfkkfjzkz/A
- https://github.com/Jfkkfjzkz/ps4-akatsuki-jailbreak
- https://github.com/well0nez/afterglow-web
- https://github.com/GoldHEN/GoldHEN/releases
- https://github.com/GoldHEN/GoldHEN/issues/422
