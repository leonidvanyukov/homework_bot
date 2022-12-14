import json
import logging
import os
import sys
import time
from http import HTTPStatus
from logging import Formatter, StreamHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (DictEmpty, MainError, Not200Error, NotList,
                        RequestExceptionError, TelegramError, ApiKeyError)

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
        raise TelegramError(error)
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
    try:
        homeworks_list = response['homeworks']
    except KeyError as error:
        message = f'Ошибка доступа по ключу homeworks: {error}'
        logger.error(message)
        raise DictEmpty(message)
    if homeworks_list is None:
        message = 'В ответе API нет домашних работ'
        logger.error(message)
        raise DictEmpty(message)
    if not isinstance(homeworks_list, list):
        message = 'Ответ API представлен не списком'
        logger.error(message)
        raise NotList(message)
    if homeworks_list:
        homeworks_status = homeworks_list[0].get('status')
        if homeworks_status not in HOMEWORK_STATUSES:
            message = 'Неизвестный статус домашней работы'
            logger.error(message)
    return homeworks_list


def parse_status(homework):
    """Проверяем статус работы и готовим сообщение об изменении статуса."""
    if 'homework_name' not in homework:
        message = 'В ответе API отсутствует ключ homework_name'
        logger.error(message)
        raise ApiKeyError(message)
    if 'status' not in homework:
        message = 'В ответе API отсутствует ключ status'
        logger.error(message)
        raise ApiKeyError(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        message = f'Статус работы отсутствует в списке: {homework_status} '
        logger.error(message)
        raise ApiKeyError(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем, что все обязательные переменные окружения настроены."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        message = 'Все обязательные переменные окружения настроены'
        logger.info(message)
        return True
    else:
        if not PRACTICUM_TOKEN:
            message = ('Отсутствует обязательная переменная окружения: '
                       '"PRACTICUM_TOKEN" Программа принудительно '
                       'остановлена.')
            logger.critical(message)
        if not TELEGRAM_TOKEN:
            message = ('Отсутствует обязательная переменная окружения: '
                       '"TELEGRAM_TOKEN" Программа принудительно остановлена.')
            logger.critical(message)
        if not TELEGRAM_CHAT_ID:
            message = ('Отсутствует обязательная переменная окружения: '
                       '"TELEGRAM_CHAT_ID" Программа принудительно '
                       'остановлена.')
            logger.critical(message)
        return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    check_status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework_list = check_response(response)
            if homework_list and check_status != homework_list[0]['status']:
                message = parse_status(homework_list[0])
                send_message(bot, message)
                check_status = homework_list[0]['status']
                message = 'Проверка обновлений успешно завершена'
                logger.info(message)
            else:
                message = 'Обновлений не было'
                logger.info(message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)
            raise MainError(message)


if __name__ == '__main__':
    main()
