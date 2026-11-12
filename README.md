# HEN Research Center

Rebuild v2 of the PS4 HEN research dashboard.

## Scope
- Firmware compatibility matrix and evidence links.
- Read-only browser diagnostics.
- Official GoldHEN release and supported-firmware reference.
- Research summaries with links to primary/community documentation.
- Optional Service Worker cache for secure contexts.

## Important limitation
This repository does not contain or execute a PS4 exploit, kernel chain, GoldHEN payload, firmware downgrade, NOR/Syscon flasher, or update bypass. Firmware 14.02 has no public userland/kernel jailbreak listed in the consulted ConsoleMods chart. Do not interpret browser checks as a jailbreak.

## Sources
- https://consolemods.org/wiki/PS4:Exploit_Chart
- https://consolemods.org/wiki/PS4:FAQ
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://github.com/GoldHEN/GoldHEN/releases
- https://github.com/GamerHack/GamerHack.github.io
- https://consolemods.org/wiki/PS4:Firmware_Revert

## Deployment
Static site. GitHub Pages or Vercel can serve the repository root. Service Worker requires HTTPS (or localhost).
