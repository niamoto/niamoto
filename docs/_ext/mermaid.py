from __future__ import annotations

from docutils import nodes
from docutils.parsers.rst import Directive


class MermaidDirective(Directive):
    has_content = True

    def run(self):
        if not self.content:
            return []
        content = "\n".join(self.content)
        html = f'<div class="mermaid">{content}</div>'
        node = nodes.raw("", html, format="html")
        return [node]


def setup(app):
    app.add_directive("mermaid", MermaidDirective)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
