import logging
import os
import sys
import time
import json
from http import HTTPStatus
from logging import Formatter, StreamHandler
from exceptions import Not200Error, DictEmpty, RequestExceptionError, UndocumentedStatusError, NotDict
import requests
import telegram
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(Formatter(fmt='%(asctime)s, %(levelname)s, %(message)s, '
                                   '%(name)s'))
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляем сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as error:
        logger.critical(error)
    info_message = f'Сообщение со статусом "{message}" успешно отправлено'
    logger.info(info_message)


def get_api_answer(current_timestamp):
    """Получаем ответ от API Practicum и проверяем, что API доступно."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            message = 'Что-то не так с API Practicum (ответ сервера не 200)'
            logger.error(message)
            raise Not200Error(message)
        return response.json()
    except requests.exceptions.RequestException as error:
        logger.critical(error)
        raise RequestExceptionError(error)
    except json.decoder.JSONDecodeError as error:
        logger.error(error)
        raise json.JSONDecodeError(error)


def check_response(response):
    """Проверяем ответ от API: все ключи приходят, известен ли нам статус."""
    if not isinstance(response, dict):
        message = 'Ответ API не словарь'
        logger.error(message)
        raise NotDict(message)
    if response.get('homeworks') is None:
        message = 'Нет ожидаемых ключей в ответе от Practicum'
        logger.error(message)
        raise DictEmpty(message)
    status = response['homeworks'][0].get('status')
    if status not in HOMEWORK_STATUSES:
        message = 'Статус домашней работы неизвестен боту'
        logger.error(message)
        raise UndocumentedStatusError(message)
    return response['homeworks'][0]


def parse_status(homework):
    """Проверяем статус работы и готовим сообщение об изменении статуса."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        message = 'Значение "homework_name" пустое'
        logger.error(message)
        raise UndocumentedStatusError(message)
    if homework_status is None:
        message = 'Значение "status" пустое'
        logger.error(message)
        raise UndocumentedStatusError(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{ homework_name }". { verdict }'


def check_tokens():
    """Проверяем, что все обязательные переменные окружения настроены."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        message = 'Все обязательные переменные окружения настроены'
        logger.info(message)
        return True
    else:
        if not PRACTICUM_TOKEN:
            message = 'Отсутствует обязательная переменная окружения:'\
                      '"PRACTICUM_TOKEN" Программа принудительно остановлена.'
            logger.critical(message)
        if not TELEGRAM_TOKEN:
            message = 'Отсутствует обязательная переменная окружения:'\
                      '"TELEGRAM_TOKEN" Программа принудительно остановлена.'
            logger.critical(message)
        if not TELEGRAM_CHAT_ID:
            message = 'Отсутствует обязательная переменная окружения:'\
                      '"TELEGRAM_CHAT_ID" Программа принудительно остановлена.'
            logger.critical(message)
        return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    check_status = 'reviewing'
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework and check_status != homework['status']:
                message = parse_status(homework)
                send_message(bot, message)
                check_status = homework['status']
                message = 'Проверка обновлений успешно завершена'
                logger.info(message)
            else:
                message = 'Обновлений не было'
                logger.debug(message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
