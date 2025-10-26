import pytest
from backend.app.utils import (
    sanitize_filename,
    generate_unique_filename,
    extract_coub_id,
    format_file_size
)


class TestSanitizeFilename:
    """Тесты очистки имени файла"""
    
    def test_sanitize_normal_filename(self):
        """Тест нормального имени файла"""
        result = sanitize_filename("video.mp4")
        assert result == "video.mp4"
    
    def test_sanitize_filename_with_spaces(self):
        """Тест имени с пробелами"""
        result = sanitize_filename("my video file.mp4")
        assert result == "my video file.mp4"
    
    def test_sanitize_filename_with_special_chars(self):
        """Тест имени со специальными символами"""
        result = sanitize_filename("video@#$%.mp4")
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result
        assert "%" not in result
    
    def test_sanitize_filename_with_path_traversal(self):
        """Тест защиты от path traversal"""
        result = sanitize_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        assert "\\" not in result
    
    def test_sanitize_filename_with_slashes(self):
        """Тест удаления слешей"""
        result = sanitize_filename("folder/video.mp4")
        assert "/" not in result
    
    def test_sanitize_empty_filename(self):
        """Тест пустого имени файла"""
        result = sanitize_filename("")
        assert result == "download"
    
    def test_sanitize_filename_max_length(self):
        """Тест ограничения длины"""
        long_name = "a" * 300 + ".mp4"
        result = sanitize_filename(long_name, max_length=50)
        assert len(result) <= 50 + 4  # +4 для .mp4
    
    def test_sanitize_filename_cyrillic(self):
        """Тест кириллических символов"""
        result = sanitize_filename("Видео_файл.mp4")
        assert "Видео" in result or "download" in result


class TestGenerateUniqueFilename:
    """Тесты генерации уникальных имён"""
    
    def test_generate_unique_filename_format(self):
        """Тест формата уникального имени"""
        result = generate_unique_filename("video.mp4")
        assert result.endswith("_video.mp4")
        assert len(result.split("_")[0]) == 8  # UUID префикс
    
    def test_generate_unique_filename_different(self):
        """Тест что генерируются разные имена"""
        result1 = generate_unique_filename("video.mp4")
        result2 = generate_unique_filename("video.mp4")
        assert result1 != result2
    
    def test_generate_unique_filename_with_unsafe_chars(self):
        """Тест с опасными символами"""
        result = generate_unique_filename("../../../video.mp4")
        assert ".." not in result
        assert "/" not in result


class TestExtractCoubId:
    """Тесты извлечения Coub ID"""
    
    def test_extract_coub_id_valid(self):
        """Тест извлечения ID из валидного URL"""
        url = "https://coub.com/view/abc123"
        result = extract_coub_id(url)
        assert result == "abc123"
    
    def test_extract_coub_id_with_trailing_slash(self):
        """Тест с завершающим слешем"""
        url = "https://coub.com/view/abc123/"
        result = extract_coub_id(url)
        assert result == "abc123"
    
    def test_extract_coub_id_http(self):
        """Тест с HTTP"""
        url = "http://coub.com/view/xyz789"
        result = extract_coub_id(url)
        assert result == "xyz789"
    
    def test_extract_coub_id_with_hyphen(self):
        """Тест ID с дефисом"""
        url = "https://coub.com/view/test-video-123"
        result = extract_coub_id(url)
        assert result == "test-video-123"
    
    def test_extract_coub_id_invalid_url(self):
        """Тест невалидного URL"""
        url = "https://example.com/video"
        result = extract_coub_id(url)
        assert result is None
    
    def test_extract_coub_id_empty(self):
        """Тест пустой строки"""
        result = extract_coub_id("")
        assert result is None


class TestFormatFileSize:
    """Тесты форматирования размера файла"""
    
    def test_format_bytes(self):
        """Тест форматирования байтов"""
        result = format_file_size(500)
        assert "500" in result
        assert "B" in result
    
    def test_format_kilobytes(self):
        """Тест форматирования килобайтов"""
        result = format_file_size(2048)
        assert "2.0" in result
        assert "KB" in result
    
    def test_format_megabytes(self):
        """Тест форматирования мегабайтов"""
        result = format_file_size(1024 * 1024 * 5)
        assert "5.0" in result
        assert "MB" in result
    
    def test_format_gigabytes(self):
        """Тест форматирования гигабайтов"""
        result = format_file_size(1024 * 1024 * 1024 * 2)
        assert "2.0" in result
        assert "GB" in result
    
    def test_format_zero(self):
        """Тест нулевого размера"""
        result = format_file_size(0)
        assert "0.0" in result
        assert "B" in result
