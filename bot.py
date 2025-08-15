#!/usr/bin/env python3
import os
import re
import asyncio
from typing import Optional, Dict

import discord
from discord.ext import commands
from dotenv import load_dotenv

import wavelink

# ----------------------------------
# Environment / Config
# ----------------------------------
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
LAVALINK_URI = os.getenv("LAVALINK_URI", "http://127.0.0.1:2333")  # 127.0.0.1 is safest on Windows
LAVALINK_PASS = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.voice_states = True
INTENTS.guilds = True

bot = commands.Bot(command_prefix="!", intents=INTENTS, help_command=commands.DefaultHelpCommand())

# Track players per guild (avoid attaching attributes to Guild objects)
MUSIC_PLAYERS: Dict[int, "MusicPlayer"] = {}

# ----------------------------------
# Helpers / Types
# ----------------------------------
YOUTUBE_QUERY_PREFIX = "ytsearch:"
YTM_QUERY_PREFIX = "ytmsearch:"
URL_RX = re.compile(r"https?://")

class Track(wavelink.Playable):
    pass

class MusicPlayer(wavelink.Player):
    """Custom player that keeps its own FIFO queue separate from Wavelink's internal .queue."""
    track_queue: asyncio.Queue  # our own queue to avoid clobbering wavelink.Player.queue

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.track_queue = asyncio.Queue()
        self.loop = False

    async def add(self, track: Track):
        await self.track_queue.put(track)

    async def play_next(self):
        # If looping, replay the current track
        if self.loop and self.current:
            await self.play(self.current)
            return
        try:
            track = await asyncio.wait_for(self.track_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            await self.stop()
            return
        await self.play(track)

# ----------------------------------
# Lavalink Connection (Pool API)
# ----------------------------------
async def connect_nodes():
    print(f"Connecting to Lavalink at {LAVALINK_URI} ...")
    node = wavelink.Node(
        uri=LAVALINK_URI,
        password=LAVALINK_PASS
    )
    await wavelink.Pool.connect(client=bot, nodes=[node])
    print("✅ Pool.connect() finished.")

# ----------------------------------
# Events
# ----------------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    try:
        if not wavelink.Pool.nodes:
            await connect_nodes()
    except Exception as e:
        print(f"❌ Lavalink connection failed: {e}")
    print("Lavalink nodes:", list(wavelink.Pool.nodes.keys()) or "none")

@bot.event
async def on_wavelink_node_ready(node: wavelink.Node):
    print(f"Lavalink node ready: {node.identifier}")

@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    player: MusicPlayer = payload.player  # type: ignore
    if not player:
        return
    if payload.reason == "replaced":
        return
    await player.play_next()

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f"Missing argument: `{error.param.name}`. Try `!help {ctx.command.qualified_name}`.")
        return
    if isinstance(error, commands.CommandInvokeError) and error.original:
        await ctx.reply(f"Error: `{type(error.original).__name__}: {error.original}`")
    else:
        await ctx.reply(f"Error: `{type(error).__name__}: {error}`")

# ----------------------------------
# Voice / Search
# ----------------------------------
async def ensure_voice(ctx: commands.Context) -> Optional[MusicPlayer]:
    author_vc = getattr(ctx.author, "voice", None)
    if not author_vc or not author_vc.channel:
        await ctx.reply("You need to be **in a voice channel** first.")
        return None

    if not wavelink.Pool.nodes:
        try:
            await connect_nodes()
        except Exception as e:
            await ctx.reply(f"Could not connect to Lavalink: `{e}`")
            return None

    player: Optional[MusicPlayer] = None
    if ctx.guild.voice_client and isinstance(ctx.guild.voice_client, MusicPlayer):
        player = ctx.guild.voice_client  # type: ignore
    elif ctx.guild.id in MUSIC_PLAYERS:
        player = MUSIC_PLAYERS.get(ctx.guild.id)

    try:
        if player and player.channel and player.channel.id != author_vc.channel.id:  # type: ignore
            await player.move_to(author_vc.channel)  # type: ignore
        elif not player:
            player = await author_vc.channel.connect(cls=MusicPlayer)  # type: ignore
            MUSIC_PLAYERS[ctx.guild.id] = player
    except discord.Forbidden:
        await ctx.reply("I don’t have permission to **Connect**/**Speak** in that voice channel.")
        return None
    except discord.HTTPException as e:
        await ctx.reply(f"Discord voice connection failed: `{e}`")
        return None
    except Exception as e:
        await ctx.reply(f"Unexpected voice error: `{type(e).__name__}: {e}`")
        return None

    if not player or not player.channel:
        await ctx.reply("Failed to connect to voice (unknown state).")
        return None

    return player

async def search_tracks(query: str) -> list[Track]:
    if URL_RX.match(query):
        result = await wavelink.Pool.fetch_tracks(query)
    else:
        result = await wavelink.Pool.fetch_tracks(f"{YTM_QUERY_PREFIX}{query}")
        if not result or result == []:
            result = await wavelink.Pool.fetch_tracks(f"{YOUTUBE_QUERY_PREFIX}{query}")

    tracks: list[Track] = []
    if hasattr(result, "tracks"):  # playlist
        tracks.extend(result.tracks)  # type: ignore
    elif isinstance(result, list):
        tracks.extend(result)  # type: ignore
    else:
        if result:
            tracks.append(result)  # type: ignore
    return tracks

# ----------------------------------
# Commands
# ----------------------------------
@bot.command(name="join", help="Join your voice channel")
async def join(ctx: commands.Context):
    player = await ensure_voice(ctx)
    if player:
        await ctx.reply(f"Joined **{player.channel.name}**")  # type: ignore

