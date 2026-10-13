"""
Renders an AST dictionary as an indented text tree.

The frontend draws its own interactive tree, but a plain-text version is handy
for the terminal, for screenshots, and for pasting into a lab record.

    Program
    └── Declaration
        ├── Type: int
        ├── Identifier: a
        └── Value
            └── Number: 10
"""

from __future__ import annotations


def render_ast(node: dict | None) -> str:
    """Return the tree as a multi-line string."""
    if node is None:
        return "(no AST produced)"
    lines: list[str] = []
    _render(node, prefix="", is_last=True, is_root=True, lines=lines)
    return "\n".join(lines)


def _label_for(node: dict) -> str:
    label = node.get("label", node.get("node_type", "Node"))
    detail = node.get("detail")
    return f"{label}: {detail}" if detail else label


def _render(node: dict, prefix: str, is_last: bool, is_root: bool, lines: list[str]) -> None:
    if is_root:
        lines.append(_label_for(node))
        child_prefix = ""
    else:
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{_label_for(node)}")
        child_prefix = prefix + ("    " if is_last else "│   ")

    children = node.get("children") or []
    for position, child in enumerate(children):
        _render(child, child_prefix, position == len(children) - 1, False, lines)


def count_nodes(node: dict | None) -> int:
    """Total number of nodes in the tree, used for the statistics panel."""
    if node is None:
        return 0
    return 1 + sum(count_nodes(child) for child in node.get("children") or [])


def tree_depth(node: dict | None) -> int:
    """How many levels deep the tree goes."""
    if node is None:
        return 0
    children = node.get("children") or []
    if not children:
        return 1
    return 1 + max(tree_depth(child) for child in children)
