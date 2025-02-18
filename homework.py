import logging
import os
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler
from pathlib import Path

import requests
import telegram

from config import (ENDPOINT, HEADERS, HOMEWORK_VERDICTS, PRACTICUM_TOKEN,
                    RETRY_PERIOD, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN)
from exceptions import EmtyResponseFromAPI, EndpointError

FILE_NAME = Path(__file__).stem

LOG_DIR = os.path.expanduser(f'~\\{FILE_NAME + ".log"}')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


handler = RotatingFileHandler(
    filename=LOG_DIR,
    maxBytes=50000000,
    encoding='utf-8',
    backupCount=3,
)
stream_handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(funcName)s, %(lineno)s',
)

stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка валидности токенов."""
    tokens = (
        (PRACTICUM_TOKEN, 'PRACTICUM_TOKEN'),
        (TELEGRAM_TOKEN, 'TELEGRAM_TOKEN'),
        (TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID'),
    )
    check: bool = True
    for token, name in tokens:
        if not token:
            logger.critical(f'Пустая переменная, - {name}')
            check = False
    return check


def send_message(bot, message):
    """Функция отправки сообщения."""
    logger.debug(f'Отправка сообщения - {message}')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(
            f'{message} успешно отправлено.',
        )
        return True
    except telegram.error.TelegramError as error:
        logger.error(
            f'Сообщение не отпралено, ошибка: {error}',
        )
        return False


def get_api_answer(current_timestamp):
    """Делает запрос к единственному API сервиса."""
    api_answer = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': current_timestamp},
    }
    logger.debug(
        'Запрос к API {url}, {headers} '
        'с параметрами {params}'.format(**api_answer),
    )
    try:
        response = requests.get(
            **api_answer,
        )
        if response.status_code != HTTPStatus.OK:
            raise EndpointError(
                f'API не доступен {response.status_code}, '
                f'{response.json()}, {response.reason}',
            )
        return response.json()
    except requests.RequestException:
        (
            'Ошибка доступа к API: '
            'URL - {url}, '
            'Headers -  {headers}, '
            'params - {params}'.format(**api_answer)
        )


def check_response(responses):
    """Проверка валидности response."""
    logger.debug('Проверка формата')
    if not isinstance(responses, dict):
        raise TypeError('Пустой ответ от API.')
    if 'homeworks' not in responses:
        logger.error('Нет ключа homeworks в response')
        raise EmtyResponseFromAPI('Нет ключа homeworks в response.')
    homeworks = responses.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('response не список')
    return homeworks


def parse_status(homework):
    """Проверяет статус домашней работы."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        if homework_status not in HOMEWORK_VERDICTS:
            raise ValueError(f'{homework_status} нет в документации.')
        verdict = HOMEWORK_VERDICTS[homework_status]
    except KeyError as error:
        raise KeyError(f'Ошибка {error}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise KeyError('Обнаружена пустая переменная.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    current_report = {}
    prev_report = {}
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                current_report['verdict'] = parse_status(homework)
                current_report['name'] = homework['homework_name']
            else:
                current_report['verdict'] = 'Нет новых статусов'
            if current_report != prev_report:
                if send_message(bot, current_report['verdict']):
                    prev_report = current_report.copy()
                    timestamp = response.get(
                        'current_date', timestamp,
                    )
            else:
                logger.debug(
                    'Нет изменений в статусах работ',
                )
        except EmtyResponseFromAPI as error:
            logger.error(f'Ошибка отравки сообщения - {error}')
            (f'Ошибка отправки сообщения - {error}')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            current_report['verdict'] = message
            logger.error(message)
            if current_report != prev_report:
                send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
