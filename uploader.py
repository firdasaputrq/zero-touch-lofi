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

VIDEO_FILE = "final_video.mp4"

def load_credentials():
    creds = Credentials.from_authorized_user_file("token.json")

    # Auto refresh jika token expired
    if creds.expired and creds.refresh_token:
        print("🔄 Token expired, refreshing...")
        creds.refresh(Request())
        # Simpan token yang sudah di-refresh
        with open("token.json", "w") as f:
            f.write(creds.to_json())
        print("✅ Token berhasil di-refresh")

    return creds

def upload_video():
    creds = load_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": "🎧 1 Hour Lofi Hip Hop Beat – Relaxing Study Music 🌙 | Chill Focus & Sleep | Zero Touch Music",
                "description": """🎶 1 Hour of Relaxing Lofi Hip Hop Beats for Study, Focus, and Sleep.
Welcome to Zero Touch Music 🎧 — your home for chill lofi vibes and peaceful background music.
This 1 hour lofi mix is perfect for:
📚 Studying & Homework
💻 Deep Focus & Productivity
🌙 Late Night Sessions
😴 Sleep & Relaxation
🌿 Stress Relief
If you're searching for:
lofi hip hop, 1 hour lofi beat, relaxing study music, chill beats for focus, calm background music, sleep lofi — this mix is made for you.
✨ Subscribe to Zero Touch Music for everyday lofi beats.
👍 Like & comment if this helped you focus.
🔔 Turn on notifications for more chill vibes.
Press play. Relax. Let the beat flow 🌊
#lofi 
#study 
#chill 
#ZeroTouchMusic
#1hourlofi
#lofihiphop
#lofibeats
#studymusic
#studybeats
#focusmusic
#sleepmusic
#relaxingmusic
#chillbeats
#instrumental
#backgroundmusic
#lofivibes
#calmmusic""",
                "tags": [
                    "1 hour lofi","1 hour lofi hip hop","1 hour lofi beat",
                    "lofi hip hop","lofi beats","lofi study music",
                    "study music 1 hour","study beats","chill beats",
                    "relaxing lofi","focus music","deep focus music",
                    "sleep lofi","calm background music","background music for studying",
                    "chillhop mix","instrumental hip hop","aesthetic lofi",
                    "late night lofi","Zero Touch Music"
                ],
                "categoryId": "10"
            },
            "status": {
                "privacyStatus": "public"
            }
        },
        media_body=MediaFileUpload(VIDEO_FILE, resumable=True)
    )

    response = request.execute()
    print("✅ Uploaded Video ID:", response["id"])

if __name__ == "__main__":
    upload_video()
