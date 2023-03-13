class TokenEmpty(Exception):
    """Исключение при неправильном токене."""
    pass


class SendMessageError(Exception):
    """Ошибка отправки сообщения ботом."""
    pass


class EndpointError(Exception):
    """Исключение если endpoint не доступен."""
    pass


class UndefinedStatus(Exception):
    """
    Исключение при не задокументированном статусе.
    """
    pass
