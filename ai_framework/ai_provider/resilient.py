"""
Resilient AI Provider Wrapper (Stage 3.3).
Provides exponential backoff retries, symmetric fallback execution, and request-level timeout overrides.
"""

from dataclasses import replace
import time

from ai_framework.ai_provider.contracts import (
    AIError,
    AIProviderProtocol,
    AIRequest,
    AIResponse,
)


class ResilientProvider(AIProviderProtocol):
    """Декоратор для обеспечения отказоустойчивости AI-провайдеров."""

    def __init__(
        self,
        primary: AIProviderProtocol,
        fallback: AIProviderProtocol | None = None,
        max_retries: int = 3,
        timeout: float | None = None,
        backoff_factor: float = 0.0,
    ) -> None:
        if max_retries < 1:
            raise ValueError("max_retries должен быть больше или равен 1.")

        self.primary = primary
        self.fallback = fallback
        self.max_retries = max_retries
        self.timeout = timeout
        self.backoff_factor = backoff_factor

    def generate(self, request: AIRequest) -> AIResponse:
        """
        Резолвит таймаут и выполняет цепочку генерации (Primary -> Retry -> Fallback -> Retry).
        Фатальные ошибки (ValueError, TypeError и др.) пробрасываются мгновенно.
        """
        effective_timeout = (
            request.timeout if request.timeout is not None else self.timeout
        )
        req = replace(request, timeout=effective_timeout)

        # 1. Попытка выполнения Primary с повторами
        try:
            return self._execute_with_retry(self.primary, req)
        except AIError as primary_err:
            # 2. Переключение на Fallback с повторами, если Primary исчерпал попытки
            if self.fallback is not None:
                try:
                    return self._execute_with_retry(self.fallback, req)
                except AIError as fallback_err:
                    raise fallback_err from primary_err
            raise primary_err

    def _execute_with_retry(
        self, provider: AIProviderProtocol, request: AIRequest
    ) -> AIResponse:
        last_error: AIError | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return provider.generate(request)
            except (AIError, TimeoutError) as err:
                if isinstance(err, TimeoutError):
                    last_error = AIError(f"Request timed out: {err}")
                else:
                    last_error = err

                if attempt < self.max_retries:
                    if self.backoff_factor > 0:
                        sleep_time = self.backoff_factor * (2 ** (attempt - 1))
                        time.sleep(sleep_time)

        if last_error is not None:
            raise last_error
        raise AIError("Неизвестная ошибка при выполнении запроса.")
