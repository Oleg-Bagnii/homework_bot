from contextlib import suppress
from http import HTTPStatus
import sys
import time
from urllib.error import HTTPError
from venv import logger
import telegram
import logging
import requests
from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = 'y0_AgAAAAAiSgTJAAYckQAAAADuYNgd26a-TfDzQkW82NDK5XVqed0uqds'
TELEGRAM_TOKEN = '6594524470:AAEimmGOgBpoohcC92scrGLN2GgDh86jaEw'
TELEGRAM_CHAT_ID = '1590615376'

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

def check_tokens():
    '''Проверка доступности токенов'''
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
        

def send_message(bot, message):
    '''Отправляет сообщение в Telegram чат'''
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f'{message}')
        logging.debug(f'Сообщение отправлено: {message}')
    except:
        logging.error(f'Не удалось отправить сообщение: {message}')


def get_api_answer(timestamp):
    '''Запрос к API'''
    try:
        homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params={'from_date': timestamp})
    except requests.RequestException:
        raise ('Ошибка в запросе. Неправильно указан адрес.')
    if homework_statuses.status_code != HTTPStatus.OK:
        raise HTTPError('Статус страницы отличный от 200.')
    return homework_statuses.json()


def check_response(response):
    '''Проверка ответа API'''
    if 'homeworks' not in response:
        raise TypeError('Нет ключа homeworks.')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Объект не является списком.')
    return True


def parse_status(homework):
    '''Извлекает статус проверки домашней работы'''
    if 'homework_name' not in homework:
        raise KeyError('Ключа homework_name не найдено.')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if verdict is None:
        raise ValueError('Непредвиденный статус домашней работы.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Проверьте переменные окружения.')
        sys.exit('Отсутствуют переменные окружения.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    send_message(bot, 'Привет')
    old_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response.get('homeworks')
            if homeworks:
                for homework in homeworks:
                    message = parse_status(homework)
                    if message != old_message:
                        old_message = message
                        send_message(bot, message)
            else:
                logger.info('Новый статус отсутствует.')
            timestamp = response.get('current_date', timestamp)
        except telegram.error.TelegramError as error:
            logger.error(f'Не удается отправить сообщение {error}.')
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
    logging.basicConfig(level=logging.INFO)
    main()
