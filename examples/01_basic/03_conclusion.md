# Underscore Files Are Ignored

Any file whose name starts with an underscore is skipped during scanning. This
folder contains `_notes.md`, but its contents never appear in the rendered
output — check for yourself.

Use underscore-prefixed files for drafts, working notes, or Jinja2 macro
libraries that should be importable but not rendered as their own section (see
`examples/04_jinja_data`).
