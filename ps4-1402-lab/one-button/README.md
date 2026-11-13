# JBherePS4

Single-button offline PS4 browser diagnostics. Version 1.1.0 adds the JBhere Safe Probe.

## Safe Probe

The probe reads only browser-exposed information: User-Agent firmware hint, platform/language, online state, secure context, browser APIs and optional WebGL renderer. It stores the resulting JSON report in local browser storage.

It does not exploit WebKit, attempt kernel access, invoke syscalls, read/write privileged memory, patch firmware, load ELF/BIN files, install PKGs, or load GoldHEN.

## Firmware 14.02 and GoldHEN

As reviewed on 2026-11-13, the official GoldHEN GitHub release page lists v2.4b18 and supported firmware through 11.00. A community host advertises a separate 2.4b18.13 payload up to 14.00 and explicitly refuses 14.01+. That is not proof of official 14.02 support. No verified public 14.02 exploit chain or GoldHEN compatibility is established by this project.

The site therefore does not download or execute any GoldHEN binary and stops at the compatibility gate.

## Offline

The first visit must be HTTPS to register Service Worker/Cache Storage. Legacy Application Cache is retained as a fallback declaration, but browser support must be tested on the actual PS4. The probe does not transmit its report.

## Sources

- https://github.com/GoldHEN/GoldHEN/releases
- https://github.com/GoldHEN/GoldHEN/issues/422
- https://github.com/patnawa/GoldhenPS4/releases
- https://github.com/well0nez/afterglow-web
- https://scenegaming.com/en/news/ps4-jailbreak-14-00-goldhen-firmware-14-02
