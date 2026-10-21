# Security policy

Do not commit credentials, API keys, private data or model checkpoints containing unreviewed training material.

Store GitHub tokens in environment variables or a secrets manager. Deta must send authentication only to the intended GitHub API host, never to raw content hosts or arbitrary source URLs. Do not paste access tokens into issues, prompts, datasets or source files.

Report potential security issues privately to the repository owner rather than publishing secrets or exploit details. Do not include confidential information in public GitHub issues.

Generated or ingested code must be tested in an isolated environment without production credentials. The four-pass verifier is a preliminary gate, not a security guarantee.

For data incidents, preserve the source manifest and hashes, stop using affected data, identify derived manifests/checkpoints, follow the original dataset's removal process, and record the remediation.
