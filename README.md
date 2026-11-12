# HEN 14.02 — Rebuild 2

PT-BR-first static PS4 browser host and research portal.

## Research snapshot (2026-11-12)

- ConsoleMods Exploit Chart: public routes through PS4 firmware 14.00; no public userland or kernel chain listed for 14.02.
- PS4 Developer Wiki: Prolapse is listed as patched since 14.02. Afterglow is tested on 13.52–14.00; its patch status on 14.02 is uncertain.
- GamerHack G2All public source has a dedicated 14.00 route. This site forwards to that upstream host after user confirmation; it does not copy the exploit chain or payload binaries.
- GoldHEN v2.4b18.13 is a beta payload advertised for 14.00. It does not provide the missing entry point/kernel exploit.
- Firmware revert is not a browser operation. It requires case-specific hardware assessment of previous firmware slots, NOR/Syscon state and compatible hardware. Brick risk is real.

## Design constraints

- No external fonts, CSS frameworks, SVG, WebGL, WebAssembly, ES modules or modern JavaScript syntax.
- Semantic anchors/forms and visible focus for the PS4 browser and DualShock 4 tab-style navigation.
- Legacy Application Cache manifest for the PS4 browser. Service Worker is optional for modern browsers.
- User-Agent version is only a hint; the user must verify System Information manually.
- The 14.00 link is a real upstream redirect. Firmware 14.02 is blocked.
- Revert Check is read-only and local-only; it cannot read/write NOR or Syscon.

## Files

- index.html: dashboard and firmware checker
- run.html: 14.00-only gate to GamerHack G2All
- compat.html: browser diagnostics
- goldhen.html: GoldHEN version and provenance notes
- revert-check.html: cautious hardware-revert triage
- guide.html: Portuguese user guide
- status.html: evidence links and research matrix
- site.manifest: legacy Application Cache resources
- sw.js / manifest.json: optional modern PWA support

## Upstream references

- https://consolemods.org/wiki/PS4:Exploit_Chart
- https://consolemods.org/wiki/PS4:FAQ
- https://consolemods.org/wiki/PS4:Firmware_Revert
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://www.psdevwiki.com/ps4/Internet_Browser
- https://www.psdevwiki.com/ps4/DualShock_4
- https://github.com/GamerHack/GamerHack.github.io
- https://github.com/GoldHEN/GoldHEN/releases
- https://github.com/patnawa/GoldhenPS4/releases/tag/v1.0.5
