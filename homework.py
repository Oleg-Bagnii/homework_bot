import logging
import os
import sys
import time
from contextlib import suppress
from http import HTTPStatus
from venv import logger

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (EmptyResponseAPIError, NoVariablesError,
                        UnexpectedStatusError, WrongAddressError)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logger.info('Начало отправки сообщения.')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f'{message}')
        logging.debug(f'Сообщение отправлено: {message}')
    except telegram.error.TelegramError as error:
        logging.error(f'Не удалось отправить сообщение: {error}')


def get_api_answer(timestamp):
    """Запрос к API."""
    try:
        logging.info(f'Отправка запроса {ENDPOINT}.'
                     f'Заголовки запросов: {HEADERS}.'
                     f'Параметры запроса {timestamp}')
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params={'from_date': timestamp})
    except requests.RequestException:
        raise WrongAddressError('Ошибка в запросе. Неправильно указан адрес.')
    if homework_statuses.status_code != HTTPStatus.OK:
        raise UnexpectedStatusError('Статус страницы отличный от 200.')
    return homework_statuses.json()


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError('Не является словарем.')
    homeworks = response.get('homeworks')
    if 'homeworks' not in response:
        raise EmptyResponseAPIError('Пустой ответ API.')
    if not isinstance(homeworks, list):
        raise TypeError('Объект не является списком.')
    return homeworks


def parse_status(homework):
    """Извлекает статус проверки домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('Ключа homework_name не найдено.')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if verdict is None:
        raise UnexpectedStatusError('Непредвиденный статус домашней работы.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Проверьте переменные окружения.')
        raise NoVariablesError('Отсутствуют переменные окружения.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    send_message(bot, 'Привет')
    old_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
            else:
                logger.debug('Новый статус отсутствует.')
                message = 'Нет статусов домашней работы.'
            if message != old_message:
                old_message = message
                send_message(bot, message)
            timestamp = response.get('current_date', timestamp)
        except EmptyResponseAPIError:
            logger.error('Пустой ответ.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != old_message:
                with suppress(FileNotFoundError):
                    logger.error(message)
                    send_message(bot, message)
                    old_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        filename='main.log')
    main()
