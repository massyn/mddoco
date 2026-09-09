# Files Are Processed In Order

Files are sorted by name before they are merged, so a numeric prefix controls
the sequence:

```
01_introduction.md
02_ordering.md
03_conclusion.md
```

You are reading `02_ordering.md`, and it appears after the introduction because
`02_` sorts after `01_`. Rename the files and the document reorders itself — no
configuration, no index file.
