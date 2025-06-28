# IRIS-TG API Client

Асинхронный Python клиент для работы с API IRIS-TG

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## Установка

```bash
pip install git+https://github.com/c0dwiztest/iris-api.git
```

## Быстрый старт

### Основное использование

```python
from iris_api import AsyncIrisAPIClient
from iris_api.models import HistoryEntry
import asyncio

async def main():
    async with AsyncIrisAPIClient(bot_id="YOUR_BOT_ID", iris_token="YOUR_IRIS_TOKEN") as api:
        # Получаем баланс
        balance = await api.get_balance()
        print(f"Текущий баланс: {balance.sweets} конфет")

        # Отправляем конфеты
        try:
            success = await api.give_sweets(
                sweets=5.0,
                user_id=123456789,
                comment="Награда"
            )
            print("Конфеты успешно отправлены!")
        except NotEnoughSweetsError as e:
            print(f"Ошибка: {e}")

asyncio.run(main())
```

### Отслеживание транзакций в реальном времени

```python
from iris_api import AsyncIrisAPIClient
import asyncio

async def print_transaction(tx):
    action = "↑ Получено" if tx.amount > 0 else "↓ Отправлено"
    print(f"{tx.datetime} | {action} {abs(tx.amount):.2f} | Баланс: {tx.balance:.2f}")

async def main():
    async with AsyncIrisAPIClient(bot_id="YOUR_BOT_ID", iris_token="YOUR_IRIS_TOKEN") as api:
        print("🚀 Начинаем отслеживание транзакций...")
        try:
            await api.track_transactions(
                callback=print_transaction,
                poll_interval=1.0
            )
        except asyncio.CancelledError:
            print("🛑 Отслеживание остановлено")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nПрограмма остановлена пользователем")
```

## Основные методы

### Получение баланса
```python
balance = await api.get_balance()
print(balance.sweets, balance.donate_score)
```

### Отправка конфет
```python
try:
    await api.give_sweets(
        sweets=10.5,
        user_id=123456789,
        comment="Чаевые"
    )
except NotEnoughSweetsError as e:
    print(f"Недостаточно конфет! Требуется: {e.required}")
```

### Получение истории операций
```python
history = await api.get_history(limit=10)
for tx in history:
    print(f"{tx.datetime}: {tx.type} {tx.amount}")
```

### Отслеживание новых операций
```python
async def handle_transaction(tx):
    print(f"Новая операция: {tx.id}")

await api.track_transactions(
    callback=handle_transaction,
    poll_interval=1.0
)
```

## Лицензия

MIT License. Полный текст лицензии доступен в файле [LICENSE](LICENSE).

## Связь

По вопросам и предложениям:
- Telegram: [@shuseks](https://t.me/shuseks)
- Issues на GitHub

---

**Happy coding!** 🚀