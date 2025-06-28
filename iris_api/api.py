import requests
from typing import Callable, Optional, List, Union, Any
import logging
import time
import typing

from .models import Balance, HistoryEntry
from .exceptions import (
    IrisAPIError,
    AuthorizationError,
    RateLimitError,
    InvalidRequestError,
    NotEnoughSweetsError,
    TransactionNotFoundError,
)

logger = logging.getLogger(__name__)


class IrisAPIClient:
    """
    Синхронный клиент для работы с API IRIS-TG

    Args:
        bot_id (str): ID бота в системе IRIS-TG
        iris_token (str): Токен авторизации
        base_url (Optional[str]): Базовый URL API (по умолчанию 'https://iris-tg.ru/api')
        timeout (Optional[int]): Таймаут запросов в секундах (по умолчанию 10)
    """

    BASE_URL = "https://iris-tg.ru/api"
    DEFAULT_TIMEOUT = 10
    RECONNECT_DELAY = 5

    def __init__(
        self,
        bot_id: str,
        iris_token: str,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.bot_id = bot_id
        self.iris_token = iris_token
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": f"IrisAPIClient/{self.bot_id}"}
        )
        self._last_id = 0

    def _make_request(
        self, method: str, params: Optional[dict[str, Any]] = None
    ) -> Any:
        """
        Базовый метод для выполнения запросов к API

        Args:
            method (str): Метод API (например 'balance')
            params (Optional[dict]): Параметры запроса

        Returns:
            dict: Ответ API

        Raises:
            AuthorizationError: При ошибках авторизации
            RateLimitError: При превышении лимита запросов
            InvalidRequestError: При неверных параметрах запроса
            IrisAPIError: При других ошибках API
        """
        url = f"{self.base_url}/{self.bot_id}_{self.iris_token}/{method}"

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 401:
                raise AuthorizationError("Invalid credentials")
            elif response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            elif response.status_code == 400:
                raise InvalidRequestError("Invalid request parameters")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise IrisAPIError(f"Network error: {str(e)}")

    def get_balance(self) -> Balance:
        """
        Получает текущий баланс бота

        Returns:
            Balance: Объект с информацией о балансе

        Example:
            >>> balance = api.get_balance()
            >>> print(balance.sweets)
        """
        data = self._make_request("balance")
        data = typing.cast(dict[str, Any], data)
        return Balance(sweets=data["sweets"], donate_score=data["donate_score"])

    def give_sweets(
        self, sweets: Union[int, float], user_id: Union[int, str], comment: str = ""
    ) -> bool:
        """
        Отправляет конфеты пользователю

        Args:
            sweets (Union[int, float]): Количество конфет для отправки
            user_id (Union[int, str]): ID пользователя-получателя
            comment (str): Комментарий к переводу

        Returns:
            bool: True если перевод успешен

        Raises:
            NotEnoughSweetsError: Если недостаточно конфет
            IrisAPIError: При других ошибках

        Example:
            >>> try:
            >>>     api.give_sweets(10, 123456789, "Награда")
            >>> except NotEnoughSweetsError as e:
            >>>     print(f"Ошибка: {e}")
        """
        params: dict[str, Any] = {
            "sweets": sweets,
            "user_id": user_id,
            "comment": comment,
        }
        response = self._make_request("give_sweets", params)
        response = typing.cast(dict[str, Any], response)
        if response.get("result") == "ok":
            return True
        if "error" in response:
            error = typing.cast(dict[str, Any], response["error"])
            if error.get("code") == 0 and "Not enough sweets" in error.get(
                "description", ""
            ):
                raise NotEnoughSweetsError(required=sweets)
        raise IrisAPIError(f"Transfer failed: {response}")

    def get_history(
        self,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        user_id: Optional[int] = None,
        transaction_type: Optional[str] = None,
    ) -> List[HistoryEntry]:
        """
        Получает историю транзакций с возможностью фильтрации

        Args:
            offset (Optional[int]): Смещение для пагинации
            limit (Optional[int]): Лимит записей
            user_id (Optional[int]): Фильтр по ID пользователя
            transaction_type (Optional[str]): Фильтр по типу ("give" или "take")

        Returns:
            List[HistoryEntry]: Список транзакций

        Example:
            >>> history = api.get_history(limit=10)
            >>> for tx in history:
            >>>     print(tx.amount)
        """
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        if user_id is not None:
            params["user_id"] = user_id
        if transaction_type is not None:
            params["type"] = transaction_type
        data = self._make_request("history", params)
        data = typing.cast(list[dict[str, Any]], data)
        return [HistoryEntry(**item) for item in data]

    def get_transaction(self, transaction_id: int) -> HistoryEntry:
        """
        Получает информацию о конкретной транзакции

        Args:
            transaction_id (int): ID транзакции

        Returns:
            HistoryEntry: Информация о транзакции

        Raises:
            TransactionNotFoundError: Если транзакция не найдена

        Example:
            >>> try:
            >>>     tx = api.get_transaction(123456)
            >>> except TransactionNotFoundError:
            >>>     print("Транзакция не найдена")
        """
        history = self.get_history()
        for entry in history:
            if entry.id == transaction_id:
                return entry
        raise TransactionNotFoundError(f"Transaction {transaction_id} not found")

    def track_transactions(
        self,
        callback: Callable[[HistoryEntry], None],
        poll_interval: float = 1.0,
        initial_offset: Optional[int] = None,
    ):
        """
        Отслеживает новые транзакции

        Args:
            callback (Callable[[HistoryEntry], None]): Функция для обработки новых транзакций
            poll_interval (float): Интервал опроса в секундах (по умолчанию 1.0)
            initial_offset (Optional[int]): Начальное смещение (если None, начинает с последней)

        Example:
            >>> def handle_tx(tx):
            >>>     print(f"Новая транзакция: {tx.id}")
            >>>
            >>> api.track_transactions(handle_tx)
        """
        if initial_offset is not None:
            self._last_id = initial_offset
        else:
            last_tx = self.get_history(limit=1)
            self._last_id = last_tx[0].id if last_tx else 0

        while True:
            try:
                new_transactions = self.get_history(offset=self._last_id + 1)

                if new_transactions:
                    for tx in new_transactions:
                        callback(tx)
                        self._last_id = tx.id
                else:
                    time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Tracking error: {e}")
                time.sleep(self.RECONNECT_DELAY)
