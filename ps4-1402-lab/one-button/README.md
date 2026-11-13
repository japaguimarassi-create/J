# JBherePS4 v1.7.0

PS4 14.02 safe browser diagnostics, functional API checks, temporary-session reporting, and private report storage.

## Current conclusion

No independently reproducible public complete jailbreak or HEN for PS4 14.02 is confirmed by the sources reviewed on 2026-11-13. ConsoleMods currently lists fully implemented public jailbreaks through 14.00 and says there is no jailbreak for 14.02. The PS4 Developer Wiki documents the Afterglow kernel vulnerability as working through 14.00 and possibly patched in 14.02. An experimental 14.02 repository claims partial kernel access but its own test notes report kernel panics on game launch and HEN/GoldHEN initialization failures. A private demonstration has been reported, but no reproducible public package was verified.

## What v1.7.0 does

- Inventories browser API availability without privileged interfaces.
- Performs small functional tests for TypedArray, WebAssembly validation, LocalStorage, IndexedDB, Cache Storage and WebCrypto SHA-256.
- Uses temporary unique IndexedDB and Cache Storage names and attempts cleanup after each test.
- Creates and releases WebGL contexts when supported.
- Labels firmware parsed from User-Agent as a non-authoritative hint.
- Prepares static cache resources where the browser supports them.
- Saves a local JSON report and offers download/copy controls.
- Tests private report storage before upload.
- Preserves a local report when offline or when the backend is unavailable.

## What it does not do

- It does not activate HEN or jailbreak the console.
- It does not execute memory corruption, kernel syscalls, kernel read/write or exploit chains.
- It does not modify firmware, install payloads, load ELF/BIN files or inject GoldHEN.
- It does not treat browser API support as evidence of a vulnerability.
- It does not treat User-Agent firmware strings as proof of the installed firmware.

## Experimental 14.02 claim audited on 2026-11-13

Repository: https://github.com/Jfkkfjzkz/A

The repository's CHAIN.txt snapshot claims uid 0, kernel read/write and 15/15 patch stubs, but also records a kernel panic when launching games and HEN/GoldHEN threads dying during initialization. It does not demonstrate a usable stable HEN.

The source also documents assumptions in the 14.02 offsets and an Afterglow base still identified as firmware 14.00. Assessment: UNVERIFIED_PARTIAL_KERNEL_CHAIN_NOT_A_USABLE_JAILBREAK.

Do not run this experimental build on the console as if it were a completed jailbreak.

## Previous Akatsuki variant

Repository: https://github.com/Jfkkfjzkz/ps4-akatsuki-jailbreak

The 14.02 port derives offsets from 14.00 and includes an always-true password condition in its landing page. It is not independently validated.

## Observed PS4 browser profile

Reports received on 2026-11-13 indicated firmware hint 14.02, WebKit hint 605.1.15, 11 of 18 browser APIs available and 10 of 16 prior safe checks passed. Service Worker, WebAssembly, IndexedDB and WebGL were unavailable in that observed profile. Cache Storage, BigInt, Atomics, LocalStorage, WebCrypto, Fetch and typed arrays were available.

These observations describe browser compatibility only. They do not prove or disprove a WebKit vulnerability.

## Backend and privacy

- Private store: jbhereps4-reports-private-02
- Access: private
- Region: gru1
- Folder: metadata/reports/
- Uploads are normalized server-side and verified by reading the private object back.
- The server-side self-test creates a temporary private JSON object, reads it and deletes it.
- Report listing and self-test require a Bearer token in the Authorization header.
- Query-string tokens are not accepted, avoiding token exposure through URLs and browser history.
- Four historic reports were migrated into the private store and the old public store was emptied.

The client report intentionally excludes cookies, credentials, full User-Agent and account content. Hosting infrastructure still receives normal connection metadata.

## Validation limits

A successful browser test only establishes that a browser API was available and behaved as expected in that test. It is not evidence of code execution outside the browser sandbox, kernel access or jailbreak capability.

## Sources

- https://consolemods.org/wiki/PS4:FAQ
- https://consolemods.org/wiki/Ps4_getting_started
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://github.com/Jfkkfjzkz/A
- https://github.com/Jfkkfjzkz/ps4-akatsuki-jailbreak
- https://github.com/well0nez/afterglow-web
- https://github.com/GoldHEN/GoldHEN/releases
- https://github.com/GoldHEN/GoldHEN/issues/422
- https://scenegaming.com/en/consoles/ps4?type=news
