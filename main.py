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
FINAL_DURATION = 300   # detik (ganti ke 300 untuk testing 5 menit)
BASE_MINUTES = 5        # menit base audio (ganti ke 5 untuk testing)
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


# ===================== AUDIO ENGINE (MODERN LOFI) =====================

def make_adsr(n_samples, attack, decay, sustain_level, release, sr=SR):
    """Smooth ADSR envelope — all times in seconds."""
    a = int(attack * sr)
    d = int(decay * sr)
    r = int(release * sr)
    s = max(0, n_samples - a - d - r)
    env = np.concatenate([
        np.linspace(0.0, 1.0, max(a, 1)),
        np.linspace(1.0, sustain_level, max(d, 1)),
        np.full(s, sustain_level),
        np.linspace(sustain_level, 0.0, max(r, 1)),
    ])
    return env[:n_samples]


def piano_note(freq, duration, sr=SR, velocity=0.7):
    """
    Realistic piano tone using additive synthesis.
    - Fundamental + harmonics with natural decay per partial
    - Inharmonicity (slight detuning of upper partials)
    - Fast attack, exponential decay like a real piano string
    """
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    wave = np.zeros(n)

    # Harmonic series: (partial, relative_amplitude, decay_rate)
    # Higher partials decay faster — gives piano's characteristic brightness→warmth
    partials = [
        (1, 1.00, 2.5),
        (2, 0.50, 3.5),
        (3, 0.28, 5.0),
        (4, 0.14, 7.0),
        (5, 0.08, 10.0),
        (6, 0.04, 14.0),
        (7, 0.02, 20.0),
    ]
    for k, amp, decay_rate in partials:
        # Slight inharmonicity: B_coeff stretches upper partials
        inharmonic_freq = freq * k * (1.0 + 0.0004 * (k ** 2))
        partial_wave = amp * velocity * np.sin(2 * np.pi * inharmonic_freq * t)
        # Per-partial exponential decay
        partial_env = np.exp(-decay_rate * t)
        wave += partial_wave * partial_env

    # Very short attack transient (hammer strike feel)
    attack_samples = int(0.006 * sr)
    attack_env = np.linspace(0, 1, attack_samples)
    wave[:attack_samples] *= attack_env

    # Soft clip to add subtle warmth (avoids harsh digital clipping)
    wave = np.tanh(wave * 1.2) / np.tanh(1.2)

    return wave


def warm_pad(freq, duration, sr=SR):
    """
    Soft pad sound (Rhodes/electric piano feel).
    Detuned pair of sines for chorus-like warmth.
    """
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)

    detune = 0.003  # slight chorus detuning
    w1 = np.sin(2 * np.pi * freq * (1 - detune) * t)
    w2 = np.sin(2 * np.pi * freq * (1 + detune) * t)
    wave = 0.5 * (w1 + w2)

    # Slow attack, long sustain, gentle fade — pad behaviour
    env = make_adsr(n, attack=0.18, decay=0.4, sustain_level=0.65, release=0.8)
    return wave * env * 0.18


def bass_note(freq, duration, sr=SR):
    """
    Warm sub-bass: fundamental + 2nd harmonic, soft clip for analog feel.
    """
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    bass_freq = freq / 2  # one octave down

    fund = np.sin(2 * np.pi * bass_freq * t)
    harm = 0.25 * np.sin(2 * np.pi * bass_freq * 2 * t)
    wave = fund + harm

    env = make_adsr(n, attack=0.01, decay=0.25, sustain_level=0.55, release=0.35)
    wave = np.tanh(wave * 1.5) / np.tanh(1.5)  # warm saturation
    return wave * env * 0.45


def lofi_kick(sr=SR):
    """Deep kick drum with pitch drop."""
    duration = 0.55
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    # Pitch drops from 160Hz → 50Hz
    freq_env = 50 + 110 * np.exp(-25 * t)
    wave = np.sin(2 * np.pi * np.cumsum(freq_env) / sr)
    amp_env = np.exp(-9 * t)
    # Small click transient
    click = np.zeros(n)
    click[:int(0.003 * sr)] = 0.6
    return (wave * amp_env * 0.85 + click)


def lofi_snare(sr=SR):
    """
    Lofi snare: tone body + filtered noise, with slight swing.
    """
    duration = 0.28
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)

    # Tone component (200 Hz body)
    tone = 0.35 * np.sin(2 * np.pi * 200 * t) * np.exp(-30 * t)
    # Noise component (snappy)
    noise = np.random.randn(n) * np.exp(-22 * t) * 0.55
    # Simple 1-pole high-pass on noise (remove too much sub)
    filtered = np.zeros(n)
    alpha = 0.85
    filtered[0] = noise[0]
    for i in range(1, n):
        filtered[i] = alpha * (filtered[i-1] + noise[i] - noise[i-1])

    return (tone + filtered * 0.6) * 0.70


