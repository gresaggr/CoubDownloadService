"""Пользовательские исключения для приложения"""


class CoubDownloadException(Exception):
    """Базовое исключение для ошибок загрузки"""
    pass


class CoubAPIError(CoubDownloadException):
    """Ошибка при обращении к API Coub"""
    pass


class FileTooLargeError(CoubDownloadException):
    """Файл превышает допустимый размер"""
    pass


class FileNotFoundError(CoubDownloadException):
    """Файл не найден"""
    pass


class InvalidURLError(CoubDownloadException):
    """Некорректный URL"""
    pass


class DownloadError(CoubDownloadException):
    """Ошибка при загрузке файла"""
    pass


class DatabaseError(CoubDownloadException):
    """Ошибка базы данных"""
    pass
