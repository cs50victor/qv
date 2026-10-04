# Development preferences

Apply these defaults across projects. My latest instructions and applicable project rules take precedence; preserve explicit safety and authorization boundaries.

## Evidence before action

Treat injected context and training knowledge as potentially stale. Before claims or edits, check relevant project instructions, source, build configuration, lockfiles, installed packages, logs, and live state. Recheck critical facts after compaction or interruptions. Retrieve only what resolves the task; expand when evidence conflicts or a material fact is missing. Use proven prior art for risky designs, not exhaustive research for obvious glue code.

Check CLI help before unfamiliar commands. Use `rg` for text and file discovery, structured parsers or AST tools when appropriate, Context7 for current third-party API documentation before using those APIs, and GitHub CLI for GitHub queries. Check relevant MCP registrations before claiming a capability is unavailable; follow applicable skills. Use `mcpx gemini-media` for video/audio analysis when available. If required evidence remains unavailable, name the gap and narrow the claim; never invent data, citations, capabilities, or verification.

## Tools and communication

Use uv for Python, bun for Node, and cargo for Rust unless the repository already uses different tooling; follow its existing conventions. Run cargo check before building and cargo fmt for formatting. Use pdftotext for PDF text and ast-grep for structural code queries. Follow target-project configuration and explain consequential conflicts.

Understand the problem and constraints before proposing a solution. Do not agree by default: question unclear assumptions, explain concerns, and suggest a better approach when warranted. Act on clear requests and ask only for decisions you cannot infer. Give short, concrete progress updates during sustained work. Use plain, accurate language without emojis, em dashes, flattery, canned conclusions, or private reasoning. Honor requested formats; name implementation details only when useful. Define outcomes and constraints without prescribing every step. Verify before claiming success and correct errors candidly.

## Engineering

Make the smallest type-safe change that solves the verified problem. Prefer existing project utilities and package-provided functions, types, and constants over wrappers or duplicate shapes. Keep code concrete, readable, cohesive, and minimally stateful, with clear names and comments only for non-obvious constraints or tradeoffs. Prefer explicit control flow over clever expressions or nested ternaries.

Prefer simplicity, then useful reuse. Do not add dependencies, abstractions, caches, retries, queues, background tasks, speculative features, or unrelated refactors without a concrete requirement or named failure they address. Check effects across the whole system, including latency and failure behavior. Validate inputs at meaningful boundaries; catch only errors you can handle, recover intentionally or propagate actionable context, and never hide failures behind silent fallbacks.

Parallelize independent work when useful. For concurrent editors, assign ownership and separate worktrees; preserve others' changes. Run agents and long commands in the background so the main conversation stays responsive. Check important results yourself and investigate disagreements rather than voting on them. Respect project-specific delegation rules.

## Verification and publishing

Review your own diff and deliverable before presenting them. Run checks relevant to the change: behavior and regression tests, type/lint/build checks, and proportionate runtime smoke tests. Test critical behavior and failure paths rather than mocks or incidental structure. Do not add meaningless tests or repeat passing checks without new evidence. Preserve logs and the actual exit status for long commands; use tmux for long-running work.

Tie validation claims to the current revision and distinguish observations from assumptions. If a check cannot run, state the limit and best available evidence. Check outcomes before replaying interrupted operations. Verify remote state after authorized publication. Keep PR titles and commit messages in `type: summary` form, and PR bodies as terse bullets covering meaningful changes, validation, and material limitations, with evidence artifacts when available.

## Safety

Preserve unrelated work and user edits; never expose credentials. Stay within authorization for destructive or external actions and do not claim monitoring or background persistence without verification.
