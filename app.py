from discord.ext import commands
from helpers import prepare_attachments, prepare_raw_attachments, strp_arg_time
from datetime import timedelta, datetime
from discord.ext import tasks
from pymongo import MongoClient
import os
import settings


oeg = os.environ.get

bot = commands.Bot(command_prefix="%")
bot.cleanings = {}

client = MongoClient(
    f'mongodb+srv://{settings.MONGO_USERNAME}:{settings.MONGO_PASSWORD}'
    '@spy-boy-z4l1f.mongodb.net/test?retryWrites=true&w=majority'
)
db = client[settings.MONGO_DB_NAME]
collection = db.guilds


def refresh_cleanings():
    docs = collection.find({'cleanings': {'$exists': True, '$ne': None}})
    for doc in docs:
        guild = doc['guild']
        bot.cleanings.setdefault(guild, {})
        missing_cleanings = set(doc['cleanings'].keys()).difference(set(bot.cleanings[guild].keys()))
        for cleaning_id in missing_cleanings:
            target = bot.get_channel(int(cleaning_id))
            if not target:
                continue
            cleaning_dict = doc['cleanings'][cleaning_id]
            delta = timedelta(**strp_arg_time(cleaning_dict['expire']))
            interval = strp_arg_time(cleaning_dict['interval'])
            interval['hours'] += interval.pop('days') * 24

            def check_message(message):
                return datetime.utcnow() - delta > message.created_at and not message.pinned

            @tasks.loop(**interval)
            async def clean():
                deleted = await target.purge(limit=100, oldest_first=True, check=check_message)
                while deleted:
                    deleted = await target.purge(limit=100, oldest_first=True, check=check_message)

            bot.cleanings[guild][cleaning_id] = clean
            bot.cleanings[guild][cleaning_id] = clean.start()
            print(f"Cleaning with id {cleaning_id} refreshed from db.")


@tasks.loop(seconds=settings.CLEANING_REFRESH_TIME)
async def sync_cleanings():
    refresh_cleanings()


@bot.event
async def on_ready():
    refresh_cleanings()
    print("Bot successfully started")


@bot.command(pass_context=True)
async def ping(ctx):
    await ctx.send('pong')


@bot.command()
@commands.has_permissions(administrator=True)
async def spy(ctx, source_name=None, target_name=None):
    if not source_name:
        await ctx.send('Please provide a channel name to spy.')
        return
    if not target_name:
        await ctx.send('Please provide a target channel name.')
        return
    source_id, target_id = None, None
    for channel in ctx.guild.text_channels:
        if source_id and target_id:
            break
        if channel.name == source_name:
            source_id = str(channel.id)
            continue
        if channel.name == target_name:
            target_id = str(channel.id)
            continue
    if not source_id:
        await ctx.send(
            f"I could not find any channel named \"{source_name}\". Please check if you passed the channel name "
            "correctly or if I have a proper permissions to see it."
        )
        return
    if not target_id:
        await ctx.send(
            f"I could not find any channel named \"{target_name}\". Please check if you passed the channel name "
            "correctly or if I have a proper permissions to see it."
        )
        return
    # todo: permission check
    collection.update_one({'guild': str(ctx.guild.id)}, {'$set': {f'observables.{source_id}': target_id}}, upsert=True)
    await ctx.send(f"Successfully added \"{source_name}\" channel to spy list. Target channel: \"{target_name}\"")


@bot.command()
@commands.has_permissions(administrator=True)
async def spy_list(ctx):
    message_content = ""
    guild_id = str(ctx.guild.id)
    guild_document = collection.find_one({'guild': guild_id}) or {}
    guild_observables = guild_document.get('observables')
    if not guild_observables:
        await ctx.send(f"No channels are being spied yet!")
        return
    for source_id, target_id in guild_observables.items():
        source = bot.get_channel(int(source_id))
        target = bot.get_channel(int(target_id))
        if not source or not target:
            collection.update_one({'guild': guild_id}, {'$unset': {f'observables.{source_id}': ''}})
            continue
        message_content += f"{source.name} ==> {target.name}\n"
    if not message_content:
        await ctx.send(f"No channels are being spied yet!")
        return
    await ctx.send(message_content)


@bot.command()
@commands.has_permissions(administrator=True)
async def spy_stop(ctx, source_name=None):
    if not source_name:
        await ctx.send('Please provide a channel name to remove from spy list.')
        return
    guild_id = str(ctx.guild.id)
    guild_document = collection.find_one({'guild': guild_id}) or {}
    guild_observables = guild_document.get('observables')
    if not guild_observables:
        await ctx.send(f"No channels are being spied yet!")
        return
    for channel in ctx.guild.text_channels:
        if channel.name == source_name:
            target_id = str(channel.id)
            break
    else:
        await ctx.send(
            f"I could not find any channel named \"{source_name}\". Please check if you passed the channel name "
            "correctly or if I have a proper permissions to see it."
        )
        return
    if target_id in guild_observables:
        collection.update_one({'guild': guild_id}, {'$unset': {f'observables.{target_id}': ''}})
        await ctx.send(f"Successfully removed \"{source_name}\" channel from spy list.")
    else:
        await ctx.send(
            "Could not find given channel on the spy list. "
            f"To check all spied channels type {bot.command_prefix}spy_list"
        )


