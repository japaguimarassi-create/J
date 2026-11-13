# JBherePS4 v1.4.2

PS4 14.02 browser compatibility lab with source-backed exploit status and non-invasive tests.

## Test suite

- Detects a PS4 browser and firmware hint only when the User-Agent exposes it.
- Records an AppleWebKit version hint when exposed.
- Runs a deterministic TypedArray check on a 64 KiB buffer.
- Validates an empty WebAssembly module without loading external code.
- Checks BigInt, Atomics, SharedArrayBuffer, WebGL/WebGL2, IndexedDB, Cache Storage, Service Worker, LocalStorage and WebCrypto.
- Tests a temporary LocalStorage value by writing, reading and deleting it.
- Tests the Blob backend with temporary JSON write/read/delete before uploading the report.
- Stores a minimized report under `metadata/reports/`.

These are compatibility checks, not vulnerability tests. A supported browser API does not prove a CVE, userland exploit or kernel exploit.

## PS4 14.02 evidence (reviewed 2026-11-13)

- The public exploit chart lists no public userland exploit or public kernel exploit for 14.02.
- Prolapse is documented as patched since 14.02.
- Afterglow is publicly released for 12.00, 12.02, 12.50, 12.52, 13.00, 13.02, 13.04, 13.50, 13.52 and 14.00. Its status on 14.02 is unconfirmed and may be patched.
- A private 14.02 HEN demonstration was reported on 2026-11-05, but no public source code or independently reproducible procedure was reported.
- The official GoldHEN public release list does not include 14.02.

## Metadata visibility

The connected store `jbhereps4-metadata` is public, and `/api/metadata` lists the minimized reports. The report excludes full User-Agent, IP address, cookies, credentials, and session identifiers. Vercel still receives ordinary request metadata. Do not submit personal information.

A separate private store `jbhereps4-meta-v2` exists but is not connected to this project and is not used by this deployment.

## Explicit limits

The site does not execute memory corruption, call kernel syscalls, read/write kernel memory, modify firmware, load ELF/BIN payloads, install GoldHEN, or bypass Sony protections. It cannot convert a browser-capability result into proof of exploitability.

## Sources

- https://consolemods.org/wiki/PS4:Exploit_Chart
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://github.com/well0nez/afterglow-web
- https://github.com/GoldHEN/GoldHEN/releases
- https://github.com/GoldHEN/GoldHEN/issues/422
- https://scenegaming.com/en/news/ps4-14-02-hen-webkit-demostracion-saudidos
