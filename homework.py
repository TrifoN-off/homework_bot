import time
import logging
import os

import requests
from telebot import TeleBot
from dotenv import load_dotenv


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

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.DEBUG,
    handlers=[logging.StreamHandler(),]
)
logger = logging.getLogger(__name__)


def check_tokens():
    """Проверяет доступность обязательных переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }

    missing_tokens = [name for name, value in tokens.items() if not value]

    if missing_tokens:
        error_message = (
            f'Отсутствуют токены: {", ".join(missing_tokens)}. '
            'Программа принудительно остановлена.')
        logger.critical(error_message)
        raise Exception(error_message)
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Бот отправил сообщение "{message}"')
    except Exception:

        logger.error('Ошибка при отправке сообщения.')


def get_api_answer(timestamp):
    """Выполняет запрос к API Практикума."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != 200:
            error_message = (
                f'Эндпоинт {ENDPOINT} недоступен. '
                f'Код ответа API: {response.status_code}'
            )
            logger.error(error_message)
            raise Exception(error_message)
        return response.json()
    except Exception as error:
        logger.error(error)
        raise Exception(error)


def check_response(response):
    """Проверяет ответ API на соответствие ожидаемой структуре."""
    if not isinstance(response, dict):
        error_message = 'Ответ API не является словарем.'
        logger.error(error_message)
        raise TypeError(error_message)
    if 'homeworks' not in response or 'current_date' not in response:
        error_message = 'Отсутствие ожидаемых ключей в ответе API.'
        logger.error(error_message)
        raise KeyError(error_message)
    if not isinstance(response['homeworks'], list):
        error_message = 'Элемент "homeworks" не является списком.'
        logger.error(error_message)
        raise TypeError(error_message)


def parse_status(homework):
    """Извлекает статус домашней работы и формирует текст сообщения."""
    try:
        homework_name = homework['homework_name']
    except Exception as error:
        raise Exception(error)
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS.keys():
        raise Exception
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    prev_message = ''
    last_error = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response.get('homeworks')
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                if message != prev_message:
                    send_message(bot, message)
                    prev_message = message
            else:
                logger.debug('Отсутствие новых статусов')
            timestamp = response.get('current_date')
        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            logger.error(error_message)
            if error_message != last_error:
                send_message(bot, error_message)
                last_error = error_message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
