# Security baseline

## Implemented in the current slice

- Google ID tokens are validated server-side by Google's verification library. The service requires the expected OAuth audience, accepted Google issuer, valid signed/unexpired token and email_verified=true; Google sub is the stable external identity key.
- PostgreSQL stores account identities and hashes of random opaque session tokens. Session cookies are HttpOnly and Secure by default, with configurable SameSite behavior.
- Logout requires a double-submit CSRF token that is also checked against the digest stored for the session.
- First-admin assignment locks the singleton platform-state row inside a transaction, preventing concurrent first logins from creating multiple owners.
- Chat and administrative user-list endpoints require a valid session; the user-list endpoint checks the admin role on the server.

## Required before public production use

- Configure exact Google OAuth origins, a real PostgreSQL instance, production secrets and database backups.
- Add distributed rate limiting at the reverse proxy/API gateway and per-account quotas. The current app does not yet provide distributed rate limiting.
- Add retention policies, scheduled expired-session cleanup, audit events, monitoring and incident recovery.
- Apply CSRF protection to every future cookie-authenticated state-changing route, not only logout.
- Treat uploaded files, repository content and tool output as untrusted data, never policy instructions.
- Keep terminal and filesystem operations disabled until there is an isolated worker, per-operation authorization and explicit approval flow.
- Require explicit approval and audit records for destructive or externally visible operations.
- Add strict request size limits, structured validation, redacted logs and security testing before public deployment.

This document distinguishes implemented controls from deferred deployment requirements; it is not a claim of production security certification.
