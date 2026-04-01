# ============================================================
# DRIFTORY - GENERATIVE LOFI ENGINE v5
# 100% Python • No API • No GPU • Berjalan di GitHub Actions
# FM Rhodes Synth • Layered Drums • Sidechain • Tape Saturation
# Vinyl Crackle • Room Reverb • Stereo Widening • 1-Jam Auto Loop
# ============================================================

import numpy as np
import soundfile as sf
import random
from scipy import signal
from scipy.signal import fftconvolve
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import os

SR             = 44100
FINAL_DURATION = 300 #3600   # detik (1 jam). Ganti ke 60 untuk test cepat
WAV_OUTPUT     = "lofi_output.wav"
VIDEO_OUTPUT   = "final_video.mp4"
CHANNEL_NAME   = "Driftory"

# ── Pilih mood secara random ──────────────────────────────────────────
MOODS = {
    "rainy_night": {
        "scale":      "minor",
        "bpm":        random.randint(68, 76),
        "root_idx":   random.choice([0, 2, 5]),
        "reverb":     0.30,
        "crackle":    0.007,
        "saturation": 1.20,
        "hooks": [
            ("rainy night feels 🌧️",  "rainy night feels"),
            ("slow down, unwind 🌙",   "slow down, unwind"),
            ("drift into calm 🌊",     "drift into calm"),
            ("soft & still 🕯️",        "soft & still"),
        ],
        "grad":    [(18,12,55),  (28,18,80)],
        "palette": [(170,150,255),(130,170,255),(150,130,215)],
    },
    "deep_focus": {
        "scale":      "dorian",
        "bpm":        random.randint(74, 84),
        "root_idx":   random.choice([0, 3, 7]),
        "reverb":     0.20,
        "crackle":    0.004,
        "saturation": 1.15,
        "hooks": [
            ("deep focus mode 🎯",    "deep focus mode"),
            ("locked in 🔒",           "locked in"),
            ("study & flow 📖",        "study & flow"),
            ("grind in silence 🖊️",    "grind in silence"),
        ],
        "grad":    [(12,22,50),  (8,35,65)],
        "palette": [(90,150,255),(70,190,210),(110,130,195)],
    },
    "good_vibes": {
        "scale":      "major",
        "bpm":        random.randint(80, 90),
        "root_idx":   random.choice([0, 5, 7]),
        "reverb":     0.18,
        "crackle":    0.003,
        "saturation": 1.10,
        "hooks": [
            ("good vibes only ☀️",    "good vibes only"),
            ("bright & easy 🌤️",       "bright & easy"),
            ("feel good beats 🌸",     "feel good beats"),
            ("warm afternoon 🌻",      "warm afternoon"),
        ],
        "grad":    [(55,28,18),  (75,45,12)],
        "palette": [(255,175,95),(255,215,75),(255,145,115)],
    },
    "late_night": {
        "scale":      "minor",
        "bpm":        random.randint(63, 73),
        "root_idx":   random.choice([2, 4, 9]),
        "reverb":     0.35,
        "crackle":    0.008,
        "saturation": 1.30,
        "hooks": [
            ("late night peace ✨",   "late night peace"),
            ("quiet hours 🌑",         "quiet hours"),
            ("just breathe 😮‍💨",        "just breathe"),
            ("sleepy jazz 🎷",          "sleepy jazz"),
        ],
        "grad":    [(8, 8, 35),  (18,12,55)],
        "palette": [(140,115,235),(115,95,195),(165,135,245)],
    },
}

mood_key              = random.choice(list(MOODS.keys()))
mood                  = MOODS[mood_key]
BPM                   = mood["bpm"]
BEAT                  = 60.0 / BPM
BAR                   = BEAT * 4
hook_meta, hook_video = random.choice(mood["hooks"])
scale_name            = mood["scale"]

# Root note frequencies (semitone dari C2=65.41 Hz)
ROOT_FREQS = [65.41,73.42,82.41,87.31,98.00,110.00,123.47,130.81,146.83,164.81,174.61,196.00]
root       = ROOT_FREQS[mood["root_idx"]]

