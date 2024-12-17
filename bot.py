import yt_dlp
import asyncio
import os
import time
import discord
from typing import Any
from dataclasses import dataclass
from discord.ext import commands
from discord.utils import get

@dataclass
class queue_item:
    youtube_url: str = ""
    output_file: str = ""
    download_task: Any = None
    ctx: Any = None


queue = []


def next_file():
    if not os.path.isdir("./audio"):
        os.mkdir("./audio")
    return f"./audio/{time.time_ns()}"


async def download_audio(youtube_url, output_file):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_file,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [youtube_url])


async def queue_push(youtube_url, ctx):
    print("[queue_push] start")
    q = queue_item()
    queue.append(q)
    print(f"[queue_push] {len(queue)} items in queue")
    q.youtube_url = youtube_url
    q.output_file = next_file()
    print(f"[queue_push] starting download")
    q.download_task = asyncio.create_task(download_audio(q.youtube_url, q.output_file))
    q.ctx = ctx
    await asyncio.sleep(0)
    print(f"[queue_push] done")
    return len(queue)

def cleanup_files():
    for f in os.listdir("./audio"):
        found = False
        for q in queue:
            print(f"[cleanup_files] checking {q.output_file}.mp3 against {f}")
            if f"{q.output_file}.mp3" == f"./audio/{f}":
                found = True
                break
        if not found:
            print(f"[cleanup_files] removing: ./audio/{f}")
            os.remove(f"./audio/{f}")

# setup bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def ensure_voice_channel(ctx):
    if ctx.author.voice and ctx.author.voice.channel:
        return ctx.author.voice.channel
    await ctx.send("You need to be in a voice channel.")
    return None

# !skip
@bot.command()
async def skip(ctx):
    # garbage collection
    try: cleanup_files()
    except Exception: pass

    vc = get(bot.voice_clients, guild=ctx.guild)

    # wait for download next item in queue
    if len(queue) == 0:
        print("[skip] queue is empty: stopping")
        await ctx.send(f"Queue is now empty: bye bye !")
        if vc and vc.is_connected(): await vc.disconnect(force=True)
        return
    q = queue[0]
    print(f"[skip] waiting for download: {q.youtube_url}")
    await q.download_task
    queue.pop(0)

    # connect to voice
    print(f"[skip] connecting to voice")
    channel = await ensure_voice_channel(q.ctx)
    if channel is None:
        await q.ctx.send(f"Cannot play `{q.youtube_url}`: you are not in a voice channel.")
        return

    if not vc or not vc.is_connected():
        vc = await channel.connect()
    else:
        await vc.disconnect(force=True)
        vc = await channel.connect()
        await vc.move_to(channel)

    await q.ctx.send(f"Now playing: `{q.youtube_url}`.")
    print(f"[skip] starting playback: {q.output_file}")
    vc.play(discord.FFmpegPCMAudio(f"{q.output_file}.mp3"), after=lambda e: bot.loop.create_task(skip(q.ctx)))


# !play <youtube-url>
@bot.command()
async def play(ctx, yt_url: str):
    print("[play] starting")

    # immediately queue requested URL
    await queue_push(yt_url, ctx)

    vc = get(bot.voice_clients, guild=ctx.guild)
    if (not vc or not vc.is_connected() or not vc.is_playing()) and len(queue) == 1:
        # queue was empty: immediately move to next song
        print("[play] queue is empty: skipping to next song now")
        await skip(ctx)
    else:
        print("[play] queue is not empty: waiting for current song to finish")
        await ctx.send(f"OK ! adding `{yt_url}` to the queue.")


bot.run(os.environ["BOT_TOKEN"])

