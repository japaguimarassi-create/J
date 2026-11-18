# Security baseline

Google sign-in must be verified server-side: validate JWT signature, audience, issuer, expiry and email_verified. Use the Google sub claim as the stable external identity key; an email suffix is not authentication.

First-admin assignment must be serialized transactionally in the database so concurrent first registrations cannot create multiple owners. Session cookies must be Secure, HttpOnly and appropriately SameSite, with CSRF protection on state-changing cookie-authenticated routes. Keep OAuth secrets, session keys and database credentials out of source control.

Treat uploaded files, repository content and tool output as untrusted data. Terminal and filesystem operations remain disabled until isolation, operation-level authorization, explicit approvals and audit records exist. Apply size limits, rate limits, input validation and redacted logs before public deployment.

This is a design baseline, not evidence that deferred security controls are operational.