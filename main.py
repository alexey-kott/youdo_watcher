import asyncio
import json
import logging
import sys
from asyncio import sleep
from configparser import ConfigParser
from typing import List, Dict, Tuple

import aioredis as aioredis
import requests
from aiogram.types import Message
from requests.exceptions import ConnectionError
from aiohttp import ClientSession, BasicAuth
from aiogram import Bot, Dispatcher
from bs4 import BeautifulSoup

from models import User

MESSAGE_LENGTH_LIMIT = 4096


async def get_task_description(task_id: int) -> str:
    url_request = f'https://youdo.com/t{task_id}'
    async with ClientSession() as session:
        async with session.get(url_request, ssl=False) as response:
            response_page = await response.text()
            soup = BeautifulSoup(response_page, 'lxml')
            description = soup.find('span', {'itemprop': 'description'})

            return description.text


async def send_message(task: Dict, config: ConfigParser, bot: Bot) -> None:
    text = f"*{task['Name']}*\n\n" \
        f"{task['Description']}\n\n" \
        f"Бюджет: *{task['BudgetDescription'] if task['BudgetDescription'] else 'не указан'}*\n\n" \
        f"https://youdo.com/t{task['Id']}"

    await bot.send_message(config['CHANNEL']['ID'], text=text, parse_mode='Markdown')


async def handle_tasks(tasks: List, config: ConfigParser, bot: Bot):
    redis_pool = await aioredis.create_redis_pool(f"redis://{config['REDIS']['HOST']}:{config['REDIS']['PORT']}",
                                                  db=config.getint('REDIS', 'TASKS_DB'))

    with await redis_pool as redis_connection:
        for task in tasks:
            saved_task = await redis_connection.get(task['Id'])
            if not saved_task:
                await redis_connection.set(key=task['Id'], value=json.dumps(task))

                task['Description'] = await get_task_description(task['Id'])
                await send_message(task, config, bot)
                logger.debug(json.dumps(task))
        await sleep(config.getint('GENERAL', 'DELAY'))


def get_search_queries(config: ConfigParser):
    with open(config['GENERAL']['QUERIES_FILE']) as file:
        return [line.strip() for line in file.readlines() if line.strip() != '']


async def get_tasks(query: str):
    url_request = 'https://youdo.com/api/tasks/tasks/'
    if query.strip() == '':
        raise ValueError('Empty search query')
    params = {'q': query,
              'list': 'all',
              'status': 'opened',
              'lat': '55.753215',
              'lng': '37.622504',
              'radius': '50', 'page': '1', 'noOffers': 'false', 'onlySbr': 'false',
              'onlyB2B': 'false', 'recommended': 'false', 'priceMin': '0', 'sortType': '1', 'categories': 'all'}
    async with ClientSession() as session:
        async with session.get(url_request, params=params, ssl=False) as response:
            logger.debug(response.real_url)
            data = json.loads(await response.text())
            logger.debug(data)

            return data['ResultObject']['Items']


async def main(bot: Bot, dispatcher: Dispatcher, config: ConfigParser):
    @dispatcher.message_handler(commands=['init'])
    async def init(message: Message):
        User.create_table(fail_silently=True)

    @dispatcher.message_handler(commands=['ping'])
    async def ping(message: Message):
        await message.reply("I'm alive")

    @dispatcher.message_handler(commands=['start'])
    async def start(message: Message):
        await message.reply('Пока что я ничего не умею, но скоро @alexkott допилит меня до minimal valuable product.')
        User.get_or_create(**message.from_user._values)

    @dispatcher.message_handler(commands=['search'])
    async def search(message: Message):
        User.get_or_create(**message.from_user._values)
        tasks = await get_tasks(message.text.replace('/search ', ''))

        message_text = ''
        for task in tasks:
            description = await get_task_description(task['Id'])
            task_text = f"[{task['Name']}](https://youdo.com{task['Url']}), {task['PriceAmount']}₽ ({task['StatusText']})\n " \
                f"{description}\n\n"

            if len(message_text + task_text) >= MESSAGE_LENGTH_LIMIT:
                await bot.send_message(message.from_user.id, message_text, parse_mode='Markdown',
                                       disable_web_page_preview=True)
                message_text = ''

            message_text += task_text

        await bot.send_message(message.from_user.id, message_text, parse_mode='Markdown',
                               disable_web_page_preview=True)

    @dispatcher.message_handler(content_types=['text'])
    async def forward(message: Message):
        User.get_or_create(**message.from_user._values)
        await bot.send_message(5844335, f"{json.dumps(message.from_user._values)} \n\n {message.text}")

    while True:
        search_queries = get_search_queries(config)
        for query in search_queries:
            tasks = await get_tasks(query)
            await handle_tasks(tasks, config, bot)
        await asyncio.sleep(1)


def get_logger(level=logging.INFO) -> logging.Logger:
    app_logger = logging.getLogger()

    logging.basicConfig(level=level,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filename='logs/default.log')

    logging.getLogger('you_do_bot')

    info_handler = logging.StreamHandler(sys.stdout)
    info_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    info_handler.setFormatter(formatter)
    app_logger.addHandler(info_handler)

    debug_handler = logging.FileHandler('logs/debug.log')
    debug_handler.setLevel(logging.DEBUG)
    app_logger.addHandler(debug_handler)

    return app_logger


def parse_args(args: List[str]) -> Tuple[List[str], Dict[str, str]]:
    options = []
    arguments = {}
    for entry in args:
        if not entry.startswith('--'):
            continue
        if entry.find('=') == -1:
            options.append(entry.strip('-'))
        else:
            key, value = entry.strip('-').split('=')
            arguments[key] = value

    return options, arguments


if __name__ == "__main__":
    options, args = parse_args(sys.argv)
    logger = get_logger(args.get('log-level'))
    config_parser = ConfigParser(comment_prefixes='#')
    config_parser.read('config.ini')

    try:
        PROXY_AUTH = None
        PROXY_URL = None
        response = requests.get('https://api.telegram.org')
    except ConnectionError:
        PROXY_URL = f"socks5://{config_parser['PROXY']['HOST']}:{config_parser['PROXY']['PORT']}"
        PROXY_AUTH = BasicAuth(login=config_parser['PROXY']['USERNAME'], password=config_parser['PROXY']['PASS'])

    tg_bot = Bot(config_parser['BOT']['TOKEN'], proxy=PROXY_URL, proxy_auth=PROXY_AUTH)
    dp = Dispatcher(tg_bot)

    loop = asyncio.get_event_loop()
    loop.create_task(dp.start_polling())
    loop.run_until_complete(main(bot=tg_bot,
                                 dispatcher=dp,
                                 config=config_parser))
