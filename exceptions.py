class Not200Error(Exception):
    """Ответ сервера не равен 200."""


class DictEmpty(Exception):
    """Словарь в ответе от API пустой."""


class RequestExceptionError(Exception):
    """Ошибка при запросе к API."""


class NotList(Exception):
    """Ответ от API не содержит список."""


class TelegramError(Exception):
    """Ошибка взаимодействия с Telegram."""


class MainError(Exception):
    """Ошибка в программе."""
