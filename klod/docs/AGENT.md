# Single-agent design

Klod has exactly one agent identity. One model runtime handles the conversation and task context. It does not spawn fake specialist agents or route work to separate simulated personas.

The coder is a capability inside the same agent. The current CoderWorkspace provides path-confined text reads and writes. Reads need filesystem:read. Writes need filesystem:write plus a separate approval for the exact relative path. Files are size limited; path traversal and paths resolving outside the workspace are rejected.

The workspace is currently a backend capability and is not yet exposed as a public web/API action. No host shell is enabled. Terminal execution must wait for a dedicated isolated worker with per-user workspace isolation, resource limits, operation audit and explicit approval for commands with side effects.

The two Claude model references are functional quality goals. Klod does not load their proprietary weights or claim to reproduce their current maximum performance. It uses one independently trained neural model and must demonstrate capability through evaluation.
