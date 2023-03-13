import logging
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram

from conf import (ENDPOINT, HEADERS, HOMEWORK_VERDICTS, PRACTICUM_TOKEN,
                  RETRY_PERIOD, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN)
from exceptions import (EndpointError, SendMessageError, TokenEmpty,
                        UndefinedStatus)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = RotatingFileHandler(
    'project_log.log',
    maxBytes=50000000,
    encoding='utf-8'
)
stream_handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')

stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка валидности токенов."""

    tokens = [
        PRACTICUM_TOKEN,
        TELEGRAM_CHAT_ID,
        TELEGRAM_TOKEN
    ]

    if all(tokens):
        logger.debug('Токены валидны')
        return all(tokens)
    else:
        logger.critical(
            'Проверьте введенные данные, пустой токен'
        )
        raise TokenEmpty(
            'Проверьте введенные данные, пустой токен'
        )


def send_message(bot, message):
    """Функция отправки сообщения."""

    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(
            'Сообщение успешно отправлено.'
        )
    except Exception as error:
        logger.error(
            f'Сообщение не отпралено, ошибка: {error}'
        )
        raise SendMessageError(
            f'Сообщение не отправлено, - {error}'
        )


def get_api_answer(current_timestamp):
    """Делает запрос к единственному API сервиса."""

    timestamp = current_timestamp or int(time.time())
    payload = {'from_date': timestamp}

    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        if response.status_code == HTTPStatus.OK.value:
            logger.info(
                'Ответ от API получен.'
            )
            return response.json()
        else:
            raise EndpointError('API недоступен')
    except Exception as error:
        raise EndpointError(error)


def check_response(response):
    """Проверка валидности response."""

    if isinstance(response, dict) and 'homeworks' in response:
        if isinstance(
            response['homeworks'],
            list
        ):
            logger.info(
                'Формат ответа соответсвует ожидаемому'
            )
            return response['homeworks']
        logger.error(
            'Формат ответа не соответсвует ожидаемому.'
        )
    logger.error(
        'Формат ответа не соотвествует ожидаемому.'
    )
    raise TypeError


def parse_status(homework):
    """Проверяет статус домашней работы."""

    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError as error:
        logger.error(
            f'Неожиданный статус работы {error}'
        )
        raise UndefinedStatus


def main():
    """Основная логика работы бота."""

    if not check_tokens():
        sys.exit(
            'Обнаружена пустая переменная.'
        )

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) > 0:
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
            else:
                logger.debug(
                    'Нет изменений в статусах работ'
                )
                current_timestamp = response.get(
                    'current_date', current_timestamp
                )
        except SendMessageError:
            ('Ошибка отравки сообщения.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
