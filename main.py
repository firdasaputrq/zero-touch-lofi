# ==========================================================
# DRIFTORY - GENERATIVE LOFI ENGINE (GITHUB VERSION)
# Auto Generates 1 Hour Lofi Video with Dynamic Hook Text
# ==========================================================

import numpy as np
import soundfile as sf
import random
import os
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont

# ===================== CONFIG =====================
SR = 44100
FINAL_DURATION = 3600   # detik (ganti ke 300 untuk testing 5 menit)
BASE_MINUTES = 8        # menit base audio (ganti ke 5 untuk testing)
OUTPUT_AUDIO = "lofi_output.wav"
OUTPUT_VIDEO = "final_video.mp4"
CHANNEL_NAME = "Driftory"
WIDTH, HEIGHT = 1920, 1080
FPS = 24

# ===================== SCALE & HOOK SYSTEM =====================

SCALE_CONFIGS = {
    "minor": {
        "intervals": [0, 2, 3, 5, 7, 8, 10],
        "mood": "melancholic",
        "hook_pool": [
            "beats to unwind & drift away 🌙",
            "late night study session 📚",
            "slow down. breathe. focus. 🌿",
            "music for when words aren't enough 🎧",
            "1 hour of calm in the chaos 🌊",
            "drift into focus mode 🌑",
            "for quiet nights & heavy thoughts 💭",
            "the soundtrack to your late nights ✨",
        ],
        "title_prefix": "🌙 1 Hour Melancholic Lofi",
        "desc_mood": "melancholic and introspective",
    },
    "dorian": {
        "intervals": [0, 2, 3, 5, 7, 9, 10],
        "mood": "focused",
        "hook_pool": [
            "beats to stay in the zone 🎯",
            "deep work. no distractions. 💻",
            "your focus playlist. press play. 🔁",
            "1 hour of pure concentration 🧠",
            "locked in. lofi on. 🔒",
            "the flow state soundtrack 🌀",
            "work smarter. not harder. 🎧",
            "beats built for focus people ⚡",
        ],
        "title_prefix": "🎯 1 Hour Focus Lofi Hip Hop",
        "desc_mood": "focused and motivating",
    },
    "major": {
        "intervals": [0, 2, 4, 5, 7, 9, 11],
        "mood": "uplifting",
        "hook_pool": [
            "good vibes. good music. good day ☀️",
            "start your morning right 🌅",
            "happy beats for happy days 🌻",
            "music that makes you smile 😊",
            "bright beats for bright minds 💡",
            "the feel-good lofi playlist 🎵",
            "positive vibes only ✌️",
            "chill, happy, unstoppable 🚀",
        ],
        "title_prefix": "☀️ 1 Hour Uplifting Lofi Beats",
        "desc_mood": "uplifting and cheerful",
    },
    "phrygian": {
        "intervals": [0, 1, 3, 5, 7, 8, 10],
        "mood": "dreamy",
        "hook_pool": [
            "drift into another world 🌌",
            "close your eyes & let go 🌠",
            "beats for daydreamers 🦋",
            "somewhere between awake and dreaming 💤",
            "lost in the music 🎶",
            "escape the noise 🎧",
            "ambient lofi for the wandering mind 🌙",
            "float away with every beat 🌊",
        ],
        "title_prefix": "🌌 1 Hour Dreamy Lofi Ambient",
        "desc_mood": "dreamy and atmospheric",
    },
}

ROOT_NOTES_HZ = {
    "C": 261.63, "C#": 277.18, "D": 293.66, "D#": 311.13,
    "E": 329.63, "F": 349.23, "F#": 369.99, "G": 392.00,
    "G#": 415.30, "A": 440.00, "A#": 466.16, "B": 493.88
}


def pick_unique_hook(scale_type):
    """Pick a hook that avoids repeating within the same session via random shuffle."""
    pool = SCALE_CONFIGS[scale_type]["hook_pool"]
    return random.choice(pool)


