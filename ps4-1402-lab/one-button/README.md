# JBherePS4 v1.5.0

PS4 14.02 browser diagnostics and private report backend.

## Current conclusion

The public ConsoleMods FAQ consulted on 2026-11-13 explicitly states that firmware 4.05 through 14.00 has a jailbreak and that there is no jailbreak for 14.02. This repository does not claim otherwise.

A complete PS4 jailbreak requires a userland entry point and a compatible kernel exploit. Browser capability checks are not vulnerability proof. This project does not attempt a kernel exploit, memory corruption, syscall invocation, or payload injection.

## Audit of the 14.02 candidate

Repository: https://github.com/Jfkkfjzkz/ps4-akatsuki-jailbreak

The public candidate claims 14.02 support, but the inspected source contains material caveats:

- The ps4_offsets.js file defines 14.02 by copying the 14.00 object and overriding only a status string.
- That status string says WebKit is assumed identical to 13.52 and kernel offsets come from 14.00 plus shiftfit.
- The afterglow-g.js file identifies its exploit base as firmware 14.00.
- The index.html file contains a password condition that is always true (if true OR password matches) and a referrer check that always returns true. These are interface-gate defects, not proof of exploit failure.
- The README lists a kernel_1402.bin, but that alone does not prove offsets, payload compatibility, or a physical 14.02 test.

Assessment: an unverified 14.02 port, not a reproducible jailbreak. Do not treat it as proven or execute it on the console based on the README claim.

## Report received from the PS4 browser

The reports received on 2026-11-13 indicated:

- Firmware hint: 14.02
- WebKit hint: 605.1.15
- Browser class: ps4-browser
- 11 of 18 browser APIs available
- 10 of 16 safe checks passed
- Service Worker, WebAssembly, IndexedDB, WebGL and WebGL2 unavailable in the observed browser profile
- Cache Storage, Application Cache, BigInt, Atomics, LocalStorage, WebCrypto, Fetch and typed arrays available

These are browser compatibility observations. They do not establish whether a particular vulnerability exists.

## Backend and privacy

- New store: jbhereps4-reports-private-02
- Access: private
- Region: gru1
- Folder: metadata/reports/
- Uploads are normalized server-side and verified by reading the private object back.
- The self-test creates a temporary private JSON object, reads it back, and deletes it.
- Report listing requires METADATA_READ_TOKEN; unauthenticated GET requests are rejected.
- The client report omits the full User-Agent, cookies, IP address, credentials, account data and session identifiers. Vercel receives ordinary request metadata.

The old public store jbhereps4-metadata has four historical reports. The new deployment no longer writes to it. Those four old objects remain in the legacy store pending a separate cleanup decision; do not confuse them with new private reports.

## Sources

- https://consolemods.org/wiki/PS4:FAQ
- https://consolemods.org/wiki/PS4:Exploit_Chart
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://github.com/well0nez/afterglow-web
- https://github.com/GoldHEN/GoldHEN/releases
- https://github.com/GoldHEN/GoldHEN/issues/422
- https://github.com/Jfkkfjzkz/ps4-akatsuki-jailbreak
