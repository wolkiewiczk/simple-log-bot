from discord.ext import commands
from helpers import prepare_attachments, strp_arg_time
from datetime import timedelta, datetime
from discord.ext import tasks
import os


oeg = os.environ.get

bot = commands.Bot(command_prefix="%")

bot.observables = {}
bot.cleanings = {}
# todo: add database communication


@bot.event
async def on_ready():
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
            source_id = channel.id
            continue
        if channel.name == target_name:
            target_id = channel.id
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
    bot.observables.setdefault(ctx.guild.id, {})
    bot.observables[ctx.guild.id][source_id] = target_id
    await ctx.send(f"Successfully added \"{source_name}\" channel to spy list. Target channel: \"{target_name}\"")


@bot.command()
@commands.has_permissions(administrator=True)
async def spy_list(ctx):
    message_content = ""
    guild_observables = bot.observables.get(ctx.guild.id)
    if not guild_observables:
        await ctx.send(f"No channels are being spied yet!")
        return
    for source_id, target_id in guild_observables.items():
        source = bot.get_channel(source_id)
        target = bot.get_channel(target_id)
        if not source or not target:
            del bot.observables[ctx.guild.id][source_id]
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
    guild_observables = bot.observables.get(ctx.guild.id)
    if not guild_observables:
        await ctx.send(f"No channels are being spied yet!")
        return
    for channel in ctx.guild.text_channels:
        channel_name = channel.name
        if channel_name == source_name:
            channel_id = channel.id
            break
    else:
        await ctx.send(
            "Could not find given channel on the spy list. "
            f"To check all spied channels type {bot.command_prefix}spy_list"
        )
        return
    if channel_id in guild_observables:
        del bot.observables[ctx.guild.id][channel_id]
        await ctx.send(f"Successfully removed \"{channel_name}\" channel from spy list.")


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
    bot.cleanings.setdefault(ctx.guild.id, {})
    if target.id in bot.cleanings[ctx.guild.id]:
        bot.cleanings[ctx.guild.id][target.id].cancel()
        del bot.cleanings[ctx.guild.id][target.id]
    bot.cleanings[ctx.guild.id][target.id] = clean
    bot.cleanings[ctx.guild.id][target.id].start()
    await ctx.send(f'Successfully scheduled cleaning on "{target_name}" channel.')
    return clean


@bot.command()
@commands.has_permissions(administrator=True)
async def cleaning_stop(ctx, target_name=None):
    if not target_name:
        await ctx.send('Please provide a channel name to remove cleaning.')
        return
    guild_cleanings = bot.cleanings.get(ctx.guild.id)
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
    loop = guild_cleanings.get(target.id)
    if not loop:
        await ctx.send(
            'No cleanings scheduled on specified channel! '
            f'To show all cleanings type {bot.command_prefix}cleaning_list'
        )
        return
    loop.cancel()
    del bot.cleanings[ctx.guild.id][target.id]
    await ctx.send(f'Successfully removed "{target_name}" channel from cleaning list.')


@bot.command()
@commands.has_permissions(administrator=True)
async def cleaning_list(ctx):
    # todo: add message expire listing and cleaning interval
    guild_cleanings = bot.cleanings.get(ctx.guild.id)
    if not guild_cleanings:
        await ctx.send('No cleanings scheduled yet!')
        return
    content = "Channels with cleaning:\n"
    for target_id in guild_cleanings:
        target = bot.get_channel(target_id)
        content += f"{target.name}\n"
    await ctx.send(content)


# todo: add help, database connection, optimise code


@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.author.id == bot.user.id:
        return
    target_id = bot.observables.get(message.guild.id, {}).get(message.channel.id)
    if not target_id:
        return
    target = bot.get_channel(target_id)
    content = (
        f"**{str(message.author)}** {message.created_at.strftime('%m-%d-%Y %H:%M:%S')} UTC:\n"
        f"{message.content}\n"
    )
    attachments = await prepare_attachments(message)
    await target.send(content, files=attachments)


@bot.event
async def on_message_edit(before, after):
    if before.content == after.content:
        return
    target_id = bot.observables.get(after.guild.id, {}).get(after.channel.id)
    if not target_id:
        return
    target = bot.get_channel(target_id)
    time = f" on {after.edited_at.strftime} UTC" if after.edited_at else ""
    content = (
        f"**{str(before.author)} performed edit{time}:**\n"
        f"*Old message:*\n||{before.content}||\n"
        f"*New message:*\n{after.content}"
    )
    attachments = await prepare_attachments(after)
    await target.send(content, files=attachments)


# Uncomment after discord.py appears in pip.
# @bot.event
# async def on_raw_message_edit(payload):
#     if payload.cached_message:
#         return
#     message = bot.fe(payload.message_id)
#     target_id = bot.observables.get(message.guild.id, {}).get(message.channel.id)
#     if not target_id:
#         return
#     target = bot.get_channel(target_id)
#     content = (
#         f"{str(message.author)} performed edit on {message.edited_at.strftime('%m-%d-%Y %H:%M:%S')} UTC:\n"
#         f"New message:\n{message.content}\n"
#         f"Old message content unknown because I could not find it in my message cache. Sorry!"
#     )
#     attachments = await prepare_attachments(message)
#     await target.send(content, files=attachments)


bot.run(oeg('LOG_BOT_TOKEN'))
