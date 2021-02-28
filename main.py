import ast
import asyncio
import os

import discord
from discord.ext import commands
from discord_slash import SlashCommand
from discord_slash.utils import manage_commands  # Allows us to manage the command settings.
from replit import db

bot = commands.Bot("tag ", intents=discord.Intents.all())
slash = SlashCommand(bot, sync_commands=True)

guild_ids = [732924162951086080, 494911447420108820, 674500858054180874]

if "tags" in db.keys():
    tag_list = set(db["tags"].split(","))
else:
    tag_list = set()
    db["tags"] = ""
def get_tag(channel):
    topic = channel.topic
    tags = str(topic).splitlines()[-1]
    if not tags.startswith("タグ: "):
        tags = []
    else:
        tags = {s.strip() for s in tags[4:].split(", ")}
        topic = "\n".join(str(topic).splitlines()[:-2])
    return topic, set(tags)


def is_issue(channel):
    if not channel.category:
        return False
    return channel.category.name.startswith(("🔔", "✅"))


def tag_didyoumean(name):
    tag_list


@bot.event
async def on_ready():
    print("Ready!")


@slash.slash(name="add",
             description="チャンネルにタグを追加します。",
             options=[
                 manage_commands.create_option(
                     name="Name",
                     description="追加するタグの名前。カンマ区切りで入力できます。",
                     option_type=3,
                     required=True)
             ],
             guild_ids=guild_ids)
async def _add(ctx, name: str):
    if not ctx.author.guild_permissions.manage_channels:
        await ctx.respond(eat=True)
        return await ctx.send("チャンネルの管理権限が必要です。", hidden=True)
    elif not is_issue(ctx.channel):
        await ctx.respond(eat=True)
        return await ctx.send("Issueのチャンネルで実行して下さい。", hidden=True)
    elif not set(name.split(",")) & tag_list:
        await ctx.respond(eat=True)
        return await ctx.send("タグが見つかりません。", hidden=True)
        
    await ctx.respond(eat=False)
    topic, tags = get_tag(ctx.channel)
    before_tags = tags
    tags |= set(name.split(",")) & tag_list
    tags = list(set(tags))

    try:
        await asyncio.wait_for(
            ctx.channel.edit(topic=topic + "\n\nタグ: " + ", ".join(tags)), 5)
        added_tags = tags - before_tags
        new_tags = "@ 現在のタグ\n"
        for t in tags:
            if t in added_tags:
                new_tags += "+ "
            new_tags += t + "\n"
        new_tags += "@ 無視されたタグ\n"
        for t in set(name.split(",")) - added_tags:
            new_tags += "- " + t + "\n"
        await ctx.send(f'{len(set(name.split(",")) & tag_list)}個のタグを追加しました。\n```diff\n' + new_tags + "```", hidden=True)
    except asyncio.TimeoutError:
        await ctx.send("レート制限により、タグを追加できませんでした。", hidden=True)

@slash.slash(name="remove",
             description="チャンネルからタグを外します。",
             options=[
                 manage_commands.create_option(name="Name",
                                               description="削除するタグの名前。",
                                               option_type=3,
                                               required=True)
             ],
             guild_ids=guild_ids)
async def _remove(ctx, name: str):
    if not ctx.author.guild_permissions.manage_channels:
        await ctx.respond(eat=True)
        return await ctx.send("チャンネルの管理権限が必要です。", hidden=True)
    elif not is_issue(ctx.channel):
        await ctx.respond(eat=True)
        return await ctx.send("Issueのチャンネルで実行して下さい。", hidden=True)
    await ctx.respond(eat=False)
    topic, tags = get_tag(ctx.channel)

    tags = set(tags) - set(name.split(","))

    # await ctx.respond(eat=False)
    try:
        await asyncio.wait_for(
            ctx.channel.edit(topic=topic + "\n\nタグ: " + ", ".join(tags)), 5)
        await ctx.send("タグを削除しました。", hidden=True)
    except asyncio.TimeoutError:
        await ctx.send("レート制限により、タグを削除できませんでした。", hidden=True)


@slash.slash(name="find",
             description="Issueをタグから絞り込みます。",
             options=[
                 manage_commands.create_option(
                     name="Name",
                     description="タグの名前。カンマ区切りで入力できます。",
                     option_type=3,
                     required=True),
                 manage_commands.create_option(
                     name="Show",
                     description="結果を全員に表示させるか。省略でFalseになります。",
                     option_type=5,
                     required=False)
             ],
             guild_ids=guild_ids)
async def _find(ctx, name: str, show: bool = False):
    try:
        await ctx.respond(eat=not show)
    except discord.errors.NotFound:
        pass
    issues = list(filter(is_issue, ctx.guild.text_channels))
    res = "> **当てはまったチャンネル**\n"
    for i in issues:
        _, tags = get_tag(i)
        if set(name.split(",")) & tags != set(name.split(",")):
            continue
        bres = res
        res += i.mention + "\n"
        if len(res) > 2000:
            await ctx.send(bres, hidden=not show)
            res = i.mention + "\n"
    if res == "> **当てはまったチャンネル**\n":
        await ctx.send(res + "何も見付かりませんでした。", hidden=not show)
    else:
        await ctx.send(res, hidden=not show)
        
@slash.slash(name="new",
             description="新しいタグを作成します。",
             options=[
                 manage_commands.create_option(name="Name",
                                               description="作成するタグの名前。",
                                               option_type=3,
                                               required=True)
             ],
             guild_ids=guild_ids)
async def _new(ctx, name: str):
    if not ctx.author.guild_permissions.manage_channels:
        await ctx.respond(eat=True)
        return await ctx.send("チャンネルの管理権限が必要です。", hidden=True)
    await ctx.respond(eat=True)
    tag_list.add(name)
    db["tags"] = ",".join(tag_list)
    await ctx.send("タグを作成しました。", hidden=True)

@slash.slash(name="list",
             description="タグ一覧を表示します。",
             guild_ids=guild_ids)
async def _list(ctx):
    await ctx.respond(eat=True)
    res = "> **タグ一覧**\n"
    for i in tag_list:
        if not i:
            continue
        bres = res
        res += "`" + i + "`, "
        if len(res) > 2000:
            await ctx.send(bres, hidden=True)
            res = "`" + i + "`, "
        
    await ctx.send(res.rstrip(", "), hidden=True)
    
@slash.slash(name="delete",
             description="タグを削除します。",
             options=[
                 manage_commands.create_option(name="Name",
                                               description="作成するタグの名前。",
                                               option_type=3,
                                               required=True)
             ],
             guild_ids=guild_ids)
async def _delete(ctx, name: str):
    if not ctx.author.guild_permissions.manage_channels:
        await ctx.respond(eat=True)
        return await ctx.send("チャンネルの管理権限が必要です。", hidden=True)
    elif name not in tag_list:
        await ctx.respond(eat=True)
        return await ctx.send("タグが含まれていません。", hidden=True)
    await ctx.respond(eat=True)
    
    tag_list.remove(name)
    await ctx.send("タグを削除しました。", hidden=True)

bot.run(os.getenv("token"))
