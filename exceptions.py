class UnexpectedStatusError(Exception):
    """Неожиданный статус."""


class NoVariablesError(Exception):
    """Проверьте переменные окружения."""


class EmptyResponseAPIError(Exception):
    """Пустой ответ."""


class WrongAddressError(Exception):
    """Неправильный адрес."""