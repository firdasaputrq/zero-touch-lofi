import os
import json

# ================================================================
# GITHUB ACTIONS: Load credentials dari environment variable
# Harus di paling atas sebelum import library Google
# ================================================================
if os.environ.get("YOUTUBE_CLIENT_SECRET"):
    with open("client_secret.json", "w") as f:
        f.write(os.environ["YOUTUBE_CLIENT_SECRET"])
    print("✅ client_secret.json restored from env")

if os.environ.get("YOUTUBE_TOKEN"):
    with open("token.json", "w") as f:
        f.write(os.environ["YOUTUBE_TOKEN"])
    print("✅ token.json restored from env")
# ================================================================

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

VIDEO_FILE = "final_video.mp4"
META_FILE = "video_meta.json"
TOKEN_FILE = "token.json"


def load_credentials():
    """Load dan auto-refresh credentials dari token.json."""
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"❌ {TOKEN_FILE} tidak ditemukan. "
            "Pastikan secret YOUTUBE_TOKEN sudah diset di GitHub."
        )

    creds = Credentials.from_authorized_user_file(TOKEN_FILE)

    # Auto-refresh jika token expired
    if creds.expired and creds.refresh_token:
        print("🔄 Token expired, refreshing...")
        creds.refresh(Request())
        # Simpan token yang sudah di-refresh
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print("✅ Token refreshed successfully")

    return creds


def load_metadata():
    """Baca metadata video yang dihasilkan main.py."""
    if os.path.exists(META_FILE):
        with open(META_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
        print(f"✅ Loaded metadata: {meta['title'][:60]}...")
        return meta
    else:
        # Fallback metadata jika video_meta.json tidak ada
        print("⚠️  video_meta.json not found, using fallback metadata")
        return {
            "title": "🎧 1 Hour Lofi Hip Hop Beats – Relax & Study Music | Driftory",
            "description": """🎶 beats to drift & focus 🌙

Welcome to Driftory 🎧 — your daily generative lofi station.

✨ Subscribe for fresh beats every day.
👍 Like if this helped you focus.
🔔 Turn on notifications.

#lofi #studymusic #chillbeats #Driftory #lofihiphop""",
            "tags": [
                "1 hour lofi", "lofi hip hop", "study music",
                "focus music", "chill beats", "relaxing music",
                "background music", "lofi beats", "Driftory"
            ]
        }


def upload_video():
    if not os.path.exists(VIDEO_FILE):
        raise FileNotFoundError(f"❌ {VIDEO_FILE} tidak ditemukan. Pastikan main.py sudah jalan.")

    print("🔑 Loading credentials...")
    creds = load_credentials()

    print("📋 Loading video metadata...")
    meta = load_metadata()

    print("🔧 Building YouTube client...")
    youtube = build("youtube", "v3", credentials=creds)

    print(f"🚀 Uploading: {meta['title'][:60]}...")
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": meta["title"],
                "description": meta["description"],
                "tags": meta.get("tags", []),
                "categoryId": "10",  # Music category
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            }
        },
        media_body=MediaFileUpload(VIDEO_FILE, resumable=True, chunksize=10 * 1024 * 1024)
    )

    # Resumable upload dengan progress
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"   Upload progress: {pct}%")

    video_id = response["id"]
    print(f"✅ Upload berhasil!")
    print(f"   Video ID : {video_id}")
    print(f"   URL      : https://www.youtube.com/watch?v={video_id}")
    print(f"   Scale    : {meta.get('scale', 'N/A')} | Root: {meta.get('root', 'N/A')} | BPM: {meta.get('bpm', 'N/A')}")
    print(f"   Hook     : {meta.get('hook', 'N/A')}")

    return video_id


if __name__ == "__main__":
    upload_video()
