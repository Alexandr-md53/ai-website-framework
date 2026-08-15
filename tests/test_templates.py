"""
Unit tests for Templates Engine.
"""

from framework.templates.engine import TemplateEngine
from framework.metadata.payload import PublicationPayload


def test_render_template_basic():
    template = "Привет, {{ name }}! Тема: {{ topic }}."
    context = {"name": "Разработчик", "topic": "Framework"}
    result = TemplateEngine.render(template, context)
    assert result == "Привет, Разработчик! Тема: Framework."


def test_render_payload():
    template = "Заголовок: {{ title }}\nТекст: {{ text }}"
    payload = PublicationPayload(title="Новость", text="Содержимое новости")
    result = TemplateEngine.render_payload(template, payload)
    assert result == "Заголовок: Новость\nТекст: Содержимое новости"