@bot.command(name="play", help="Play a song by name or URL")
async def play(ctx: commands.Context, *, query: str):
    player = await ensure_voice(ctx)
    if not player:
        return

    tracks = await search_tracks(query)
    if not tracks:
        await ctx.reply("No results found.")
        return

    for t in tracks:
        await player.add(t)

    # Some builds expose a boolean .playing instead of is_playing()
    if not getattr(player, "playing", False):
        await player.play_next()

    if len(tracks) == 1:
        t = tracks[0]
        await ctx.reply(f"Queued **{t.title}** by **{t.author}**")
    else:
        await ctx.reply(f"Queued {len(tracks)} tracks.")

@bot.command(name="pause", help="Pause playback")
async def pause(ctx: commands.Context):
    player: MusicPlayer = ctx.voice_client  # type: ignore
    if not player:
        return await ctx.reply("Not connected.")
    await player.pause(True)   # explicitly pause for compatibility
    await ctx.reply("Paused ⏸️")

@bot.command(name="resume", help="Resume playback")
async def resume(ctx: commands.Context):
    player: MusicPlayer = ctx.voice_client  # type: ignore
    if not player:
        return await ctx.reply("Not connected.")
    await player.pause(False)  # explicitly resume for compatibility
    await ctx.reply("Resumed ▶️")

@bot.command(name="skip", help="Skip current track")
async def skip(ctx: commands.Context):
    player: MusicPlayer = ctx.voice_client  # type: ignore
    if not player or not player.current:
        return await ctx.reply("Nothing playing.")
    await player.stop()
    await ctx.reply("Skipped ⏭️")

@bot.command(name="stop", help="Stop and clear the queue")
async def stop(ctx: commands.Context):
    player: MusicPlayer = ctx.voice_client  # type: ignore
    if not player:
        return await ctx.reply("Not connected.")
    try:
        while True:
            player.track_queue.get_nowait()
    except Exception:
        pass
    await player.stop()
    await ctx.reply("Stopped and cleared the queue ⏹️")

@bot.command(name="np", help="Show the currently playing track")
async def now_playing(ctx: commands.Context):
    player: MusicPlayer = ctx.voice_client  # type: ignore
    if not player or not player.current:
        return await ctx.reply("Nothing playing.")
    t = player.current
    await ctx.reply(f"Now playing: **{t.title}** by **{t.author}** [{t.length // 1000}s]")

@bot.command(name="queue", help="Show next few tracks in queue")
async def queue_cmd(ctx: commands.Context):
    player: MusicPlayer = ctx.voice_client  # type: ignore
    if not player:
        return await ctx.reply("Not connected.")
    if player.track_queue.empty():
        return await ctx.reply("Queue is empty.")
    # Snapshot our asyncio.Queue without consuming
    items = list(player.track_queue._queue)  # type: ignore
    lines = []
    for i, t in enumerate(items[:10], start=1):
        lines.append(f"{i}. {t.title} — {t.author}")
    extra = player.track_queue.qsize() - len(lines)
    more = f"\n...and {extra} more" if extra > 0 else ""
    await ctx.reply("**Up next:**\n" + "\n".join(lines) + more)

@bot.command(name="vol", help="Set volume (0-1000)")
async def volume(ctx: commands.Context, vol: Optional[int] = None):
    player: MusicPlayer = ctx.voice_client  # type: ignore
    if not player:
        return await ctx.reply("Not connected.")
    if vol is None:
        return await ctx.reply(f"Current volume: {player.volume}")
    vol = max(0, min(vol, 1000))
    await player.set_volume(vol)
    await ctx.reply(f"Volume set to {vol}")

@bot.command(name="seek", help="Seek to position in seconds (e.g., !seek 90)")
async def seek(ctx: commands.Context, seconds: int):
    player: MusicPlayer = ctx.voice_client  # type: ignore
    if not player or not player.current:
        return await ctx.reply("Nothing playing.")
    ms = max(0, seconds * 1000)
    await player.seek(ms)
    await ctx.reply(f"Seeked to {seconds}s ⏩")

@bot.command(name="loop", help="Toggle loop of the current track")
async def loop_cmd(ctx: commands.Context):
    player: MusicPlayer = ctx.voice_client  # type: ignore
    if not player:
        return await ctx.reply("Not connected.")
    player.loop = not getattr(player, "loop", False)
    await ctx.reply(f"Loop is now **{'ON' if player.loop else 'OFF'}**")

@bot.command(name="leave", aliases=["disconnect"], help="Disconnect the bot from voice")
async def leave(ctx: commands.Context):
    if ctx.voice_client:
        await ctx.voice_client.disconnect(force=True)
        await ctx.reply("Disconnected.")
    else:
        await ctx.reply("I'm not in a voice channel.")

@bot.command(name="status", help="Show Lavalink/node and voice status")
async def status(ctx: commands.Context):
    node_ids = list(wavelink.Pool.nodes.keys())
    vc = ctx.guild.voice_client
    await ctx.reply(
        "Nodes: " + (", ".join(node_ids) if node_ids else "none") +
        f"\nConnected to voice: {'yes' if vc and vc.is_connected() else 'no'}" +
        (f"\nCurrent channel: {vc.channel.name}" if vc and vc.channel else "")
    )

# ----------------------------------
# Entrypoint
# ----------------------------------
async def main():
    if not TOKEN:
        raise SystemExit("Please set DISCORD_TOKEN in your environment or .env file.")
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