with open("hook.txt", "w", encoding="utf-8") as f:
    f.write(f"{hook_meta}\n{scale_name}\n{BPM}")

print(f"🎵 Mood: {mood_key} | Scale: {scale_name} | BPM: {BPM} | Hook: {hook_meta}")

# ── Skala nada ────────────────────────────────────────────────────────
SCALES = {
    "minor":  [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "major":  [0, 2, 4, 5, 7, 9, 11],
}
scale = SCALES[scale_name]

def note_freq(base, degree, octave=0):
    return base * (2 ** (scale[degree % len(scale)] / 12)) * (2 ** octave)

# ── FM Rhodes synthesizer ─────────────────────────────────────────────
def rhodes_tone(freq, duration, velocity=0.8):
    """
    Fender Rhodes via FM synthesis.
    Karakteristik khas: attack tajam, decay melengkung, tremolo tipis.
    """
    n  = int(SR * duration)
    t  = np.linspace(0, duration, n, endpoint=False)

    mod_ratio = 2.0
    mod_index = 1.9
    modulator = np.sin(2 * np.pi * freq * mod_ratio * t)
    carrier   = np.sin(2 * np.pi * freq * t + mod_index * modulator)

    h2   = 0.14 * np.sin(2 * np.pi * freq * 2 * t)
    h3   = 0.05 * np.sin(2 * np.pi * freq * 3 * t)
    wave = carrier + h2 + h3

    atk = min(int(0.003 * SR), n)
    dec = min(int(0.13  * SR), n - atk)
    sus = 0.44
    rel = min(int(0.38  * SR), n - atk - dec)
    ss  = max(n - atk - dec - rel, 0)
    env = np.concatenate([
        np.linspace(0, 1, atk),
        np.linspace(1, sus, dec) ** 1.6,
        np.full(ss, sus),
        np.linspace(sus, 0, rel) ** 2.0,
    ])[:n]

    trem_rate = random.uniform(4.5, 6.0)
    trem      = 1.0 + 0.038 * np.sin(2 * np.pi * trem_rate * t)

    return wave * env * trem * velocity

# ── Chord voicing dengan strum humanization ───────────────────────────
def strum_chord(degrees, duration, velocity=0.72, strum_ms=14):
    n    = int(SR * duration)
    wave = np.zeros(n)

    bf   = note_freq(root, degrees[0], -1)
    bass = rhodes_tone(bf, duration, velocity * 0.58)
    wave[:len(bass)] += bass * 0.52

    for i, deg in enumerate(degrees):
        oct_        = 1 if i == len(degrees) - 1 else 0
        freq        = note_freq(root, deg, oct_)
        strum_delay = int(i * strum_ms * 0.001 * SR)
        v           = velocity * random.uniform(0.80, 1.02)
        tone        = rhodes_tone(freq, duration, v)
        end         = min(strum_delay + len(tone), n)
        wave[strum_delay:end] += tone[:end - strum_delay]

    return wave / (len(degrees) + 1)

# ── Sub bass synth ────────────────────────────────────────────────────
def make_bass_note(degree, duration, octave=-1):
    freq = note_freq(root, degree, octave)
    n    = int(SR * duration)
    t    = np.linspace(0, duration, n, endpoint=False)

    sub  = np.sin(2 * np.pi * freq * t)
    oct2 = 0.28 * np.sin(2 * np.pi * freq * 2 * t)
    wave = np.tanh((sub + oct2) * 1.3)

    atk = min(int(0.008 * SR), n)
    dec = min(int(0.07  * SR), n - atk)
    sus = 0.58
    rel = min(int(0.12  * SR), n - atk - dec)
    ss  = max(n - atk - dec - rel, 0)
    env = np.concatenate([
        np.linspace(0, 1, atk),
        np.linspace(1, sus, dec),
        np.full(ss, sus),
        np.linspace(sus, 0, rel),
    ])[:n]

    b, a = signal.butter(3, 380 / (SR / 2), btype='low')
    return signal.lfilter(b, a, wave * env) * 0.42

# ── Drum synthesizer ──────────────────────────────────────────────────
def make_kick():
    dur   = 0.55; n = int(SR * dur); t = np.linspace(0, dur, n)
    freq  = np.linspace(185, 45, n)
    phase = np.cumsum(2 * np.pi * freq / SR)
    body  = np.sin(phase) * np.exp(-t * 9) * 0.88
    click_len = int(0.003 * SR)
    click = np.random.randn(click_len) * np.linspace(1, 0, click_len)
    body[:click_len] += click * 0.32
    return np.tanh(body * 1.65) / 1.65

def make_snare():
    dur  = 0.22; n = int(SR * dur); t = np.linspace(0, dur, n)
    tone = (np.sin(2*np.pi*175*t)*0.38 + np.sin(2*np.pi*245*t)*0.14) * np.exp(-t*26)
    noise = np.random.randn(n)
    b, a  = signal.butter(3, [900/(SR/2), 8500/(SR/2)], btype='band')
    noise = signal.lfilter(b, a, noise) * np.exp(-t * 15)
    return (tone*0.38 + noise*0.62) * np.exp(-t*5) * 0.55

def make_ghost():
    dur  = 0.055; n = int(SR * dur); t = np.linspace(0, dur, n)
    click = np.random.randn(n) * np.exp(-t * 130)
    tone  = np.sin(2*np.pi*1300*t) * np.exp(-t*90) * 0.45
    b, a  = signal.butter(3, 900/(SR/2), btype='high')
    return signal.lfilter(b, a, click + tone) * 0.16

def make_hihat(open_hat=False):
    dur   = 0.13 if open_hat else 0.032
    n     = int(SR * dur); t = np.linspace(0, dur, n)
    noise = np.random.randn(n)
    b, a  = signal.butter(5, 8800/(SR/2), btype='high')
    metal = signal.lfilter(b, a, noise)
    metal += 0.28 * np.sin(2*np.pi*9500*t)  * np.exp(-t*85)
    metal += 0.18 * np.sin(2*np.pi*12500*t) * np.exp(-t*130)
    env   = np.exp(-t * (7.5 if open_hat else 95))
    return metal * env * 0.11

# ── Effect chain ──────────────────────────────────────────────────────
def lofi_eq(audio):
    b,  a  = signal.butter(4, 8200/(SR/2), btype='low')
    audio  = signal.filtfilt(b, a, audio)
    b2, a2 = signal.butter(2, [180/(SR/2), 420/(SR/2)], btype='band')
    audio += signal.filtfilt(b2, a2, audio) * 0.20
    b3, a3 = signal.iirnotch(2800/(SR/2), Q=3.5)
    return signal.lfilter(b3, a3, audio)

def room_reverb(audio, wet=0.22):
    ir_len = int(SR * 0.85)
    t_ir   = np.arange(ir_len) / SR
    ir     = np.zeros(ir_len)
    for ms, amp in [(11,.54),(20,.41),(32,.31),(49,.23),(71,.17),(95,.12),(135,.08)]:
        idx = int(ms * SR / 1000)
        if idx < ir_len:
            ir[idx] = amp * random.uniform(0.84, 1.0)
    ts = int(0.045 * SR)
    ir[ts:] += np.random.randn(ir_len - ts) * np.exp(-t_ir[ts:] * 5.5) * 0.18
    wet_sig = fftconvolve(audio, ir)[:len(audio)]
    peak    = np.max(np.abs(wet_sig)) + 1e-9
    wet_sig = wet_sig / peak * np.max(np.abs(audio)) * 0.88
    return audio * (1 - wet) + wet_sig * wet

def vinyl_crackle(audio, intensity=0.005):
    n    = len(audio)
    t    = np.arange(n) / SR
    crk  = np.random.randn(n) * intensity
    b, a = signal.butter(1, 220/(SR/2), btype='low')
    crk  = signal.lfilter(b, a, crk) + np.random.randn(n) * (intensity * 0.28)
    wow  = np.sin(2*np.pi*0.42*t) * 0.00014 * SR
    flt  = np.sin(2*np.pi*7.2*t)  * 0.00007 * SR
    idx  = np.clip(np.arange(n) + (wow + flt).astype(int), 0, n-1)
    return audio[idx] + crk

def tape_saturation(audio, drive=1.25):
    sat = np.tanh(audio * drive) / drive
    h2  = 0.035 * (np.tanh(audio * drive * 2) ** 2)
    return sat + h2

def sidechain_duck(audio, strength=0.30):
    n        = len(audio)
    duck_env = np.ones(n)
    release  = int(0.16 * SR)
    beat_num = 0
    while True:
        b_in_bar = beat_num % 4
        t_pos    = (beat_num // 4) * BAR + b_in_bar * BEAT
        idx      = int(t_pos * SR)
        if idx >= n: break
        if b_in_bar == 0 or (b_in_bar == 2 and random.random() < 0.85):
            end = min(idx + release, n)
            dl  = end - idx
            duck_env[idx:end] = np.minimum(
                duck_env[idx:end],
                np.linspace(1 - strength, 1.0, dl) ** 2
            )
        beat_num += 1
    return audio * duck_env

def stereo_widen(mono, width_ms=7.2, chorus_depth=0.0007):
    n   = len(mono)
    t   = np.arange(n) / SR
    mod = np.sin(2*np.pi*0.32*t) * chorus_depth * SR
    idx = np.clip(np.arange(n) + mod.astype(int), 0, n-1)
    right = mono[idx] * 0.93
    return np.vstack([mono, right]).T

# ── Build musik (~5 menit base, lalu loop ke 1 jam) ──────────────────
BASE_MINUTES = 5
base_dur     = BASE_MINUTES * 60
N            = int(SR * base_dur)
music        = np.zeros(N)
bars         = int(base_dur / BAR)

PROGRESSIONS = {
    "minor":  [
        [[0,2,4],[5,0,2],[3,5,0],[4,6,1]],
        [[0,3,5],[6,1,3],[4,6,1],[5,0,2]],
        [[0,2,4],[3,5,0],[6,1,3],[5,0,2]],
    ],
    "dorian": [
        [[0,2,4],[3,5,0],[1,3,5],[4,6,1]],
        [[0,4,6],[3,5,0],[1,3,5],[4,6,1]],
    ],
    "major":  [
        [[0,2,4],[3,5,0],[4,6,1],[3,5,0]],
        [[0,2,4],[5,0,2],[3,5,0],[4,6,1]],
    ],
}
progression = random.choice(PROGRESSIONS[scale_name])

print("🎹 Generating Rhodes chords...")
for bar in range(bars):
    chord = strum_chord(
        progression[bar % len(progression)],
        BAR + random.uniform(-0.008, 0.008),
        velocity=random.uniform(0.62, 0.76)
    )
    idx = int(bar * BAR * SR)
    end = min(idx + len(chord), N)
    music[idx:end] += chord[:end-idx] * 0.46

print("🎵 Generating melody...")
melody_pen = [0, 2, 4, 7, 9]
for beat_num in range(int(base_dur / BEAT) * 2):
    if random.random() < 0.36:
        t_pos = beat_num * BEAT * 0.5 + random.uniform(-0.012, 0.012)
        idx   = int(t_pos * SR)
        if not (0 <= idx < N): continue
        deg  = random.choice(melody_pen)
        vel  = random.uniform(0.32, 0.58)
        dur  = BEAT * random.uniform(0.28, 0.78)
        tone = rhodes_tone(note_freq(root, deg, 2), dur, vel)
        end  = min(idx + len(tone), N)
        music[idx:end] += tone[:end-idx] * 0.21

print("🎸 Generating bass...")
for bar in range(bars):
    chord_deg = progression[bar % len(progression)][0]
    for beat_b in range(4):
        if   beat_b == 0:             pass
        elif beat_b == 2:
            if random.random() > 0.88: continue
        elif beat_b in (1, 3):
            if random.random() > 0.30: continue
        t_pos = bar * BAR + beat_b * BEAT + random.uniform(-0.005, 0.005)
        idx   = int(t_pos * SR)
        if idx >= N: break
        dur  = BEAT * (0.72 if beat_b % 2 == 0 else 0.38)
        bass = make_bass_note(chord_deg, dur)
        end  = min(idx + len(bass), N)
        music[idx:end] += bass[:end-idx]

print("🥁 Generating drums...")
kick_s  = make_kick()
snare_s = make_snare()
ghost_s = make_ghost()
hh_c    = make_hihat(False)
hh_o    = make_hihat(True)

for beat_num in range(int(base_dur / BEAT)):
    t_pos    = beat_num * BEAT
    idx      = int(t_pos * SR)
    if idx >= N: break
    b_in_bar = beat_num % 4

    if b_in_bar == 0 or (b_in_bar == 2 and random.random() < 0.84):
        e = min(idx + len(kick_s), N)
        music[idx:e] += kick_s[:e-idx] * random.uniform(0.86, 1.0)

    if b_in_bar in (1, 3):
        e = min(idx + len(snare_s), N)
        music[idx:e] += snare_s[:e-idx] * random.uniform(0.82, 1.0)

    if b_in_bar not in (1, 3) and random.random() < 0.22:
        g_idx = idx + int(BEAT * 0.5 * SR)
        if g_idx < N:
            e = min(g_idx + len(ghost_s), N)
            music[g_idx:e] += ghost_s[:e-g_idx] * random.uniform(0.35, 0.55)

    hat_delay = int(random.uniform(-0.004, 0.006) * SR)
    hi        = max(0, idx + hat_delay)
    if beat_num % 2 == 1 and random.random() < 0.18:
        hat = hh_o; h_vel = random.uniform(0.75, 1.0)
    else:
        hat = hh_c; h_vel = random.uniform(0.55, 0.95)
    e = min(hi + len(hat), N)
    music[hi:e] += hat[:e-hi] * h_vel

# ── Effects chain ─────────────────────────────────────────────────────
print("🎛️  Processing effects chain...")
music = lofi_eq(music)
music = room_reverb(music, wet=mood["reverb"])
music = sidechain_duck(music, strength=0.28)
music = vinyl_crackle(music, intensity=mood["crackle"])
music = tape_saturation(music, drive=mood["saturation"])
music = music / (np.max(np.abs(music)) + 1e-9) * 0.88

# Loop ke durasi final lalu stereo widen
loops  = int(np.ceil(FINAL_DURATION / base_dur))
full   = np.tile(music, loops)[:SR * FINAL_DURATION]
stereo = stereo_widen(full, width_ms=7.2, chorus_depth=0.0007)
sf.write(WAV_OUTPUT, stereo, SR)
print(f"✅ Audio selesai: {WAV_OUTPUT}")

# ── VIDEO ─────────────────────────────────────────────────────────────
print("\n🎬 Rendering video...")

W, H       = 1280, 720
FPS        = 24
audio_clip = AudioFileClip(WAV_OUTPUT)
duration   = audio_clip.duration

# Gradient background
col1, col2 = mood["grad"]
grad = np.zeros((H, W, 3), dtype=np.uint8)
for y in range(H):
    grad[y] = [
        max(0,min(255, int(col1[0] + (col2[0]-col1[0])*y/H))),
        max(0,min(255, int(col1[1] + (col2[1]-col1[1])*y/H))),
        max(0,min(255, int(col1[2] + (col2[2]-col1[2])*y/H))),
    ]
bg_clip = ImageClip(grad).set_duration(duration)

# Floating boxes
box_colors = mood["palette"]
box_data   = [{
    'x0':  random.uniform(0, W),
    'y0':  random.uniform(0, H),
    'vx':  (random.random()-0.5)*2 * 3.8,
    'vy':  (random.random()-0.5)*2 * 3.8,
    's':   random.randint(18, 70),
    'op':  random.uniform(0.07, 0.20),
    'col': random.choice(box_colors),
} for _ in range(22)]

boxes_clips = []
for b in box_data:
    clip = (ColorClip((b['s'], b['s']), color=b['col'])
            .set_opacity(b['op'])
            .set_duration(duration)
            .set_position(lambda t, bd=b: (
                (bd['x0'] + bd['vx']*t*28) % W,
                (bd['y0'] + bd['vy']*t*28) % H
            )))
    boxes_clips.append(clip)

# BPM Visualizer
BEAT_INTERVAL = 60.0 / BPM
def make_beat_frame(t):
    phase = (t % BEAT_INTERVAL) / BEAT_INTERVAL
    pulse = np.exp(-phase * 7) if phase < 0.6 else 0.0
    bar_h = int(5 + pulse * 20)
    img   = Image.new("RGBA", (130, 32), (0,0,0,0))
    d     = ImageDraw.Draw(img)
    for i in range(8):
        alpha = int(70 + pulse * 130)
        d.rectangle([i*16, 32-bar_h, i*16+11, 32], fill=(*box_colors[0], alpha))
    # ── FIX: flatten RGBA → RGB against black background ──────────────
    # Sample gradient color at the bottom-center of the screen
    bg_color = tuple(grad[H-48, W//2].tolist())
    bg = Image.new("RGB", img.size, bg_color)
    bg.paste(img, mask=img.split()[3])
    return np.array(bg)

beat_clip = (VideoClip(make_beat_frame, duration=duration, ismask=False)
             .set_position((W//2-65, H-65)))

# Text overlay
try:
    font_hook = ImageFont.truetype("DejaVuSans-Bold.ttf", 52)
    font_ch   = ImageFont.truetype("DejaVuSans.ttf", 23)
    font_bpm  = ImageFont.truetype("DejaVuSans.ttf", 15)
except:
    font_hook = ImageFont.load_default()
    font_ch   = ImageFont.load_default()
    font_bpm  = ImageFont.load_default()

bpm_label = f"{BPM} BPM • {scale_name} • lofi"
tmp   = Image.new("RGBA", (W, H), (0,0,0,0))
d     = ImageDraw.Draw(tmp)
hbbox = d.textbbox((0,0), hook_video,   font=font_hook)
cbbox = d.textbbox((0,0), CHANNEL_NAME, font=font_ch)
bbbox = d.textbbox((0,0), bpm_label,    font=font_bpm)
TW,TH = hbbox[2]-hbbox[0], hbbox[3]-hbbox[1]
CW    = cbbox[2]-cbbox[0]
BW    = bbbox[2]-bbbox[0]
pad   = 22
txt_w = max(TW, CW, BW) + pad*2
txt_h = TH + 40 + 22 + pad*2

txt_img = Image.new("RGBA", (txt_w, txt_h), (0,0,0,0))
td      = ImageDraw.Draw(txt_img)
for dx, dy in [(-3,0),(3,0),(0,-3),(0,3),(-2,-2),(2,2),(-1,-1),(1,1)]:
    td.text((txt_w//2-TW//2+dx, pad+dy), hook_video, font=font_hook, fill=(*box_colors[0], 40))
td.text((txt_w//2-TW//2, pad),       hook_video,   font=font_hook, fill=(255,255,255,228))
td.text((txt_w//2-CW//2, pad+TH+14), CHANNEL_NAME, font=font_ch,   fill=(180,165,220,168))
td.text((txt_w//2-BW//2, pad+TH+40), bpm_label,    font=font_bpm,  fill=(150,140,190,128))

RX = (W - txt_w) * 0.29
RY = (H - txt_h) * 0.27
CX = W/2 - txt_w/2
CY = H/2 - txt_h/2
text_clip = (ImageClip(np.array(txt_img))
             .set_duration(duration)
             .set_position(lambda t: (
                 CX + RX * np.sin(t * 0.17),
                 CY + RY * np.sin(t * 0.12)
             )))

# Composite & export
final = CompositeVideoClip(
    [bg_clip] + boxes_clips + [beat_clip, text_clip], size=(W, H)
)
final = final.set_audio(audio_clip)
final.write_videofile(
    VIDEO_OUTPUT, fps=FPS,
    codec="libx264", audio_codec="aac",
    preset="ultrafast", threads=4,
)
print(f"\n✅ SELESAI: {VIDEO_OUTPUT}")
