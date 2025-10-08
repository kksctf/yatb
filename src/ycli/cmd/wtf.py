import datetime
from uuid import UUID

from yatb.api.api_dynamic_tasks import DynamicTasksClient
from yatb.shared.dtc.models.task import is_taskinfo_ready
from ycli.base import app, c
from ycli.client import YATB


@app.command
async def wtf() -> None:
    raw_uids = """
    79aa0811-0b04-484a-b39c-263485315a03
    25ca1ab5-2b9a-4ff9-b636-2ef36b41231b
    4b9d4a2a-e33a-4d9a-b3d4-d087bd4d630e
    a71c769a-7bbd-48a5-a5c3-09cda88708f0
    e53ce943-0468-4f9e-8133-9346f10b3dc3
    a9ab45f3-bc5d-4ce2-af7c-abbf632ee495
    8d73384b-92ea-417e-94a5-f158cb6c3551
    8e2baf1d-9087-4d3b-b391-871c63e9e363
    458d5d1b-f686-4341-9c0d-dbb89f49094c
    5c374c80-a61b-4662-8b9a-57569a220f0b
    """

    now = datetime.datetime.now(datetime.UTC)

    uids = {UUID(x.strip()) for x in raw_uids.strip().split("\n")}
    async with YATB() as y, DynamicTasksClient() as dtc:
        datas = await dtc._client.get_prefix(f"{dtc.tasks_prefix}/u:".encode())
        for data in datas:
            if data.key.endswith(b"/rpc"):
                continue

            model = dtc._task_bytes_to_model(data.value)

            if model.user_id in uids:
                continue

            if not (is_taskinfo_ready(model) and model.time_of_death < now):
                continue

            c.print(model)

            await dtc.delete_task(model)  # type: ignore
