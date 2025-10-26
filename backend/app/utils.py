import re
import uuid
from pathlib import Path
from typing import Optional


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Очистка имени файла от опасных символов.

    Args:
        filename: Исходное имя файла
        max_length: Максимальная длина имени

    Returns:
        Безопасное имя файла
    """
    # Удалить расширение
    stem = Path(filename).stem
    ext = Path(filename).suffix

    # Удалить все кроме букв, цифр, пробелов, дефисов и подчёркиваний
    stem = re.sub(r'[^\w\s-]', '', stem)

    # Заменить множественные пробелы на один
    stem = re.sub(r'\s+', ' ', stem)

    # Удалить path traversal попытки
    stem = stem.replace('..', '').replace('/', '').replace('\\', '')

    # Обрезать до максимальной длины
    stem = stem[:max_length].strip()

    # Если имя пустое после очистки
    if not stem:
        stem = "download"

    return f"{stem}{ext}"


def generate_unique_filename(original_filename: str) -> str:
    """
    Генерация уникального имени файла с UUID префиксом.

    Args:
        original_filename: Исходное имя файла

    Returns:
        Уникальное имя файла
    """
    safe_name = sanitize_filename(original_filename)
    unique_id = str(uuid.uuid4())[:8]
    stem = Path(safe_name).stem
    ext = Path(safe_name).suffix
    return f"{unique_id}_{stem}{ext}"


def extract_coub_id(url: str) -> Optional[str]:
    """
    Извлечение ID Coub из URL.

    Args:
        url: URL Coub видео

    Returns:
        ID видео или None
    """
    pattern = r'coub\.com/view/([\w-]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else None


def format_file_size(size_bytes: int) -> str:
    """
    Форматирование размера файла в человекочитаемый формат.

    Args:
        size_bytes: Размер в байтах

    Returns:
        Отформатированная строка (например, "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
