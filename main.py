import asyncio
import json
from asyncio import sleep
from configparser import ConfigParser
from typing import List, Dict, Sequence, Optional
from logging import getLogger

import aioredis
from aiogram.types import Message
from aiohttp import ClientSession, BasicAuth
from aiogram import Bot, Dispatcher, executor

from models import User

logger = getLogger("youdo_watcher")

config = ConfigParser(comment_prefixes='#')
config.read('config.ini')


# Initialize bot and dispatcher
bot = Bot(token=config['BOT']['TOKEN'])
dp = Dispatcher(bot)


async def get_task(task_id: int) -> Optional[Dict]:
    url_request = 'https://youdo.com/api/tasks/taskmodel/'
    params = {'taskId': task_id}
    async with ClientSession() as session:
        async with session.get(url_request, params=params, ssl=False) as response:
            text = await response.text()
            if response.status == 200:
                data = json.loads(text)

                return data["ResultObject"]["TaskData"]
            else:
                logger.error(f"Response code: {response.status}; response text: {text}")
                await bot.send_message(config["CHANNEL"]["ID"], f"Response code: {response.status}; response text: {text}")


async def handle_tasks(pins: List):
    redis_pool = await aioredis.create_redis_pool(f"redis://{config['REDIS']['HOST']}:{config['REDIS']['PORT']}",
                                                  db=config.getint('REDIS', 'TASKS_DB'))
    for pin in pins:
        task_id = pin[0]
        task = await get_task(task_id)
        saved_task = await redis_pool.get(task_id)
        if not saved_task:
            await redis_pool.set(key=task_id, value=json.dumps(task))

            price = task['Price']['PriceInHeader']['StringFormat'] + task['Price']['PriceInHeader']['CurrencyShort']
            text = f"*{task['Title']}*\n\n" \
                   f"{task['Description']}\n\n" \
                   f"Бюджет: *{price} *\n\n" \
                   f"https://youdo.com/t{task['Id']}"

            await bot.send_message(config['CHANNEL']['ID'], text=text, parse_mode='Markdown')

            print(task, end='\n\n\n')

        await sleep(3)


def get_search_queries() -> Sequence[str]:
    with open(config['GENERAL']['QUERIES_FILE']) as file:
        queries = [query.strip() for query in file.readlines()]
        return queries


async def get_pins(query_text: str):
    # pin - список, который возвращает YouDo API. Это список из нескольких
    # значений: [task_id, lng, lat, ..., ...]. Можно воспринимать пин как точку на карте.
    url_request = 'https://youdo.com/api/tasks/mappinsclusters/'
    params = {'q': query_text,
              'list': 'all',
              'status': 'opened',
              'lat': 55.753215,
              'lng': 37.622504,
              'neLat': 56.18094240165325,
              'neLng': 38.6013858359375,
              'swLat': 55.322191430966846,
              'swLng': 36.64362216406251,
              'radius': '50', 'page': '1', 'noOffers': 'false', 'onlySbr': 'false',
              'onlyB2B': 'false', 'recommended': 'false', 'priceMin': '0', 'sortType': '1', 'categories': 'all'}
    async with ClientSession() as session:
        async with session.post(url_request, data=params, ssl=False) as response:
            text = await response.text()
            if response.status == 200:
                data = json.loads(text)

                return data['ResultObject']['Pins']
            else:
                logger.error(f"Response code: {response.status}; response text: {text}")
                await bot.send_message(config['REDIS']['ADMIN'], f"Response code: {response.status}; response text: {text}")
                return


@dp.message_handler(commands=['init'])
async def init(message: Message):
    User.create_table(fail_silently=True)


@dp.message_handler(commands=['ping'])
async def ping(message: Message):
    await message.reply("I'm alive")


@dp.message_handler(commands=['start'])
async def start(message: Message):
    await message.reply('Пока что я ничего не умею, но скоро @alexkott допилит меня до minimal valuable product.')
    User.get_or_create(**message.from_user._values)


@dp.message_handler(content_types=['text'])
async def forward(message: Message):
    User.get_or_create(**message.from_user._values)
    await bot.send_message(config.getint('ADMIN', 'USER_ID'),
                           f"{json.dumps(message.from_user._values)} \n\n {message.text}")


async def observe_tasks():
    while True:
        search_queries = get_search_queries()
        for query in search_queries:
            pins = await get_pins(query)
            if pins:
                await handle_tasks(pins)
        await asyncio.sleep(1)


if __name__ == "__main__":
    dp.loop.create_task(observe_tasks())
    executor.start_polling(dp, skip_updates=True)
