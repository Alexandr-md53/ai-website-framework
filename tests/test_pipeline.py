"""
Integration tests for Content Pipeline.
"""

from typing import Dict, Any

from framework.generators.base import BaseGenerator
from framework.generators.pipeline import ContentPipeline
from framework.metadata.payload import PublicationPayload
from framework.core.registry import PluginRegistry


# 1. Создаем "заглушку" генератора (чтобы не тратить токены AI в тестах)
class DummyGenerator(BaseGenerator):
    def get_system_prompt(self) -> str:
        return "You are a test assistant."

    def get_user_prompt_template(self) -> str:
        return "Test: {{ topic }}"

    def generate(self, context: Dict[str, Any]) -> PublicationPayload:
        # Сразу возвращаем готовый Payload, имитируя успешную работу AI
        return PublicationPayload(
            id=context.get("id", "test-123"),
            title="Тестовый Заголовок",
            text=f"Сгенерированный текст про {context.get('topic')}",
        )


# 2. Создаем "заглушку" плагина публикации
class DummyPlugin:
    def __init__(self, name="dummy"):
        self.name = name

    def publish(self, payload: Dict[str, Any]) -> bool:
        # Имитируем успешную публикацию
        return True


def test_pipeline_execution():
    """Тестируем сквозной проход данных по конвейеру."""
    # Настраиваем реестр с фейковым плагином
    registry = PluginRegistry()
    registry.register("dummy_plugin", DummyPlugin())

    # Инициализируем конвейер
    pipeline = ContentPipeline(registry=registry)
    generator = DummyGenerator(ai_service=None)  # AI сервис не нужен для заглушки

    # Запускаем конвейер
    context = {"topic": "Интеграция"}
    results = pipeline.run(generator, context, target_plugins=["dummy_plugin"])

    # Проверяем, что оркестратор вернул правильный отчет
    assert "payload" in results
    assert results["payload"]["title"] == "Тестовый Заголовок"
    assert "dummy_plugin" in results["publications"]
    assert results["publications"]["dummy_plugin"]["status"] == "success"
