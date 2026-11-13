# JBherePS4 v1.3.0

Single-button PS4 browser diagnostics with automatic metadata upload.

## Report backend

A successful browser diagnostic automatically POSTs a minimized JSON report to `/api/metadata`. The Vercel Function stores each report as a Blob at `metadata/reports/<uuid>.json`. The GET endpoint `/api/metadata` returns the latest reports in JSON so they can be reviewed without copying data from the console.

The report contains only:
- Firmware hint if the browser exposes it.
- Boolean browser capability flags.
- Online and secure-context booleans.
- Public compatibility evidence summary and timestamps.

The JSON report excludes the full User-Agent, IP address, cookies, session identifiers, platform/language strings, and WebGL renderer strings. The hosting provider still necessarily receives network connection metadata such as the connecting IP, and may retain standard security/request logs. Vercel infrastructure may still retain ordinary request/security logs outside this application report.

**Visibility:** the Blob store and GET endpoint are public. Anyone who knows the endpoint can read the minimized technical reports. Do not submit personal information.

If upload fails or the PS4 is offline, the report remains in local browser storage and the page reports the error. Re-run while online to upload again.

## Safety

This is a browser-only diagnostic. It does not trigger an exploit, access kernel memory, invoke syscalls, patch firmware, load ELF/BIN payloads, or install GoldHEN.

## Runtime

The API is a Vercel Node.js Function. Reports are stored in Vercel Blob, not the ephemeral function filesystem. Blob region: GRU (São Paulo). Store name: `jbhereps4-metadata`.

## Official documentation

- https://vercel.com/docs/vercel-blob/private-storage
- https://vercel.com/docs/vercel-blob/using-blob-sdk
- https://vercel.com/docs/vercel-blob/usage-and-pricing
