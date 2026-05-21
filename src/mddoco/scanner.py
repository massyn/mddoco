from pathlib import Path

_ACCEPTED_SUFFIXES = {".md", ".j2"}


def find_markdown_files(input_path: Path) -> list[Path]:
    """Return markdown files to process, sorted by path.

    Accepts *.md and *.md.j2 files; skips any whose name starts with '_'.
    If input_path is a file, it must be .md or .md.j2.
    If input_path is a directory, both file types are found recursively and
    sorted together so numeric prefixes (01_, 02_, …) determine sequence.
    """
    if input_path.is_file():
        if input_path.suffix.lower() not in _ACCEPTED_SUFFIXES:
            raise ValueError(f"File must be a .md or .md.j2 file: {input_path}")
        return [input_path]

    if input_path.is_dir():
        md = [p for p in input_path.rglob("*.md") if not p.name.startswith("_")]
        j2 = [p for p in input_path.rglob("*.md.j2") if not p.name.startswith("_")]
        files = sorted(md + j2)
        if not files:
            raise FileNotFoundError(f"No markdown files found in: {input_path}")
        return files

    raise ValueError(f"Input path does not exist: {input_path}")
