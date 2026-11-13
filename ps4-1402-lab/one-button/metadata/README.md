# Metadata

Automatic, minimized PS4 browser diagnostic reports are stored in the connected Vercel Blob store under `metadata/reports/`.

The report directory is external persistent storage, not the deployment filesystem. Read the latest JSON through `/api/metadata`.

Reports do not include full User-Agent, IP, cookies, session IDs, or WebGL renderer strings. The endpoint and report objects are public and contain technical metadata only.
