import aiohttp
import asyncio
import logging
import time
import json
import urllib3
import io
import os.path
from os import path

author = "kalka"
repo = "wolfpack-legacy"

curseforge_url = "https://addons-ecs.forgesvc.net/api/v2/addon/"
gitea_url = "https://git.kalka.io/api/v1/repos/{}/{}/releases".format(author, repo)
mod_list = []

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')

async def fetch(session, url):
    try:
        async with session.get(url) as r:
            r = await r.read()
    except aiohttp.ClientResponseError as e:
        logging.warning(e.code)
    except asyncio.TimeoutError:
        logging.warning("Timeout")
    except Exception as e:
        logging.warning(e)
    else:
        return r
    return

async def fetch_async(loop, mods):
    tasks = []
    # try to use one client session
    async with aiohttp.ClientSession() as session:
        for k in mods["resolutions"].keys():
            project_id = mods["resolutions"][k]["projectId"]
            if project_id is not None:
                task = asyncio.ensure_future(fetch(session, curseforge_url + str(project_id)))
                tasks.append(task)
        # await response outside the for loop
        responses = await asyncio.gather(*tasks)
    return responses

def get_gitea_data(): #single threaded, not needed to be intensive
    if path.exists('packmaker.lock'):
        logging.info("Found local packmaker.lock. Using that instead.")
        with open('packmaker.lock', 'r') as f:
            mod_data_json = json.loads(f.read())
        logging.info("Done.")
    else:
        logging.info("Local packmaker not found, grabbing from the URL.")
        http = urllib3.PoolManager()
        r = http.request('GET', gitea_url)
        data = json.loads(r.data)
        mod_data = http.request('GET', data[0]["assets"][2]["browser_download_url"])
        mod_data_json = json.loads(mod_data.data)
    return mod_data_json

def get_logo(attachments):
    for l in attachments:
        if l['isDefault']:
            return l['thumbnailUrl']

def main():
    logging.info("Awoo!")
    start_time = time.time()
    loop = asyncio.get_event_loop()
    mods = get_gitea_data()
    future = asyncio.ensure_future(fetch_async(loop, mods))
    loop.run_until_complete(future)
    responses = future.result()
    data = []
    for r in responses:
        json_response = json.loads(r)
        clean_data = {
            "id": json_response.get("id"),
            "name": json_response.get("name"),
            "summary": json_response.get("summary"),
            "website_url": json_response.get("website_url"),
            "logo": get_logo(json_response.get("attachments", {})),
            "slug": json_response.get("slug")
        }
        data.append(clean_data)
    
    with open('modlist.db', 'wb') as f:
        b = bytes(json.dumps(data), encoding='utf8')
        f.write(b)

    logging.info("Requests took %s seconds", str(time.time() - start_time))

main()
