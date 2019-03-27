import asyncio
import json
from asyncio import sleep
from configparser import ConfigParser
from typing import List, Dict

from socks import SOCKS5
import aioredis as aioredis
from aiohttp import ClientSession, BasicAuth
from aiogram import Bot, Dispatcher, executor


async def save_task(task: Dict, config: ConfigParser):
    redis_pool = await aioredis.create_redis_pool(f"{config['REDIS']['HOST']}:{config['REDIS']['PORT']}",
                                                  db=config['REDIS']['TASKS_DB'])
    with await redis_pool as redis_connection:

        return await redis_connection.set(key=task['Id'], value=json.dumps(task))


async def send_message(task: Dict, config: ConfigParser, bot: Bot):

    await bot.send_message(config['CHANNEL']['ID'], text='test')
    # await bot.send_message(config['CHANNEL']['ID'], json.dumps(task))


async def handle_tasks(tasks: List, config: ConfigParser, bot: Bot):
    for task in tasks:
        await send_message(task, config, bot)

        # await save_task(task, config)


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


async def main(bot: Bot, config: ConfigParser):

    # await bot.send_message(config['CHANNEL']['ID'], text='test')

    search_queries = get_search_queries(config)
    while True:
        for query in search_queries:
            tasks = await get_tasks(query)
            await handle_tasks(tasks, config, bot)

        await sleep(3)


if __name__ == "__main__":
    config_parser = ConfigParser(comment_prefixes='#')
    config_parser.read('config.ini')

    PROXY_URL = 'socks5://51.144.86.230:18001'
    PROXY_AUTH = BasicAuth(login='usrTELE', password='avt231407')
    bot = Bot(config_parser['BOT']['TOKEN'], proxy=PROXY_URL, proxy_auth=PROXY_AUTH)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(bot, config_parser))
