from dataclasses import dataclass, field


@dataclass
class TocEntry:
    """One heading in the table of contents, at its absolute heading level."""

    level: int
    anchor: str
    label: str


@dataclass
class _Node:
    entry: TocEntry | None
    children: list["_Node"] = field(default_factory=list)


def flatten_tokens(tokens: list[dict]) -> list[TocEntry]:
    """Flatten Python-Markdown ``toc_tokens`` into entries in document order.

    ``label`` is the token's ``name``, which Python-Markdown has already
    HTML-escaped, so it is safe to place in markup as-is.
    """
    entries: list[TocEntry] = []
    for token in tokens:
        entries.append(TocEntry(token["level"], token["id"], token["name"]))
        entries.extend(flatten_tokens(token["children"]))
    return entries


def build_toc(entries: list[TocEntry]) -> str:
    """Render entries from all files as one nested <ul>, nested by heading level.

    Nesting follows the absolute heading level, so an H2 always sits one
    level below the top whatever file it came from. An H2 with no H1 before
    it is placed in an unlabelled top-level item rather than promoted.
    """
    root = _Node(None)
    stack: list[_Node] = []  # stack[d] is the open node at heading level d + 1
    for entry in entries:
        del stack[entry.level - 1 :]
        while len(stack) < entry.level - 1:
            placeholder = _Node(None)
            (stack[-1] if stack else root).children.append(placeholder)
            stack.append(placeholder)
        node = _Node(entry)
        (stack[-1] if stack else root).children.append(node)
        stack.append(node)

    def render(nodes: list[_Node]) -> str:
        items = []
        for node in nodes:
            link = (
                f'<a href="#{node.entry.anchor}">{node.entry.label}</a>'
                if node.entry
                else ""
            )
            nested = render(node.children) if node.children else ""
            items.append(f"<li>{link}{nested}</li>")
        return "<ul>\n" + "\n".join(items) + "\n</ul>"

    return render(root.children) if root.children else ""
