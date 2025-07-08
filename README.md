
# TON Portfolio Bot 🧾

Telegram-бот + mini-app для просмотра баланса TON, проверки NFT и статуса адресов.

## 🚀 Возможности
- Подключение кошелька через TON Connect mini-app
- Проверка баланса TON
- Поиск NFT в кошельке
- Скам-чек через TonAPI
- Whale-алерты по крупным транзакциям

## 🔧 Структура проекта

```
ton-portfolio-bot/
├── main.py
├── mini-app/
│   ├── index.html
│   └── manifest.json
├── requirements.txt
└── README.md
```

## 🛠️ Установка зависимостей

```bash
pip install python-telegram-bot requests nest_asyncio
```

## 🧠 Запуск

1. Укажите `BOT_TOKEN` и `TONAPI_KEY` в main.py
2. Запустите файл:

```bash
python main.py
```

3. Перейдите в Telegram → найдите вашего бота → нажмите «Подключить кошелёк»

## 💰 Грант
Проект подаётся на грант STON.fi и других TON-программ. Построен индивидуально с телефона на Python.

