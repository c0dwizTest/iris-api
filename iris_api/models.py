from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Balance:
    """
    Модель баланса бота

    Attributes:
        sweets (float): Основной баланс конфет
        donate_score (float): Донат-счет
        available (Optional[float]): Доступный баланс (по умолчанию равен sweets)
    """

    sweets: float
    donate_score: float
    available: Optional[float] = None

    def __post_init__(self):
        """Инициализирует available, если не указан"""
        if self.available is None:
            self.available = self.sweets


@dataclass
class TransactionInfo:
    """
    Дополнительная информация о транзакции

    Attributes:
        donateScore (Optional[int]): Количество донат-очков
        sweets (Optional[float]): Количество конфет (для операций give)
        commission (Optional[float]): Комиссия (для операций give)
    """

    donateScore: Optional[int] = None
    sweets: Optional[float] = None
    commission: Optional[float] = None


@dataclass
class HistoryEntry:
    """
    Модель записи истории операций

    Attributes:
        id (int): Уникальный ID транзакции
        date (int): Timestamp операции в миллисекундах
        amount (float): Сумма операции (отрицательная для отправки)
        balance (float): Баланс после операции
        to_user_id (int): ID пользователя
        type (str): Тип операции ("give" или "take")
        info (TransactionInfo): Дополнительная информация

    Properties:
        datetime (datetime): Возвращает datetime объект
    """

    id: int
    date: int
    amount: float
    balance: float
    to_user_id: int
    type: str
    info: TransactionInfo

    @property
    def datetime(self) -> datetime:
        """Конвертирует timestamp в datetime объект"""
        return datetime.fromtimestamp(self.date / 1000)