def lofi_hihat(open_hat=False, sr=SR):
    """Crispy hi-hat: band-passed noise."""
    duration = 0.18 if open_hat else 0.07
    n = int(sr * duration)
    noise = np.random.randn(n)
    # Simple high-pass approximation
    alpha = 0.92
    hp = np.zeros(n)
    hp[0] = noise[0]
    for i in range(1, n):
        hp[i] = alpha * (hp[i-1] + noise[i] - noise[i-1])
    decay = 12.0 if open_hat else 35.0
    t = np.linspace(0, duration, n, endpoint=False)
    env = np.exp(-decay * t)
    return hp * env * (0.18 if open_hat else 0.13)


def simple_reverb(signal, decay=0.35, sr=SR):
    """
    Very lightweight reverb via Schroeder comb filters.
    Adds space and depth without heavy convolution.
    """
    # Comb filter delay times (prime-ish, in ms)
    delays_ms = [29.7, 37.1, 41.1, 43.7]
    gains     = [0.82, 0.80, 0.78, 0.76]
    out = np.copy(signal).astype(np.float64)
    for delay_ms, g in zip(delays_ms, gains):
        d = int(delay_ms * sr / 1000)
        buf = np.zeros(d)
        comb = np.zeros(len(signal))
        idx = 0
        for i in range(len(signal)):
            comb[i] = signal[i] + g * buf[idx]
            buf[idx] = comb[i]
            idx = (idx + 1) % d
        out += comb * 0.22
    # Normalise to avoid clipping
    mx = np.max(np.abs(out))
    if mx > 0:
        out = out / mx
    return out


def vinyl_crackle(n_samples, intensity=0.012, sr=SR):
    """
    Lofi vinyl crackle: sparse random pops + continuous low-level hiss.
    """
    hiss = np.random.randn(n_samples) * (intensity * 0.4)
    # Occasional pops (roughly 1–3 per second)
    pops = np.zeros(n_samples)
    pop_rate = int(sr * random.uniform(0.3, 0.7))
    for i in range(0, n_samples, pop_rate):
        offset = i + random.randint(0, pop_rate - 1)
        if offset < n_samples:
            pop_len = random.randint(80, 400)
            amplitude = random.uniform(0.01, 0.04)
            pop_end = min(offset + pop_len, n_samples)
            pop_n = pop_end - offset
            t_pop = np.linspace(0, 1, pop_n)
            pops[offset:pop_end] += amplitude * np.random.randn(pop_n) * np.exp(-8 * t_pop)
    return hiss + pops


