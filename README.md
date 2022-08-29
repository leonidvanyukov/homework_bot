# Бот для проверки домашней работы Practicum
Бот для Телеграмма работает с Яндекс.Практикум, получает обновления статуса проверки последней домашней работы.<br>

## Переменные для Environment
```bash
PRACTICUM_TOKEN='qwertyqwertyqwertyqwertyqwertyqwertyqwe'
TELEGRAM_TOKEN='1123456789:qwertyqwertyqwertyqwertyqwertyqwert'
TELEGRAM_CHAT_ID='12345678'
```

## Установка скрипта
```bash
$ cd /root/
$ mkdir python_projects
$ cd python_projects
$ git clone https://github.com/leonidvanyukov/homework_bot.git
$ cd homework_bot
$ python3 -m venv venv
$ source venv/bin/activate
(venv)$ pip install -r requirements.txt
$ python homework.py
```