def generate_video_metadata(scale_type, root_name, bpm):
    """Generate unique title, description and hook for this run."""
    config = SCALE_CONFIGS[scale_type]
    hook = pick_unique_hook(scale_type)
    mood = config["mood"]
    prefix = config["title_prefix"]
    desc_mood = config["desc_mood"]

    title = f"{prefix} – {hook.split(' ')[0].replace('🌙','').replace('🎯','').replace('☀️','').replace('🌌','').strip()} Study Music | {CHANNEL_NAME}"
    title = f"{prefix} – Relaxing {mood.capitalize()} Beats | {CHANNEL_NAME}"

    description = f"""🎶 {hook}

Welcome to {CHANNEL_NAME} 🎧 — your daily source for generative lofi beats.

This {desc_mood} 1 hour lofi mix is perfect for:
📚 Studying & Deep Work
💻 Focus & Productivity  
🌙 Late Night Sessions
😴 Sleep & Relaxation
🌿 Stress Relief & Mindfulness

Generated in key: {root_name} {scale_type.capitalize()} | BPM: {bpm}

✨ Subscribe to {CHANNEL_NAME} for fresh lofi beats every day.
👍 Like & comment if this helped you focus.
🔔 Turn on notifications so you never miss a drop.

Press play. Let the beat carry you. 🌊

#lofi #studymusic #{mood}lofi #lofihiphop #lofibeats #focusmusic
#studybeats #{scale_type}lofi #chillbeats #relaxingmusic
#backgroundmusic #deepwork #{CHANNEL_NAME.lower()} #1hourlofi
#instrumentalmusic #ambientlofi #lofivibes #calmmusic"""

    tags = [
        f"1 hour lofi", f"1 hour {mood} lofi", f"lofi {scale_type}",
        "lofi hip hop", "lofi beats", "study music",
        "focus music", "deep work music", "chill beats",
        f"relaxing {mood} music", "background music for studying",
        "sleep lofi", "calm background music", "chillhop",
        "instrumental hip hop", "aesthetic lofi", "late night lofi",
        CHANNEL_NAME, f"{mood} beats", "lofi 2025"
    ]

    return title, description, tags, hook


# ===================== AUDIO ENGINE =====================

def make_envelope(length, attack=0.01, decay=0.1, sustain=0.7, release=0.2):
    total = length
    a = int(attack * SR)
    d = int(decay * SR)
    r = int(release * SR)
    s = max(0, total - a - d - r)
    env = np.concatenate([
        np.linspace(0, 1, a),
        np.linspace(1, sustain, d),
        np.full(s, sustain),
        np.linspace(sustain, 0, r)
    ])
    return env[:length]


def sine_wave(freq, duration, sr=SR):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t)


def generate_chord(root_hz, scale_intervals, num_notes=4, duration=2.0):
    chosen = random.sample(scale_intervals, min(num_notes, len(scale_intervals)))
    chord = np.zeros(int(SR * duration))
    for interval in chosen:
        freq = root_hz * (2 ** (interval / 12))
        wave = sine_wave(freq, duration)
        env = make_envelope(len(wave))
        chord += wave * env * 0.25
    return chord


def generate_bass(root_hz, duration=2.0):
    freq = root_hz / 2
    wave = sine_wave(freq, duration)
    env = make_envelope(len(wave), attack=0.005, decay=0.3, sustain=0.4, release=0.3)
    return wave * env * 0.4


def generate_kick(duration=0.5):
    t = np.linspace(0, duration, int(SR * duration))
    freq = 55 * np.exp(-20 * t)
    wave = np.sin(2 * np.pi * freq * t)
    env = np.exp(-10 * t)
    return wave * env * 0.8


def generate_snare(duration=0.3):
    noise = np.random.randn(int(SR * duration))
    env = np.exp(-15 * np.linspace(0, duration, int(SR * duration)))
    return noise * env * 0.3


def generate_hihat(duration=0.1):
    noise = np.random.randn(int(SR * duration))
    env = np.exp(-40 * np.linspace(0, duration, int(SR * duration)))
    return noise * env * 0.15


def generate_melody_note(freq, duration=0.5):
    wave = sine_wave(freq, duration)
    env = make_envelope(len(wave), attack=0.02, decay=0.2, sustain=0.5, release=0.3)
    return wave * env * 0.2


