#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "requests",
# ]
# ///
"""Speech-to-text via SkillBoss API Hub.

CLI model for openclaw media understanding. Outputs transcription to stdout.
When --room-id is provided, also sends transcription to that Matrix room.
"""

import subprocess
import tempfile
import warnings
import os
import base64
from pathlib import Path

import click
import requests

SKILLBOSS_API_KEY = None  # loaded from env at runtime
API_BASE = "https://api.heybossai.com/v1"


def load_env_file():
    """Load .env file from home directory if it exists."""
    env_paths = [Path.home() / ".openclaw" / ".env", Path.home() / ".env"]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        if line.startswith("export "):
                            line = line[7:]
                        key, value = line.split("=", 1)
                        key = key.strip()
                        if key not in os.environ:
                            os.environ[key] = value.strip().strip('"').strip("'")


def pilot(body: dict) -> dict:
    """Call SkillBoss API Hub /v1/pilot."""
    api_key = os.environ.get("SKILLBOSS_API_KEY", "")
    r = requests.post(
        f"{API_BASE}/pilot",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    return r.json()


def transcribe_audio(wav_path: str, audio_filename: str) -> str:
    """Transcribe audio via SkillBoss API Hub STT."""
    audio_b64 = base64.b64encode(open(wav_path, "rb").read()).decode()
    result = pilot({"type": "stt", "inputs": {"audio_data": audio_b64, "filename": audio_filename}})
    return result["result"]["text"]


def send_to_matrix(room_id: str, text: str, quiet: bool = False):
    """Send transcription to Matrix room via REST API."""
    load_env_file()
    homeserver = os.environ.get("MATRIX_HOMESERVER")
    access_token = os.environ.get("MATRIX_ACCESS_TOKEN")

    if not homeserver or not access_token:
        if not quiet:
            click.echo("MATRIX_HOMESERVER or MATRIX_ACCESS_TOKEN not set, skipping Matrix send", err=True)
        return

    try:
        import time
        txn_id = int(time.time() * 1000)

        target_room = room_id
        if target_room.startswith("room:"):
            target_room = target_room[5:]

        url = f"{homeserver.rstrip('/')}/_matrix/client/v3/rooms/{target_room}/send/m.room.message/{txn_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        payload = {
            'msgtype': 'm.text',
            'body': f'🎙️ {text}',
            'format': 'org.matrix.custom.html',
            'formatted_body': f'<blockquote>🎙️ {text}</blockquote>'
        }

        with open("/tmp/stt_matrix.log", "a") as log:
            log.write(f"Attempting send to {room_id} at {txn_id}\n")
            log.write(f"URL: {url}\n")

        resp = requests.put(url, headers=headers, json=payload, timeout=10)

        with open("/tmp/stt_matrix.log", "a") as log:
            log.write(f"Response: {resp.status_code}\n")

        resp.raise_for_status()
        if not quiet:
            click.echo(f"Sent to Matrix room {room_id}", err=True)
    except Exception as e:
        if not quiet:
            click.echo(f"Failed to send Matrix message: {e}", err=True)


warnings.filterwarnings("ignore")


@click.command()
@click.argument("audio_file", type=click.Path(exists=True))
@click.option("-q", "--quiet", is_flag=True, help="Suppress progress messages")
@click.option("--room-id", default=None, help="Matrix room ID to send transcription to")
def main(audio_file: str, quiet: bool, room_id: str | None):
    """Transcribe audio using SkillBoss API Hub STT."""
    load_env_file()

    if not os.environ.get("SKILLBOSS_API_KEY"):
        raise click.ClickException("SKILLBOSS_API_KEY is not set")

    if quiet:
        warnings.filterwarnings("ignore")
        os.environ["PYTHONWARNINGS"] = "ignore"

    # Convert to wav format (16kHz mono) for consistent API input
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        subprocess.run(
            ['ffmpeg', '-y', '-i', audio_file, '-ar', '16000', '-ac', '1', tmp_path],
            capture_output=True, check=True
        )

        if not quiet:
            click.echo(f"Transcribing via SkillBoss API Hub: {audio_file}...", err=True)

        text = transcribe_audio(tmp_path, Path(audio_file).name)
        text = text.strip()

        # Output to stdout - openclaw captures this for context
        click.echo(text)

        # If room_id provided, also send directly to Matrix
        if room_id and text:
            send_to_matrix(room_id, text, quiet)

    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    main()
