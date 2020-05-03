import io
import re
from itertools import zip_longest

import requests
from discord import File


async def prepare_attachments(message):
    to_attach = []
    for attachment in message.attachments:
        file_bytes = await attachment.read(use_cached=True)
        file = File(io.BytesIO(file_bytes), filename=attachment.filename)
        to_attach.append(file)
    return to_attach


async def prepare_raw_attachments(message):
    to_attach = []
    warning = None
    for attachment in message['attachments']:
        try:
            response = requests.get(attachment['url'])
        except requests.RequestException:
            warning = '*WARNING: Could not retrieve some of the attachments of the message!*'
            continue
        else:
            if response.status_code != requests.codes.ok:
                warning = '*WARNING: Could not retrieve some of the attachments of the message!*'
                continue
        file = File(io.BytesIO(response.content), filename=attachment['filename'])
        to_attach.append(file)
    return to_attach, warning


def strp_arg_time(time_str):
    keys = ('days', 'hours', 'minutes', 'seconds')
    pattern = re.compile(r'^\d{1,7}(:\d{1,7}){,3}$')
    is_valid = pattern.fullmatch(time_str)
    if not is_valid:
        return None
    time_list = time_str.split(':')
    mapping = zip_longest(keys, time_list, fillvalue=0)
    return {k: int(v) for k, v in mapping}
