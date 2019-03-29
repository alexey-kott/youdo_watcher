import asyncio
import json
from asyncio import sleep
from configparser import ConfigParser
from typing import List, Dict

import aioredis as aioredis
import requests
from requests.exceptions import ConnectionError
from aiohttp import ClientSession, BasicAuth
from aiogram import Bot, Dispatcher, executor
from bs4 import BeautifulSoup



async def get_task_description(task_id: int) -> str:
    url_request = f'https://youdo.com/t{task_id}'
    async with ClientSession() as session:
        async with session.get(url_request, ssl=False) as response:
            response_page = await response.text()
            soup = BeautifulSoup(response_page, 'lxml')
            description = soup.find('span', {'itemprop': 'description'})

            return description.text


async def send_message(task: Dict, config: ConfigParser, bot: Bot):
    description = await get_task_description(task['Id'])

    text = f"*{task['Name']}*\n\n" \
        f"{description}\n\n" \
        f"Бюджет: *{task['BudgetDescription'] if task['BudgetDescription'] else 'не указан'}*\n\n" \
        f"https://youdo.com/t{task['Id']}"

    await bot.send_message(config['CHANNEL']['ID'], text=text, parse_mode='Markdown')


async def handle_tasks(tasks: List, config: ConfigParser, bot: Bot):
    for task in tasks:

        redis_pool = await aioredis.create_redis_pool(f"redis://{config['REDIS']['HOST']}:{config['REDIS']['PORT']}",
                                                      db=config.getint('REDIS', 'TASKS_DB'))

        with await redis_pool as redis_connection:
            saved_task = await redis_connection.get(task['Id'])
            if not saved_task:
                await redis_connection.set(key=task['Id'], value=json.dumps(task))
                await send_message(task, config, bot)
                print(task, end='\n\n\n')

        await sleep(config.getint('GENERAL', 'DELAY'))


def get_search_queries(config: ConfigParser):
    with open(config['GENERAL']['QUERIES_FILE']) as file:
        return file.readlines()


async def get_tasks(query: str):
    url_request = 'https://youdo.com/api/tasks/tasks/'
    params = {'q': query,
              'list': 'all',
              'status': 'opened',
              'lat': '55.753215',
              'lng': '37.622504',
              'radius': '50', 'page': '1', 'noOffers': 'false', 'onlySbr': 'false',
              'onlyB2B': 'false', 'recommended': 'false', 'priceMin': '0', 'sortType': '1', 'categories': 'all'}
    async with ClientSession() as session:
        async with session.get(url_request, params=params, ssl=False) as response:
            data = json.loads(await response.text())

            return data['ResultObject']['Items']


async def main(bot: Bot, dispatcher: Dispatcher, config: ConfigParser):
    @dispatcher.message_handler(commands=['ping'])
    async def ping(message):
        await message.reply("I'm alive")

    search_queries = get_search_queries(config)
    while True:
        for query in search_queries:
            tasks = await get_tasks(query)
            await handle_tasks(tasks, config, bot)


if __name__ == "__main__":
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