def build_lofi_track(scale_type, root_note, bpm):
    config = SCALE_CONFIGS[scale_type]
    intervals = config["intervals"]
    root_hz = ROOT_NOTES_HZ[root_note]

    beat_duration = 60 / bpm
    bar_duration = beat_duration * 4
    base_duration = BASE_MINUTES * 60
    total_samples = int(SR * base_duration)

    track = np.zeros(total_samples)
    pos = 0

    # Scale frequencies for melody
    scale_freqs = [root_hz * (2 ** (i / 12)) for i in intervals]
    scale_freqs += [f * 2 for f in scale_freqs]  # octave up

    while pos < total_samples:
        remaining = total_samples - pos

        # Chord pad
        chord_dur = min(bar_duration * 2, remaining / SR)
        if chord_dur > 0.1:
            chord = generate_chord(root_hz, intervals, duration=chord_dur)
            end = min(pos + len(chord), total_samples)
            track[pos:end] += chord[:end - pos]

        # Bass (every beat)
        for beat in range(8):
            beat_pos = pos + int(beat * beat_duration * SR)
            if beat_pos >= total_samples:
                break
            if beat in [0, 3, 4, 7]:
                bass = generate_bass(root_hz, min(beat_duration * 0.8, (total_samples - beat_pos) / SR))
                end = min(beat_pos + len(bass), total_samples)
                track[beat_pos:end] += bass[:end - beat_pos]

        # Drums
        for beat in range(8):
            beat_pos = pos + int(beat * beat_duration * SR)
            if beat_pos >= total_samples:
                break

            # Kick on 1, 3
            if beat in [0, 4]:
                kick = generate_kick()
                end = min(beat_pos + len(kick), total_samples)
                track[beat_pos:end] += kick[:end - beat_pos]

            # Snare on 2, 4
            if beat in [2, 6]:
                snare = generate_snare()
                end = min(beat_pos + len(snare), total_samples)
                track[beat_pos:end] += snare[:end - beat_pos]

            # Hihat every half beat
            for half in range(2):
                hh_pos = beat_pos + int(half * beat_duration * SR * 0.5)
                if hh_pos >= total_samples:
                    break
                hihat = generate_hihat()
                end = min(hh_pos + len(hihat), total_samples)
                track[hh_pos:end] += hihat[:end - hh_pos]

        # Melody (sparse, every 2 bars)
        if random.random() > 0.3:
            for note_idx in range(random.randint(2, 5)):
                note_pos = pos + int(random.uniform(0, bar_duration * 2) * SR)
                if note_pos >= total_samples:
                    break
                freq = random.choice(scale_freqs)
                note_dur = random.uniform(0.3, 0.8)
                note = generate_melody_note(freq, note_dur)
                end = min(note_pos + len(note), total_samples)
                track[note_pos:end] += note[:end - note_pos]

        pos += int(bar_duration * 2 * SR)

    # Normalize
    max_val = np.max(np.abs(track))
    if max_val > 0:
        track = track / max_val * 0.85

    return track


# ===================== VIDEO ENGINE =====================

