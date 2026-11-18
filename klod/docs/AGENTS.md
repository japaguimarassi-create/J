# Agent execution foundation

The current implementation adds a bounded coordinator that invokes registered asynchronous Python agent modules in sequence. Each module receives a typed context and the prior module's structured output. The coordinator enforces a maximum number of steps, a wall-clock deadline, unique module names, and result validation. A failed module stops the run.

The workspace helper confines resolved paths to one configured root. Reads require filesystem:read. Writes require filesystem:write and an approval entry matching the exact relative path. Writes are size-limited and use a temporary file followed by atomic replacement.

This is an execution foundation, not a finished autonomous multi-agent product. No research connector, shell/terminal executor, model-driven planner, Git client, or agent API route is enabled. Tool operations remain unavailable until a deployment-specific sandbox and audit layer are integrated.