def build_lofi_track(scale_type, root_note, bpm):
    """
    Build a full modern lofi track:
    - Piano melody (additive synthesis with natural decay)
    - Warm pad chords (Rhodes-like)
    - Warm sub-bass
    - Kick / snare / hihat drum pattern with swing
    - Schroeder reverb for depth
    - Vinyl crackle signature
    """
    config   = SCALE_CONFIGS[scale_type]
    intervals = config["intervals"]
    root_hz  = ROOT_NOTES_HZ[root_note]

    beat_dur   = 60.0 / bpm
    bar_dur    = beat_dur * 4
    base_dur   = BASE_MINUTES * 60
    total_samp = int(SR * base_dur)

    # Lofi swing: 16th-note triplet feel — every 2nd 8th note is pushed slightly late
    swing_ratio = 0.58   # 0.5 = straight, 0.67 = full triplet swing

    track = np.zeros(total_samp)
    pos = 0

    # Build scale frequencies across 3 octaves for melody
    scale_freqs_mid  = [root_hz * (2 ** (i / 12)) for i in intervals]
    scale_freqs_high = [f * 2 for f in scale_freqs_mid]
    scale_freqs_low  = [f / 2 for f in scale_freqs_mid]
    all_melody_freqs = scale_freqs_low + scale_freqs_mid + scale_freqs_high

    # Chord voicings: root + 3rd + 5th + 7th (jazz-style)
    CHORD_VOICINGS = [
        [0, 3, 7, 10],  # min7
        [0, 4, 7, 11],  # maj7
        [0, 3, 7, 11],  # minMaj7
        [0, 4, 7, 10],  # dom7
        [0, 3, 6, 10],  # half-dim
    ]

    def add_signal(buf, signal, start):
        """Safe add: clips to buffer length."""
        end = min(start + len(signal), len(buf))
        buf[start:end] += signal[:end - start]

    while pos < total_samp:
        remaining = (total_samp - pos) / SR

        # ── Pad chords (2 bars, soft background) ─────────────────────────
        chord_dur = min(bar_dur * 2, remaining)
        if chord_dur > 0.5:
            voicing = random.choice(CHORD_VOICINGS)
            pad_chord = np.zeros(int(SR * chord_dur))
            for interval in voicing:
                freq = root_hz * (2 ** (interval / 12))
                pad  = warm_pad(freq, chord_dur)
                pad_chord += pad
            add_signal(track, pad_chord, pos)

        # ── Piano melody (sparse, 2 bars) ─────────────────────────────────
        # Pick 3–6 notes spread across 2 bars, leave silences for breathing room
        num_notes = random.randint(3, 6)
        bar_samples = int(bar_dur * 2 * SR)
        used_positions = []
        for _ in range(num_notes):
            # Quantise to 8th note grid with swing
            eighth = beat_dur / 2
            step   = random.randint(0, 15)  # 16 eighth-note slots in 2 bars
            swing_offset = (swing_ratio - 0.5) * eighth if step % 2 == 1 else 0
            note_time = step * eighth + swing_offset + random.uniform(-0.02, 0.02)
            note_pos  = pos + int(note_time * SR)
            if note_pos >= total_samp:
                continue
            freq     = random.choice(scale_freqs_mid + scale_freqs_high)
            vel      = random.uniform(0.45, 0.85)
            note_dur = random.uniform(0.25, beat_dur * 1.8)
            note_dur = min(note_dur, (total_samp - note_pos) / SR)
            if note_dur > 0.1:
                note = piano_note(freq, note_dur, velocity=vel) * 0.55
                add_signal(track, note, note_pos)

        # ── Bass (follows chord root, on beats 1 & 3 with variation) ──────
        bass_pattern = [0, 4] if random.random() > 0.3 else [0, 3, 4, 7]
        for beat_idx in bass_pattern:
            beat_pos = pos + int(beat_idx * beat_dur * SR)
            if beat_pos >= total_samp:
                break
            b_dur = min(beat_dur * 0.85, (total_samp - beat_pos) / SR)
            if b_dur > 0.1:
                bass = bass_note(root_hz, b_dur) * 0.80
                add_signal(track, bass, beat_pos)

        # ── Drums (2 bars = 8 beats) ──────────────────────────────────────
        for beat_idx in range(8):
            beat_pos = pos + int(beat_idx * beat_dur * SR)
            if beat_pos >= total_samp:
                break

            # Kick: beat 1 & 3 (indices 0 & 4), occasional extra ghost kick
            if beat_idx in [0, 4]:
                add_signal(track, lofi_kick() * 0.88, beat_pos)
            elif beat_idx == 6 and random.random() > 0.6:
                add_signal(track, lofi_kick() * 0.4, beat_pos)  # ghost kick

            # Snare: beat 2 & 4 (indices 2 & 6) with slight humanise offset
            if beat_idx in [2, 6]:
                human_offset = int(random.uniform(-0.01, 0.015) * SR)
                snare_pos = max(0, beat_pos + human_offset)
                add_signal(track, lofi_snare() * 0.75, snare_pos)

            # Hi-hat: every 8th note with swing, occasional open hat
            for step in range(2):
                eighth_pos = beat_pos + int(step * beat_dur * 0.5 * SR)
                if step == 1:
                    eighth_pos += int((swing_ratio - 0.5) * beat_dur * 0.5 * SR)
                open_hat = (beat_idx == 2 and step == 1) and random.random() > 0.5
                hat = lofi_hihat(open_hat=open_hat)
                add_signal(track, hat * 0.80, eighth_pos)

        pos += int(bar_dur * 2 * SR)

    # ── Post-processing ───────────────────────────────────────────────────
    print("   Applying reverb...")
    track = simple_reverb(track, decay=0.35)

    print("   Adding vinyl crackle...")
    crackle = vinyl_crackle(len(track), intensity=0.010)
    track += crackle

    # Final normalise with small headroom
    mx = np.max(np.abs(track))
    if mx > 0:
        track = track / mx * 0.82

    return track


# ===================== VIDEO ENGINE =====================

def smooth_bounce(t, speed, phase_offset=0.0):
    """
    Smooth bounce using sine — value oscillates 0..1 with smooth easing at ends.
    Much smoother than triangle wave for text movement.
    """
    return 0.5 + 0.5 * np.sin(t * speed + phase_offset)


