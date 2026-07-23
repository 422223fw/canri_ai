# Canri brains

This package is the organized loading boundary for every Canri brain.

- `catalog.py` is the single authoritative list used by `main.py` registration.
- `agent.py` owns bounded project actions, approvals, backups, commands, and audit records.
- `project_context.py` indexes related files and supplies bounded cross-file context.
- Root-level `Agent_brain.py` and `Project_context_brain.py` are compatibility imports.

Existing root-level brain modules remain in place temporarily because they resolve
their data files relative to their current location and are imported directly by
external tests. Moving them without compatibility wrappers would break those paths.
New brains should be implemented in this package and may expose a root-level wrapper
until all external imports have migrated.

Agent modes:

- `off`: no project reading or action.
- `autonomous`: executes approved tool types without asking each time.
- `restricted`: uses a smaller command set and cannot run destructive operations.
- `approval`: reads context but queues every write or command for chat approval.

No mode may escape the selected workspace, modify source-control metadata, invoke a
shell, or execute a hard-blocked destructive/system command.
