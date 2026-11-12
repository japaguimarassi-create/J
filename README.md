# HEN 14.02 — PS4 Host

Offline-first static compatibility dashboard and documentation site for PS4 firmware research.

## Compatibility facts
- ConsoleMods' PS4 FAQ explicitly states there is no jailbreak for firmware 14.02.
- Its Getting Started guide lists 14.00 as the latest exploited firmware in that guide.
- GoldHEN is a Homebrew Enabler payload; it is not an exploit entry point.
- The official GoldHEN v2.4b18 release page lists supported firmware through 11.00.
- This project does not include WebKit or kernel exploit code, GoldHEN binaries, payload injection or console modification routines.

## GamerHack G2All integration
- Audited the public GamerHack/GamerHack.github.io repository; its current public launcher has firmware routes through 14.00 and rejects 14.01+.
- The dashboard reveals a direct link to the real upstream G2All host only after the user manually confirms 14.00.
- Firmware 14.02 remains blocked: the current PS4 Developer Wiki records the 14.00 AIO kernel vulnerability as patched on 14.02 and lists no public 14.02 kernel chain.
- GoldHEN v2.4b18.13 is the separate community beta bundled by G2All for 14.00. The stable upstream v2.4b18 release page still lists support through 11.00.

## Features
- Responsive dark-first UI with light mode toggle.
- Static PWA cache (optional) plus a standalone offline HTML reference for browsers without Service Worker support.
- Two-stage reload-based preflight using sessionStorage.
- Browser API checks only; no exploit testing, memory scanning or payload loading.
- GoldHEN official firmware compatibility reference and local version gate.
- Exportable local browser preflight report.
- English and Portuguese guide.\n- PS4 User-Agent firmware hint, D-pad focus navigation and a real G2All 14.00 upstream launch gate.
- GitHub Actions workflow for GitHub Pages.

## Publish with GitHub Pages
1. Open this repository's Settings → Pages.
2. Set the build and deployment source to GitHub Actions.
3. The workflow deploys the static site whenever the hen-14-02-host branch is updated.
4. Open the Pages URL shown by GitHub after the workflow completes.

## Run locally
Serve this directory over HTTPS or localhost. Service Workers are unavailable in most local file URL contexts.

## Sources
- https://consolemods.org/wiki/PS4:FAQ
- https://consolemods.org/wiki/PS4:Getting_Started
- https://github.com/GoldHEN/GoldHEN/releases\n- https://github.com/GamerHack/GamerHack.github.io\n- https://www.psdevwiki.com/ps4/Vulnerabilities

Independent community project. Not affiliated with Sony, PlayStation or GoldHEN.
