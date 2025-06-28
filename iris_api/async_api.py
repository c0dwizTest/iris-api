import asyncio
import logging
from typing import Any, Callable, List, Optional, Type, Union
import typing

import aiohttp

from .exceptions import (
    AuthorizationError,
    InvalidRequestError,
    IrisAPIError,
    NotEnoughSweetsError,
    RateLimitError,
    TransactionNotFoundError,
)
from .models import Balance, HistoryEntry

logger = logging.getLogger(__name__)


class AsyncIrisAPIClient:
    """
    Асинхронный клиент для работы с API IRIS-TG

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
        self.session = None
        self._last_id = 0

    async def __aenter__(self):
        """Контекстный менеджер для автоматического подключения"""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        """Контекстный менеджер для автоматического закрытия"""
        await self.close()

    async def connect(self):
        """Устанавливает соединение с API"""
        self.session = aiohttp.ClientSession(
            headers={
                "Accept": "application/json",
                "User-Agent": f"AsyncIrisAPIClient/{self.bot_id}",
            },
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        )

    async def close(self):
        """Закрывает соединение с API"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _make_request(
        self, method: str, params: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
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
            if self.session is None:
                raise IrisAPIError("Session is not initialized. Call connect() first.")
            async with self.session.get(url, params=params) as response:
                if response.status == 401:
                    raise AuthorizationError("Invalid credentials")
                elif response.status == 429:
                    raise RateLimitError("Rate limit exceeded")
                elif response.status == 400:
                    raise InvalidRequestError("Invalid request parameters")

                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as e:
            raise IrisAPIError(f"Network error: {str(e)}")

    async def get_balance(self) -> Balance:
        """
        Получает текущий баланс бота

        Returns:
            Balance: Объект с информацией о балансе

        Example:
            >>> balance = await api.get_balance()
            >>> print(balance.sweets)
        """
        data = await self._make_request("balance")
        return Balance(sweets=data["sweets"], donate_score=data["donate_score"])

    async def give_sweets(
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
            >>>     await api.give_sweets(10, 123456789, "Награда")
            >>> except NotEnoughSweetsError as e:
            >>>     print(f"Ошибка: {e}")
        """
        params = {"sweets": sweets, "user_id": user_id, "comment": comment}  # type: ignore

        response = await self._make_request("give_sweets", params)  # type: ignore

        if response.get("result") == "ok":
            return True

        if "error" in response:
            error = response["error"]
            if error.get("code") == 0 and "Not enough sweets" in error.get(
                "description", ""
            ):
                raise NotEnoughSweetsError(required=sweets)

        raise IrisAPIError(f"Transfer failed: {response}")

    async def get_history(
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
            >>> history = await api.get_history(limit=10)
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

    async def get_transaction(self, transaction_id: int) -> HistoryEntry:
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
            >>>     tx = await api.get_transaction(123456)
            >>> except TransactionNotFoundError:
            >>>     print("Транзакция не найдена")
        """
        history = await self.get_history()
        for entry in history:
            if entry.id == transaction_id:
                return entry
        raise TransactionNotFoundError(f"Transaction {transaction_id} not found")

    async def track_transactions(
        self,
        callback: Callable[[HistoryEntry], None],
        poll_interval: float = 1.0,
        initial_offset: Optional[int] = None,
    ):
        """
        Отслеживает новые транзакции в реальном времени

        Args:
            callback (Callable[[HistoryEntry], None]): Функция для обработки новых транзакций
            poll_interval (float): Интервал опроса в секундах (по умолчанию 1.0)
            initial_offset (Optional[int]): Начальное смещение (если None, начинает с последней)

        Example:
            >>> async def handle_tx(tx):
            >>>     print(f"Новая транзакция: {tx.id}")
            >>>
            >>> await api.track_transactions(handle_tx)
        """
        import inspect

        if initial_offset is not None:
            self._last_id = initial_offset
        else:
            last_tx = await self.get_history(limit=1)
            self._last_id = last_tx[0].id if last_tx else 0

        while True:
            try:
                new_transactions = await self.get_history(offset=self._last_id + 1)

                if new_transactions:
                    for tx in new_transactions:
                        if inspect.iscoroutinefunction(callback):
                            await callback(tx)
                        else:
                            callback(tx)
                        self._last_id = tx.id
                else:
                    await asyncio.sleep(poll_interval)

            except asyncio.CancelledError:
                logger.info("Transaction tracking stopped")
                break
            except Exception as e:
                logger.error(f"Tracking error: {e}")
                await asyncio.sleep(self.RECONNECT_DELAY)
