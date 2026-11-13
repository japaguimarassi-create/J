# JBherePS4

Single-button offline PS4 browser diagnostics. Version 1.2.0 includes the JBhere Safe Probe and a visible local JSON report.

## Safe Probe

Reads only browser-exposed information: User-Agent firmware hint, platform/language, online state, secure context, browser APIs and optional WebGL renderer. The resulting JSON report is saved locally and displayed in the page under "VER RELATÓRIO JSON".

It does not exploit WebKit, attempt kernel access, invoke syscalls, read/write privileged memory, patch firmware, load ELF/BIN files, install PKGs, or load GoldHEN.

## PS4 firmware 14.02 status (reviewed 2026-11-13)

A private HEN demonstration was reported in a video dated 2026-11-05, but no source code or reproducible release is public. This does not prove that no vulnerability exists; it means there is no public, independently reproducible chain to test.

A third-party repository claims 14.02 support. Its own technical notes describe the WebKit compatibility as assumed from 13.52 and its kernel offsets as derived from 14.00 with a "shiftfit". That is not a measured, independently verified 14.02 port. The project therefore treats the claim as unverified and does not execute its binaries.

## GoldHEN

- Official upstream GitHub release visible: v2.4b18; its declared firmware list ends at 11.00.
- Community revision v2.4b18.13 reports support for 14.00.
- Neither source declares 14.02 support.

The site does not download or load GoldHEN binaries.

## Sources

- https://github.com/GoldHEN/GoldHEN/releases
- https://github.com/GoldHEN/GoldHEN/issues/422
- https://github.com/EEJTek/GoldHEN_v2.4b18.12
- https://github.com/Jfkkfjzkz/ps4-akatsuki-jailbreak
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://consolemods.org/wiki/PS4%3AExploit_Chart
- https://scenegaming.com/en/news/ps4-14-02-hen-webkit-demostracion-saudidos

## Offline behavior

The first visit must be HTTPS to register Service Worker/Cache Storage. Legacy Application Cache remains declared as a fallback, but its support must be checked on the actual PS4 browser. The report remains on the console's local browser storage unless manually copied.
