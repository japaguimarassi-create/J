# JBherePS4 v1.4.0

PS4 14.02 non-invasive browser research harness.

## What this build actually does

- Prepares an offline cache of the host and test modules.
- Detects a PS4 browser hint and firmware/WebKit version only if exposed in the User-Agent.
- Checks browser APIs such as Service Worker, Cache Storage, WebAssembly, BigInt, IndexedDB, WebGL and related capabilities.
- Performs a backend storage self-test: temporary JSON write, read, and delete.
- Uploads a minimized technical report to \`metadata/reports/\`.
- Preserves the full local report in browser localStorage.

## What it does not do

This is not a jailbreak and does not execute an exploit. It does not attempt memory corruption, kernel access, syscalls, firmware modification, ELF/BIN loading, payload injection, or GoldHEN installation. Browser feature detection cannot establish that a kernel vulnerability exists.

## PS4 14.02 research status (reviewed 2026-11-13)

The current public ConsoleMods exploit chart lists 14.02 without a public userland exploit or public kernel exploit. PS4 Dev Wiki marks Prolapse as patched since 14.02 and Afterglow as possibly patched in 14.02. Consequently, no public, independently reproducible full jailbreak chain is established for this firmware.

GoldHEN's official public release list does not declare 14.02 support. Do not treat a third-party host's firmware claim as proof without independently reproducible hardware evidence.

## Metadata backend

The active connected store is \`jbhereps4-metadata\`, region GRU, and its access mode is **public**. The report endpoint lists minimized reports at \`/api/metadata\`. Do not submit personal data. The application report omits full User-Agent, IP address, cookies, credentials, and session identifiers; the hosting provider still receives ordinary connection metadata.

A separate private store named \`jbhereps4-meta-v2\` exists but is not connected to this Vercel project. It is not used by this deployment.

## Validation

Before sending a report, the browser calls the API's self-test path. The function writes a temporary JSON blob, reads it back, validates it, deletes it, and only then stores the real report. If any stage fails, the report remains local and the page displays the error.

## Sources

- https://consolemods.org/wiki/PS4:Exploit_Chart
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://github.com/well0nez/afterglow-web
- https://github.com/GoldHEN/GoldHEN/releases
- https://github.com/GoldHEN/GoldHEN/issues/422
- https://vercel.com/docs/vercel-blob/private-storage
