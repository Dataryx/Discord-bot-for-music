# Discord Music Bot (YouTube + Lavalink v4)

A ready-to-run Discord music bot using **discord.py + Wavelink + Lavalink v4**.

## Features
- `!join`, `!play`, `!pause`, `!resume`, `!skip`, `!stop`, `!np`, `!queue`, `!vol`, `!seek`, `!loop`, `!leave`
- Works with **YouTube/YouTube Music** searches (`!play youtube link`)
- Accepts **Spotify/Apple** links if you add the **LavaSrc** plugin

## Prereqs
- Python 3.10+ (works on 3.13)
- Docker Desktop (for Lavalink) or Java 17+ (to run Lavalink JAR)
- A Discord bot token with **Message Content Intent** enabled

## Quick Start

### 1) Lavalink (Docker)
```bash
docker compose up -d
docker logs -f lavalink
```

> Put the **YouTube plugin JAR** (and optional **LavaSrc JAR**) into `lavalink/plugins/` before starting.  
> YouTube plugin releases: https://github.com/lavalink-devs/youtube-source/releases  
> LavaSrc releases: https://github.com/topi314/LavaSrc/releases

### 2) Bot
```bash
python -m venv .venv
# Windows PowerShell:
. .\.venv\Scripts\Activate.ps1
# Git Bash:
source .venv/Scripts/activate

pip install -r requirements.txt
cp .env.example .env
# edit .env and set DISCORD_TOKEN (and optional plugin creds)

python bot.py
```

### 3) Use in Discord
1. Invite the bot with scopes `bot` (and `applications.commands` if you later add slash commands).
2. Join a voice channel.
3. In a text channel:
```
!join
!play sunflower postmalone
```

## Troubleshooting
- **`PrivilegedIntentsRequired`**: enable **Message Content Intent** in the Dev Portal (Bot tab).
- **No audio / join fails**: check channel permissions (Connect/Speak) and that Lavalink is running.
- **`LavalinkLoadException` on search**: ensure the **YouTube plugin JAR** is present and `sources.youtube: false` in `application.yml`.
- **Attribute mismatches**: this bot targets Wavelink 3.x (`wavelink>=3.3,<4.0`).