@bot.command()
@commands.has_permissions(administrator=True)
async def cleaning(ctx, target_name=None, expire_time="3", schedule_interval="0:0:10"):
    if not target_name:
        await ctx.send('Please provide a channel name to schedule cleaning.')
        return
    delta = timedelta(**strp_arg_time(expire_time))
    interval = strp_arg_time(schedule_interval)
    interval['hours'] += interval.pop('days') * 24
    for channel in ctx.guild.text_channels:
        if channel.name == target_name:
            target = channel
            break
    else:
        await ctx.send(
            f"I could not find any channel named \"{target_name}\". Please check if you passed the channel name "
            "correctly or if I have a proper permissions to see it."
        )
        return

    def check_message(message):
        return datetime.utcnow() - delta > message.created_at and not message.pinned

    @tasks.loop(**interval)
    async def clean():
        deleted = await target.purge(limit=100, oldest_first=True, check=check_message)
        while deleted:
            deleted = await target.purge(limit=100, oldest_first=True, check=check_message)
    guild_id = str(ctx.guild.id)
    target_id = str(target.id)
    bot.cleanings.setdefault(guild_id, {})
    if target_id in bot.cleanings[guild_id]:
        bot.cleanings[guild_id][target_id].cancel()
        del bot.cleanings[guild_id][target_id]
    collection.update_one(
        {'guild': guild_id},
        {'$set': {f'cleanings.{target_id}': {'interval': schedule_interval, 'expire': expire_time}}},
        upsert=True
    )
    bot.cleanings[guild_id][target_id] = clean
    bot.cleanings[guild_id][target_id].start()
    await ctx.send(f'Successfully scheduled cleaning on "{target_name}" channel.')
    return clean


@bot.command()
@commands.has_permissions(administrator=True)
async def cleaning_stop(ctx, target_name=None):
    if not target_name:
        await ctx.send('Please provide a channel name to remove cleaning.')
        return
    guild_id = str(ctx.guild.id)
    guild_document = collection.find_one({'guild': guild_id}) or {}
    guild_cleanings = guild_document.get('cleanings')
    if not guild_cleanings:
        await ctx.send('No cleanings scheduled yet!')
        return
    for channel in ctx.guild.text_channels:
        if channel.name == target_name:
            target = channel
            break
    else:
        await ctx.send(
            f"I could not find any channel named \"{target_name}\". Please check if you passed the channel name "
            "correctly or if I have a proper permissions to see it."
        )
        return
    target_id = str(target.id)
    loop = bot.cleanings.get(guild_id, {}).get(target_id)
    if not loop and target_id not in guild_cleanings:
        await ctx.send(
            'No cleanings scheduled on specified channel! '
            f'To show all cleanings type {bot.command_prefix}cleaning_list'
        )
        return
    if loop:
        loop.cancel()
        del bot.cleanings[guild_id][target_id]
    collection.update_one({'guild': guild_id}, {'$unset': {f'cleanings.{target_id}': ''}})
    await ctx.send(f'Successfully removed "{target_name}" channel from cleaning list.')


@bot.command()
@commands.has_permissions(administrator=True)
async def cleaning_list(ctx):
    # todo: add message expire listing and cleaning interval
    guild_document = collection.find_one({'guild': str(ctx.guild.id)}) or {}
    guild_cleanings = guild_document.get('cleanings')
    if not guild_cleanings:
        await ctx.send('No cleanings scheduled yet!')
        return
    content = "Channels with cleaning:\n"
    for target_id in guild_cleanings:
        target = bot.get_channel(int(target_id))
        content += f"{target.name}\n"
    await ctx.send(content)


# todo: add help, database connection, optimise code


@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.author.id == bot.user.id:
        return
    guild_document = collection.find_one({'guild': str(message.guild.id)}) or {}
    guild_observables = guild_document.get('observables', {})
    target_id = guild_observables.get(str(message.channel.id))
    if not target_id:
        return
    target = bot.get_channel(int(target_id))
    content = (
        f"**{message.author}** {message.created_at.strftime('%m-%d-%Y %H:%M:%S')} UTC:\n"
        f"{message.content}\n"
    )
    attachments = await prepare_attachments(message)
    await target.send(content, files=attachments)


@bot.event
async def on_message_edit(before, after):
    if before.content == after.content:
        return
    guild_document = collection.find_one({'guild': str(after.guild.id)}) or {}
    guild_observables = guild_document.get('observables', {})
    target_id = guild_observables.get(str(after.channel.id))
    if not target_id:
        return
    target = bot.get_channel(int(target_id))
    time = f" on {after.edited_at.strftime('%m-%d-%Y %H:%M:%S')} UTC" if after.edited_at else ""
    content = (
        f"**{before.author}** performed edit{time}:\n"
        f"*Old message:*\n||{before.content}||\n"
        f"*New message:*\n{after.content}"
    )
    attachments = await prepare_attachments(after)
    await target.send(content, files=attachments)


@bot.event
async def on_raw_message_edit(payload):
    # cached messages are supported by different method.
    if payload.cached_message:
        return
    message = payload.data
    guild_document = collection.find_one({'guild': message['guild_id']}) or {}
    guild_observables = guild_document.get('observables', {})
    target_id = guild_observables.get(str(payload.channel_id))
    if not target_id:
        return
    target = bot.get_channel(int(target_id))
    content = (
        f"**{message['author']['username']}{message['author']['discriminator']}** performed edit on "
        f"{datetime.fromisoformat(message['edited_timestamp']).strftime('%m-%d-%Y %H:%M:%S')} UTC:\n"
        f"*New message:*\n{message['content']}\n"
        f"*Old message content unknown because I could not find it in my message cache "
        f"(the message is too old). Sorry!*"
    )
    attachments, warning = await prepare_raw_attachments(message)
    if warning:
        content = f'{content}\n{warning}'
    await target.send(content, files=attachments)


bot.run(settings.DISCORD_TOKEN)
