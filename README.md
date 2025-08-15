# Discord Music Bot (YouTube, YouTube Music, Spotify, Apple Music)

A simple, **workable** Discord music bot using **discord.py + Wavelink (Lavalink v4)**.

- ✅ Plays from **YouTube** and **YouTube Music** out of the box
- ✅ Accepts **Spotify** and **Apple Music** links via Lavalink's **LavaSrc** plugin (optional setup below)
- ✅ Commands: `!join`, `!play <query|url>`, `!pause`, `!resume`, `!skip`, `!stop`, `!np`, `!queue`, `!vol <0-1000>`, `!seek <seconds>`, `!loop`, `!leave`

## 1) Prerequisites
- Python 3.10+
- Docker + Docker Compose
- A Discord bot token (create at https://discord.com/developers/applications and enable **MESSAGE CONTENT INTENT**)

## 2) Setup Lavalink (audio backend)

```bash
# from project root
docker compose up -d
```

This launches **Lavalink v4** on `localhost:2333` with password `youshallnotpass` using `lavalink/application.yml`.

### (Optional) Enable Spotify & Apple Music link support
Lavalink can resolve Spotify/Apple URLs via the **LavaSrc** plugin.

```bash
# Download the latest lavasrc plugin jar into the plugins folder
mkdir -p lavalink/plugins
curl -L -o lavalink/plugins/lavasrc-plugin.jar \
  https://github.com/lavalink-devs/lavalink-plugins/releases/latest/download/lavasrc-plugin.jar

# Restart Lavalink
docker compose up -d --force-recreate
```

If you have credentials, add them to `.env` (optional but improves reliability):
```
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
APPLE_MUSIC_MEDIA_TOKEN=...
```

> Without credentials, many Spotify/Apple links still resolve by searching YouTube/YouTube Music equivalents via LavaSrc.

## 3) Bot setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# copy and edit env
cp .env.example .env
# put your Discord token in DISCORD_TOKEN=...
```

## 4) Invite the bot to your server
On the Discord Developer Portal, create an OAuth2 URL with these scopes/permissions:
- Scopes: `bot`
- Bot Permissions: `Connect`, `Speak`, `View Channel`, `Send Messages` (and `Use Slash Commands` if you later add app commands)

Invite the bot using that URL.

## 5) Run the bot

Make sure Lavalink is up (`docker compose ps`). Then start the bot:

```bash
python bot.py
```

## 6) Use it!
In any text channel:
```
!join
!play never gonna give you up
!play https://music.youtube.com/watch?v=...
!play https://open.spotify.com/track/...
!play https://music.apple.com/us/album/...
```

## Notes & Troubleshooting
- If the bot doesn't connect, check:
  - Your Discord token and the **MESSAGE CONTENT INTENT** is enabled.
  - Lavalink logs: `docker logs -f lavalink`
  - Ports 2333/2334 open locally.
- Volume 0-1000: Lavalink allows amplification; keep sensible values to avoid clipping.
- Seeking may not work on live streams.
- This bot uses **prefix commands** (`!play`). You can easily add slash commands via `discord.app_commands` later.
- For production, consider hosting Lavalink on a VM and setting `LAVALINK_URI` to that host.

Happy listening! 🎵
