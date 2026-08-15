"""
framework/validation/validators/base.py
-----------------------------------------
Базовый абстрактный класс для всех валидаторов фреймворка.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Validator(ABC):
    """
    Абстрактный базовый класс валидатора.
    Все конкретные валидаторы должны наследоваться от него и реализовывать метод validate.
    """

    @abstractmethod
    async def validate(
        self,
        field: str,
        value: Any,
        payload: Dict[str, Any],
        context: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Выполняет валидацию отдельного поля.

        :param field: Имя/путь проверяемого поля.
        :param value: Значение проверяемого поля.
        :param payload: Полный словарь данных (контекст всего запроса/объекта).
        :param context: Дополнительный контекст валидации (например, состояние приложения).
        :return: None, если валидация успешна, или Dict с ключами 'field', 'message_key', 'params'.
        """
        pass
