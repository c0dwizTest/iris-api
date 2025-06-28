from typing import Optional


class IrisAPIError(Exception):
    """Базовый класс для всех ошибок API"""

    pass


class AuthorizationError(IrisAPIError):
    """Ошибка авторизации (неверные учетные данные)"""

    pass


class RateLimitError(IrisAPIError):
    """Превышен лимит запросов к API"""

    pass


class InvalidRequestError(IrisAPIError):
    """Некорректные параметры запроса"""

    pass


class NotEnoughSweetsError(IrisAPIError):
    """Недостаточно конфет для выполнения операции"""

    def __init__(self, required: float, available: Optional[float] = None):
        """
        Args:
            required (float): Требуемое количество конфет
            available (Optional[float]): Доступное количество конфет
        """
        self.required = required
        self.available = available
        message = f"Недостаточно конфет. Требуется: {required}"
        if available is not None:
            message += f", доступно: {available}"
        super().__init__(message)


class TransactionNotFoundError(IrisAPIError):
    """Транзакция не найдена"""

    pass
