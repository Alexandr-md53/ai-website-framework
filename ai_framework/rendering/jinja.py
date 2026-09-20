from __future__ import annotations
import pathlib
from typing import Dict


class JinjaTemplateRenderer:
    """
    Framework-level Jinja implementation of TemplateRendererProtocol.
    Generic — knows only templates_dir + template_name + context, no domain semantics.
    """

    def __init__(self, templates_dir: pathlib.Path | str | None = None):
        if templates_dir is None:
            # generic fallback, caller should pass explicit dir
            templates_dir = pathlib.Path("templates")
        self.templates_dir = pathlib.Path(templates_dir)

        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape

            self._env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                autoescape=select_autoescape(["html", "xml"]),
                auto_reload=False,
            )
            self._available = True
        except Exception:
            self._env = None
            self._available = False

    def render(self, template_name: str, context: Dict) -> str:
        if not self._available or self._env is None:
            raise RuntimeError(
                f"Jinja not available or templates_dir missing: {self.templates_dir}"
            )
        tmpl = self._env.get_template(template_name)
        return tmpl.render(**context)
