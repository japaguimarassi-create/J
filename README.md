# HEN 14.02 — PS4 Host

Offline-first static compatibility dashboard and documentation site for PS4 firmware research.

## Compatibility facts
- ConsoleMods' PS4 FAQ explicitly states there is no jailbreak for firmware 14.02.
- Its Getting Started guide lists 14.00 as the latest exploited firmware in that guide.
- GoldHEN is a Homebrew Enabler payload; it is not an exploit entry point.
- The official GoldHEN v2.4b18 release page lists supported firmware through 11.00.
- This project does not include WebKit or kernel exploit code, GoldHEN binaries, payload injection or console modification routines.

## Features
- Responsive dark-first UI with light mode toggle.
- Static PWA and service-worker cache.
- Two-stage reload-based preflight using sessionStorage.
- Browser API checks only; no exploit testing, memory scanning or payload loading.
- GoldHEN official firmware compatibility reference.
- Exportable local browser preflight report.
- English and Portuguese guide.

## Run locally
Serve this directory over HTTPS or localhost. Service Workers are unavailable in most local file URL contexts.

## Sources
- https://consolemods.org/wiki/PS4:FAQ
- https://consolemods.org/wiki/PS4:Getting_Started
- https://github.com/GoldHEN/GoldHEN/releases

Independent community project. Not affiliated with Sony, PlayStation or GoldHEN.
