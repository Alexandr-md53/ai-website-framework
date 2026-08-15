"""
Content Pipeline & Orchestrator for AI Website Framework.
"""

from typing import Dict, Any, List, Optional

from framework.generators.base import BaseGenerator
from framework.core.registry import PluginRegistry
from framework.metadata.payload import PublicationPayload
from framework.core.exceptions import FrameworkError


class ContentPipeline:
    """
    Главный оркестратор (конвейер) сквозного процесса:
    Генерация (BaseGenerator) -> Валидация (PublicationPayload) -> Публикация (Plugins).
    """

    def __init__(self, registry: Optional[PluginRegistry] = None):
        self.registry = registry or PluginRegistry()

    def run(
        self,
        generator: BaseGenerator,
        context: Dict[str, Any],
        target_plugins: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Запускает полный цикл: генерирует контент и рассылает по целевым плагинам.
        """
        # 1. Запуск генератора контента
        payload: PublicationPayload = generator.generate(context)

        results = {"payload": payload.to_dict(), "publications": {}}

        # 2. Если плагины не указаны — просто возвращаем сгенерированный payload
        if not target_plugins:
            return results

        # 3. Публикация через указанные плагины
        for plugin_name in target_plugins:
            try:
                plugin = self.registry.get_plugin(plugin_name)
                success = plugin.publish(payload.to_dict())
                results["publications"][plugin_name] = {
                    "status": "success" if success else "failed",
                    "error": None,
                }
            except Exception as err:
                results["publications"][plugin_name] = {
                    "status": "error",
                    "error": str(err),
                }

        return results
