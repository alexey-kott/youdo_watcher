import asyncio
import json
from asyncio import sleep
from http import HTTPMethod
from typing import Sequence
from logging import getLogger

import redis.asyncio as aioredis
from playwright.async_api import async_playwright, Route, Request, Page
from deepdiff import DeepDiff

from app.config import config
from app.schemas import TaskSchema, TaskListSchema

logger = getLogger("youdo_watcher")


HEADERS = {
    'Accept':          'application/json',
    'Content-Type':    'application/json',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
}
TASKS_API_URL = 'https://youdo.com/api/tasks/tasks/'
OPENED_TASKS_URL = 'https://youdo.com/tasks-all-opened-all'

def get_search_queries() -> Sequence[str]:
    with open(config.app.QUERIES_FILE) as file:
        queries = [query.strip() for query in file.readlines()]
        return queries


async def handle_task(task: TaskSchema):
    redis = aioredis.from_url(config.redis.URL, decode_responses=True)
    # async with redis
    previous_state = await redis.set(task.id, task.model_dump_json(), get=True)
    if previous_state:
        old_task = TaskSchema.model_validate_json(previous_state)
        diff = DeepDiff(old_task.model_dump(exclude_unset=True), task.model_dump(exclude_unset=True))
        logger.info(f"Task {task.id} was changed; changes: {diff}")


async def mixin_search_query_to_task_request(route: Route, request: Request, page: int | None = None, query_text: str | None = None) -> None:
    if request.method != HTTPMethod.POST and '/api/tasks/tasks' not in request.url:
        await route.continue_()
        return

    headers = dict(request.headers)
    headers.pop("content-length", None)  # content-length can change during replace search fields

    body = request.post_data_json or {}

    body["q"] = query_text if query_text else body['q']
    body["page"] = page if page else body['page']

    await route.continue_(
        headers=headers,
        post_data=body,
    )


async def handle_tasks_search_response(task_list: TaskListSchema):
    for task in task_list:
        await handle_task(task)


async def parse_tasks(tab: Page, query: str | None = None) -> None:

    page = 1
    while True:
        # modify requests for this route from that tab
        await tab.route("**/api/tasks/tasks/**", lambda route, request: mixin_search_query_to_task_request(route, request, page=page, query_text=query))

        async with tab.expect_response(lambda r: "/api/tasks/tasks/" in r.url) as resp_info:
            await tab.goto(OPENED_TASKS_URL)

        resp = await resp_info.value

        try:
            data = await resp.json()
            logger.info(f"Response code: {resp.status}; response text: {data}")
        except json.decoder.JSONDecodeError:
            logger.error(f"Response code: {resp.status}; response body: {resp.request.post_data_json}; headers: {resp.request.headers}")
            return

        items = TaskListSchema.model_validate(data['ResultObject']['Items'])
        if items:
            logger.info(f"{len(items)} items found")
            await handle_tasks_search_response(items)
            page += 1
            await sleep(config.app.DELAY)
        else:
            logger.info(f"task list was run out of items")
            page = 1


async def observe_tasks() -> None:
    async with async_playwright() as playwright:
        # browser = await playwright.chromium.launch_persistent_context(
        #     user_data_dir="./user-profile",
        #     headless=False,
        #     service_workers="block",
        # )

        browser = await playwright.chromium.launch(headless=config.watcher.headless)
        context = await browser.new_context()
        tab = await context.new_page()


        await parse_tasks(tab)


        # search_queries = get_search_queries()
        # for query in search_queries:
            # pins = await get_pins(query)
            # if pins:
            #     await handle_tasks(query)
            # tasks = await parse_tasks(page, query)
            # await asyncio.sleep(config.app.DELAY)


async def main():
    await asyncio.gather(
        observe_tasks(),
    )


if __name__ == "__main__":
    asyncio.run(main())