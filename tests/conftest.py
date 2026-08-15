"""
tests/conftest.py
------------------
Центральный файл фикстур pytest для AI_Website_Framework.
Предоставляет базовое окружение, временные пути и mock-объекты.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Generator, Dict, List, Any, Optional

import pytest

from ai_framework.validation.validators.base import Validator


class MockValidator(Validator):
    """
    Mock-валидатор, строго реализующий контракт Validator:
    validate(field, value, payload, context)
    """

    def __init__(
        self, should_pass: bool = True, error_msg: str = "validation.mock_error"
    ):
        print("\n>>> MOCK VALIDATOR INITIALIZED <<<")
        self.should_pass = should_pass
        self.error_msg = error_msg

    async def validate(
        self,
        field: str,
        value: Any,
        payload: Dict[str, Any],
        context: Any = None,
    ) -> Optional[Dict[str, Any]]:
        print(f"\n>>> MockValidator.validate CALLED for field: '{field}' <<<")
        if self.should_pass:
            return None
        return {
            "field": field,
            "message_key": self.error_msg,
            "params": {},
        }


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Возвращает корневой путь проекта."""
    return Path(__file__).parent.parent


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Предоставляет временную директорию для тестов с последующей очисткой."""
    tmp_path = Path(tempfile.mkdtemp(prefix="ai_framework_test_"))
    yield tmp_path
    if tmp_path.exists():
        shutil.rmtree(tmp_path)


@pytest.fixture
def mock_valid_payload() -> Dict[str, Any]:
    """Возвращает валидный payload для тестов."""
    return {
        "html_content": "<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello</h1></body></html>",
        "status": "success",
    }


@pytest.fixture
def mock_invalid_payload() -> Dict[str, Any]:
    """Возвращает невалидный payload для негативных тестов."""
    return {
        "html_content": "<html><body><h1>Unclosed tag",
        "status": "error",
    }


@pytest.fixture
def passing_rules() -> Dict[str, List[Any]]:
    """Правила валидации, которые всегда проходят успешно."""
    return {"html_content": [MockValidator(should_pass=True)]}


@pytest.fixture
def failing_rules() -> Dict[str, List[Any]]:
    """Правила валидации, которые гарантированно возвращают ошибку."""
    return {
        "html_content": [
            MockValidator(should_pass=False, error_msg="validation.mock_error")
        ]
    }
