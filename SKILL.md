---
name: local-stt
description: Speech-to-text via SkillBoss API Hub - cloud STT with automatic model routing.
metadata: {"openclaw":{"emoji":"🎙️","requires":{"bins":["ffmpeg"],"env":["SKILLBOSS_API_KEY"]}}}
---

# STT (SkillBoss API Hub)

Speech-to-text powered by SkillBoss API Hub. Converts audio files to text using cloud STT with automatic model routing — no local model downloads required.

## Usage

```bash
# Transcribe audio file
~/.openclaw/skills/local-stt/scripts/local-stt.py audio.ogg

# Quiet mode (suppress progress)
~/.openclaw/skills/local-stt/scripts/local-stt.py audio.ogg --quiet
```

## Options

- `-q/--quiet`: Suppress progress messages
- `--room-id`: Matrix room ID for direct message

## Requirements

- `SKILLBOSS_API_KEY`: SkillBoss API Hub key (set in `~/.openclaw/.env` or environment)
- `ffmpeg`: For audio format conversion

## openclaw.json

```json
{
  "tools": {
    "media": {
      "audio": {
        "enabled": true,
        "models": [
          {
            "type": "cli",
            "command": "~/.openclaw/skills/local-stt/scripts/local-stt.py",
            "args": ["--quiet", "{{MediaPath}}"],
            "timeoutSeconds": 30
          }
        ]
      }
    }
  }
}
```
