# Daily checklist validation

[Desktop preview](main.template.preview.png) contains synthetic example tasks only.

Validated with Chromium 145.0.7632.6 on October 4, 2026, using the local HTML file:

- All four `data-status` values produce the expected visible color, text and native checkbox properties. Only completed is checked; only in-progress is indeterminate. Blocked is red, unchecked, not indeterminate, and has a visible reason.
- Actual pointer clicks cannot toggle disabled controls. Reload derives the same state from HTML; no browser storage is used.
- Notes open by mouse and close by keyboard. The checklist remains visible.
- Desktop (1000 px) and mobile (390 px) have no horizontal overflow.
- Tailwind CDN returned HTTP 200. Blocking external requests preserved layout, colors, notes and status initialization.
- With JavaScript disabled, CSS status labels and markers remain visible; the native indeterminate property requires the local script.
- Relative Markdown links were followed in a local synthetic fixture with real task files. Template links are placeholders to replace when creating a day page.

The initial test dispatched a JavaScript click event, which can bypass disabled user-input behavior. It was corrected to use an actual pointer click; no source change was needed for that assertion.

This verifies rendering and deterministic display mapping, not general model compliance. Other browsers, screen readers and production hosting were not tested. GitHub blob pages show HTML source; no Pages deployment is included. Tailwind documents Play CDN for development only.