def make_gradient_frame(t, width, height, hook_text, total_duration,
                        box_configs, text_anim_config):
    """Generate a single PIL frame with gradient background + bouncing boxes + floating text."""

    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Gradient background (dark purple → dark blue)
    for y in range(height):
        ratio = y / height
        r = int(15 + ratio * 5)
        g = int(10 + ratio * 15)
        b = int(40 + ratio * 50)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Bouncing boxes — all drawn on one RGBA overlay for efficiency
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for box in box_configs:
        bx, by = box_position(box, t, width, height)
        size = box["size"]
        alpha_val = int(box["alpha"] * 255)
        box_color = (box["r"], box["g"], box["b"], alpha_val)
        ov_draw.rectangle([bx, by, bx + size, by + size], fill=box_color)
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── Smooth floating text ──────────────────────────────────────────────
    cfg = text_anim_config

    # Smooth sine-based position — full 60% width, 35% height range
    travel_w = width * 0.60
    travel_h = height * 0.35
    # x: starts from 20% left edge, travels to 80% right edge
    x_center = width * 0.20 + travel_w * smooth_bounce(t, cfg["x_speed"], 0.0)
    # y: centers around 50%, drifts ±17.5%
    y_center = height * 0.50 + travel_h * (smooth_bounce(t, cfg["y_speed"], 1.5) - 0.5)

    # Smooth size pulse ±6% — slow sine, different phase from position
    size_scale = 1.0 + 0.06 * np.sin(t * cfg["pulse_speed"])
    font_size = int(cfg["base_font_size"] * size_scale)
    # Clamp to avoid jarring jumps at integer boundaries
    font_size = max(60, min(font_size, 90))

    try:
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        font_reg  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
        font_sub  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
    except Exception:
        font_bold = ImageFont.load_default()
        font_reg  = ImageFont.load_default()
        font_sub  = ImageFont.load_default()

    # ── Hook text (line 1) ────────────────────────────────────────────────
    bbox = draw.textbbox((0, 0), hook_text, font=font_bold)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    tx = int(x_center - text_w / 2)
    ty = int(y_center - text_h / 2)

    # Soft dark shadow
    draw.text((tx + 3, ty + 3), hook_text, font=font_bold, fill=(0, 0, 0))
    # Main hook text — warm white
    draw.text((tx, ty), hook_text, font=font_bold, fill=(235, 225, 255))

    # ── Subtitle line 2: channel name + duration dot ──────────────────────
    # Follows hook text position (same x_center), placed just below
    sub_text = f"{CHANNEL_NAME}  ·  1 hour lofi"
    sub_bbox = draw.textbbox((0, 0), sub_text, font=font_sub)
    sub_w = sub_bbox[2] - sub_bbox[0]
    sub_x = int(x_center - sub_w / 2)
    sub_y = ty + text_h + 14   # 14px gap below hook

    draw.text((sub_x + 2, sub_y + 2), sub_text, font=font_sub, fill=(0, 0, 0))
    draw.text((sub_x, sub_y), sub_text, font=font_sub, fill=(150, 135, 190))

    return np.array(img)


def generate_box_configs(n=20, width=1920, height=1080):
    """Pre-generate random box parameters — boxes bounce inside screen edges."""
    boxes = []
    for _ in range(n):
        size = random.randint(40, 130)   # lebih besar
        boxes.append({
            # Starting position (normalized 0–1)
            "x0": random.uniform(0.0, 1.0),
            "y0": random.uniform(0.0, 1.0),
            # Velocity (normalized per second, bounces off walls)
            "vx": random.uniform(0.02, 0.10) * random.choice([-1, 1]),
            "vy": random.uniform(0.02, 0.08) * random.choice([-1, 1]),
            "size": size,
            "r": random.randint(80, 180),
            "g": random.randint(60, 120),
            "b": random.randint(150, 255),
            "alpha": random.uniform(0.12, 0.30),
        })
    return boxes


def box_position(box, t, width, height):
    """Calculate bouncing box position at time t using triangle wave."""
    size = box["size"]
    max_x = width - size
    max_y = height - size

    # Triangle wave for bouncing: x = |((vx*t + x0) mod 2) - 1| * max
    def triangle(v, p0, max_val):
        # period = 2 / |v|, bounce between 0 and max_val
        if max_val <= 0:
            return 0
        period = 2.0 / (abs(v) + 1e-9)
        raw = (v * t + p0 * period) / period  # normalized phase
        # fold into 0..1 range with triangle wave
        phase = raw % 2.0
        if phase < 0:
            phase += 2.0
        pos_n = phase if phase <= 1.0 else 2.0 - phase
        return pos_n * max_val

    x = triangle(box["vx"], box["x0"], max_x)
    y = triangle(box["vy"], box["y0"], max_y)
    return x, y


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
