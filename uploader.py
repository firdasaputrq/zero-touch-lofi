import os
import json

# === GITHUB ACTIONS: Load credentials dari environment variable ===
if os.environ.get("YOUTUBE_CLIENT_SECRET"):
    with open("client_secret.json", "w") as f:
        f.write(os.environ["YOUTUBE_CLIENT_SECRET"])

if os.environ.get("YOUTUBE_TOKEN"):
    with open("token.json", "w") as f:
        f.write(os.environ["YOUTUBE_TOKEN"])
# ================================================================

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

VIDEO_FILE    = "final_video.mp4"
CHANNEL_NAME  = "Driftory"

TITLE_TEMPLATES = {
    "minor": [
        "🎧 {hook} - 1 Hour Lofi Beats for Sleep & Relaxation | {channel}",
        "🌙 {hook} - Lofi Hip Hop Mix 1 Hour | Chill & Unwind | {channel}",
        "✨ {hook} - 1 Hour Relaxing Lofi Music | Sleep & Calm | {channel}",
    ],
    "dorian": [
        "🎯 {hook} - 1 Hour Lofi Beats for Study & Focus | {channel}",
        "📖 {hook} - Lofi Hip Hop Study Mix 1 Hour | Deep Focus | {channel}",
        "💻 {hook} - 1 Hour Focus Lofi Music | Study & Work | {channel}",
    ],
    "major": [
        "☀️ {hook} - 1 Hour Feel Good Lofi Beats | Chill Vibes | {channel}",
        "🌸 {hook} - Happy Lofi Mix 1 Hour | Good Vibes Only | {channel}",
        "🎶 {hook} - 1 Hour Uplifting Lofi Music | Relax & Smile | {channel}",
    ],
}

DESC_MOODS = {
    "minor":  ("sleep, late night sessions, and unwinding",    "lofi sleep, calm lofi, relaxing lofi beats"),
    "dorian": ("studying, deep work, and staying productive",   "lofi study, focus music, lofi for work"),
    "major":  ("brightening your day and feeling good",         "happy lofi, feel good beats, uplifting lofi"),
}

def load_hook():
    try:
        with open("hook.txt", "r", encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        hook       = lines[0] if len(lines) > 0 else "lofi beats to relax"
        scale_type = lines[1] if len(lines) > 1 else "minor"
        bpm        = lines[2] if len(lines) > 2 else "76"
    except FileNotFoundError:
        hook, scale_type, bpm = "lofi beats to relax", "minor", "76"
    return hook, scale_type, bpm

def build_metadata(hook, scale_type, bpm):
    import random
    title = random.choice(TITLE_TEMPLATES.get(scale_type, TITLE_TEMPLATES["minor"])).format(
        hook=hook, channel=CHANNEL_NAME
    )
    mood_desc, mood_tags = DESC_MOODS.get(scale_type, DESC_MOODS["minor"])

    description = f"""🎶 {hook} – 1 Hour of Lofi Beats by {CHANNEL_NAME}

Perfect for {mood_desc}.

Welcome to {CHANNEL_NAME} 🎧 — your daily source for fresh, AI-generated lofi music.
Every track is uniquely composed: different key, BPM ({bpm} BPM this session), mood, and vibe.
No two uploads are the same.

This mix is great for:
📚 Studying & Homework
💻 Deep Work & Productivity
🌙 Late Night Sessions
😴 Sleep & Relaxation
🌿 Stress Relief & Mindfulness

✨ Subscribe to {CHANNEL_NAME} for fresh lofi beats every day.
👍 Like this track if it helped you focus or unwind.
🔔 Turn on notifications so you never miss a drop.

Press play. Drift away. 🌊

#{CHANNEL_NAME.lower()} #lofi #lofihiphop #studymusic #chillbeats #focusmusic #sleepmusic #relaxingmusic #lofibeats #chillhop #backgroundmusic #1hourlofi #instrumental #calmmusic"""

    tags = [
        "1 hour lofi", "lofi hip hop", "lofi beats", "study music",
        "chill beats", "focus music", "sleep music", "relaxing music",
        "lofi mix", "background music", "lofi vibes", "chillhop",
        "instrumental", "calm music", CHANNEL_NAME,
        f"{bpm} bpm lofi", "lofi 2025",
    ]
    return title, description, tags

def load_credentials():
    creds = Credentials.from_authorized_user_file("token.json")
    if creds.expired and creds.refresh_token:
        print("🔄 Refreshing token...")
        creds.refresh(Request())
        with open("token.json", "w") as f:
            f.write(creds.to_json())
        print("✅ Token refreshed")
    return creds

def upload_video():
    hook, scale_type, bpm = load_hook()
    title, description, tags = build_metadata(hook, scale_type, bpm)
    print(f"📤 Uploading: {title}")
    creds   = load_credentials()
    youtube = build("youtube", "v3", credentials=creds)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title":       title,
                "description": description,
                "tags":        tags,
                "categoryId":  "10",
            },
            "status": {"privacyStatus": "public"},
        },
        media_body=MediaFileUpload(VIDEO_FILE, resumable=True)
    )
    response = request.execute()
    print(f"✅ Uploaded! https://youtube.com/watch?v={response['id']}")

if __name__ == "__main__":
    upload_video()
