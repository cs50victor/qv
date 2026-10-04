# Daily records and backups

Use this when recording work, editing the checklist, delivering artifacts or
backing up. The coordinator owns these files; workers return workspace results.

## Record and resume work

Keep `YYYY/MM/DD/task/<task-id>.md` and `artifacts/<task-id>/` under `~/daily`,
using the task's local start date. Later days link back instead of moving records.
Before dispatch or changed scope, record:

- Outcome, priority, completion criteria, dependencies, constraints and next step.
- Owner, resolved workspace, planned tmux target, log/result paths, task ID,
  unique completion ID and planned notice path.

After launch, add observed session/thread IDs and launch status. Record results,
blockers and next actions with local timestamps. Collect verified artifacts into
the task's artifact directory and link them from its record.

On recovery, read today's checklist and relevant task records, inspect owned
workers and review unchecked notices in the indicated day, today and linked older
days. Do not scan or rewrite all history. Account for each outcome as active,
queued, blocked, cancelled or verified complete. Preserve previous decisions and
check interrupted actions before replaying them.

## Maintain the checklist

Use `~/daily/YYYY/MM/DD/main.html` and the installed
[template](../main.template.html). Keep task IDs stable and link task records.
Before editing today's page, start and verify a local HTTP server for it; keep
that server running during edits. Preserve useful notes in details or linked
records rather than crowding the task list.

Set each row's `data-status` from evidence; the template derives disabled checkbox
properties and status text. Keep its Tailwind Play CDN, fallback CSS and visible
text labels. Do not add browser storage or manual status toggles.

| Status | Meaning and display |
| --- | --- |
| `not-started` | Neutral, unchecked; queued/deferred work has a visible note |
| `in-progress` | Yellow, indeterminate; work is actually advancing |
| `completed` | Green, checked; requested outcome has been verified |
| `blocked` | Red, unchecked with a marker; visible dependency and next action |

Label cancelled work explicitly, never as success. A handled notice may report a
failure or handoff; it does not make the task complete. Reconcile records and
checklist at intake, dispatch, progress, blockage, deferral, cancellation and
completion, and before status replies, backups and ending work turns.

When migrating an existing Markdown day page, save its exact bytes as a same-day
history artifact, link it from the new page and check links before retiring it.
Re-read the current page before replacement to preserve concurrent edits.

## Track goals and back up

Use `get_goal` before creating a native goal; do not replace an unfinished goal.
When authorized by the applicable instructions and supported by the runtime,
create a goal for the outcomes in the checklist and linked records. Keep changing
scope in those records; `update_goal` changes status. Honor user pauses and the
runtime's budget/blocker rules. If the tool is unavailable, retain the work in
records and report the limitation rather than inventing a running goal.

After meaningful progress and before ending work turns, commit and push daily
records to the authenticated user's private daily repository, creating it if
missing. This standing backup instruction does not authorize publishing other
projects. Verify owner and private visibility first, inspect the payload, preserve
history and never force-push. Exclude secrets and temporary runtime files; captured
message bodies, archives, review state and drafts remain outside Git.

Verify the remote SHA matches the local backup commit. Record failures and
exclusions while continuing independent work. Linked external files and ignored
files are not backed up by a link alone. For recovery, clone into a separate
directory, verify the saved commit and restore only needed files without
replacing newer work. Reconcile instruction versions before installing them.

## Deliver artifacts

Unless the user requests prose or another format, have workers make useful
visuals for substantive explanations, even from available evidence. Use the
simplest form that helps; prefer self-contained HTML/SVG when suitable, and Manim
when animation is requested or useful. Verify rendering and controls. Keep source
and limitations linked, with a clickable local artifact link and a supported
preview where available. In voice, give the short outcome without reading paths.
Workers revise their own sources; collect the verified final versions.