def make_gradient_frame(t, width, height, hook_text, total_duration,
                        box_configs, text_anim_config):
    """Generate a single PIL frame with gradient background + animated boxes + floating text."""

    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Gradient background (dark purple → dark blue)
    for y in range(height):
        ratio = y / height
        r = int(15 + ratio * 5)
        g = int(10 + ratio * 15)
        b = int(40 + ratio * 50)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Animated boxes
    for box in box_configs:
        speed = box["speed"]
        size = box["size"]
        # X oscillates across full width
        x = (box["x_offset"] + t * speed * 80) % (width + size) - size
        # Y oscillates up and down
        y = box["y_base"] + np.sin(t * box["y_freq"] + box["y_phase"]) * box["y_amp"]

        alpha_val = int(box["alpha"] * 255)
        box_color = (box["r"], box["g"], box["b"], alpha_val)

        # Draw on separate layer for transparency
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        ov_draw.rectangle([x, y, x + size, y + size], fill=box_color)
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay)
        img = img.convert("RGB")
        draw = ImageDraw.Draw(img)

    # Floating + pulsing text
    cfg = text_anim_config
    # Text travel: covers 60% of screen width from left to right and back
    travel_w = width * 0.60
    travel_h = height * 0.30
    x_center = width * 0.20 + travel_w * (0.5 + 0.5 * np.sin(t * cfg["x_speed"]))
    y_center = height * 0.50 + travel_h * (0.5 * np.sin(t * cfg["y_speed"] + 1.0))

    # Pulse size: ±7%
    size_scale = 1.0 + 0.07 * np.sin(t * cfg["pulse_speed"])

    # Try to load font, fallback to default
    try:
        font_size = int(cfg["base_font_size"] * size_scale)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    # Hook text (main, animated)
    bbox = draw.textbbox((0, 0), hook_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    tx = int(x_center - text_w / 2)
    ty = int(y_center - text_h / 2)

    # Shadow
    draw.text((tx + 3, ty + 3), hook_text, font=font, fill=(0, 0, 0, 120))
    # Main text (white glow)
    draw.text((tx, ty), hook_text, font=font, fill=(230, 220, 255))

    # Channel name (smaller, subtle, below center — more static)
    try:
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except Exception:
        small_font = ImageFont.load_default()

    ch_text = f"— {CHANNEL_NAME} —"
    ch_bbox = draw.textbbox((0, 0), ch_text, font=small_font)
    ch_w = ch_bbox[2] - ch_bbox[0]
    ch_x = (width - ch_w) // 2
    ch_y = height - 80
    draw.text((ch_x + 2, ch_y + 2), ch_text, font=small_font, fill=(0, 0, 0, 80))
    draw.text((ch_x, ch_y), ch_text, font=small_font, fill=(160, 140, 200))

    return np.array(img)


def generate_box_configs(n=20, width=1920, height=1080):
    """Pre-generate random box parameters so they're consistent across frames."""
    boxes = []
    for _ in range(n):
        size = random.randint(15, 60)
        boxes.append({
            "x_offset": random.uniform(0, width),
            "y_base": random.uniform(0, height),
            "speed": random.uniform(0.5, 4.0),       # horizontal drift
            "y_freq": random.uniform(0.3, 1.5),       # vertical oscillation frequency
            "y_phase": random.uniform(0, 2 * np.pi),
            "y_amp": random.uniform(20, 120),          # vertical travel distance
            "size": size,
            "r": random.randint(80, 180),
            "g": random.randint(60, 120),
            "b": random.randint(150, 255),
            "alpha": random.uniform(0.08, 0.25),
        })
    return boxes


def generate_text_anim_config():
    return {
        "x_speed": random.uniform(0.08, 0.18),    # how fast text moves L-R
        "y_speed": random.uniform(0.06, 0.14),    # how fast text moves U-D
        "pulse_speed": random.uniform(0.5, 1.2),  # size pulse speed
        "base_font_size": 72,
    }


# ===================== MAIN =====================

def main():
    print("🎵 Starting Driftory Lofi Generator...")

    # Pick random musical parameters
    scale_type = random.choice(list(SCALE_CONFIGS.keys()))
    root_note = random.choice(list(ROOT_NOTES_HZ.keys()))
    bpm = random.randint(68, 88)

    print(f"   Scale: {scale_type} | Root: {root_note} | BPM: {bpm}")

    # Generate metadata
    title, description, tags, hook_text = generate_video_metadata(scale_type, root_note, bpm)
    print(f"   Hook text: {hook_text}")
    print(f"   Title: {title[:60]}...")

    # Save metadata for uploader
    import json
    with open("video_meta.json", "w", encoding="utf-8") as f:
        json.dump({
            "title": title,
            "description": description,
            "tags": tags,
            "hook": hook_text,
            "scale": scale_type,
            "root": root_note,
            "bpm": bpm,
        }, f, ensure_ascii=False, indent=2)
    print("   ✅ video_meta.json saved")

    # Generate audio
    print("🎧 Generating audio track...")
    base_track = build_lofi_track(scale_type, root_note, bpm)

    # Loop to fill FINAL_DURATION
    total_samples = int(SR * FINAL_DURATION)
    if len(base_track) < total_samples:
        repeats = int(np.ceil(total_samples / len(base_track)))
        full_track = np.tile(base_track, repeats)[:total_samples]
    else:
        full_track = base_track[:total_samples]

    sf.write(OUTPUT_AUDIO, full_track, SR)
    print(f"   ✅ Audio saved: {OUTPUT_AUDIO} ({FINAL_DURATION}s)")

    # Generate video
    print("🎬 Generating video frames...")
    box_configs = generate_box_configs(n=20, width=WIDTH, height=HEIGHT)
    text_anim_config = generate_text_anim_config()

    def make_frame(t):
        return make_gradient_frame(
            t, WIDTH, HEIGHT, hook_text,
            FINAL_DURATION, box_configs, text_anim_config
        )

    video_clip = VideoClip(make_frame, duration=FINAL_DURATION)
    audio_clip = AudioFileClip(OUTPUT_AUDIO)
    final = video_clip.set_audio(audio_clip)

    print(f"🚀 Rendering video ({FINAL_DURATION}s)...")
    final.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4,
        logger="bar"
    )

    print(f"   ✅ Video saved: {OUTPUT_VIDEO}")
    print("🎉 Done! Ready to upload.")


if __name__ == "__main__":
    main()
