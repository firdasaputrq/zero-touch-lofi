# ============================================================
# DRIFTORY - GENERATIVE LOFI ENGINE v7
# 100% Python • No API • No GPU • Berjalan di GitHub Actions
# ─────────────────────────────────────────────────────────────
# UPGRADE v7:
#   • FM Rhodes synth (velocity-sensitive, key-click, tremolo)
#   • Swing quantization (ratio 0.58, jazz feel)
#   • Chord-conditioned melody (jacbz/Lofi insight)
#   • Probabilistic note duration (mtsandra insight)
#   • Section structure: intro → verse → bridge → verse2 → outro
#   • Walking bass: root → fifth → walk → chromatic approach
#   • Ghost notes, rim shot, humanized drum grid
#   • Tape saturation, room reverb, vinyl crackle, sidechain
#   • Stereo widening via chorus delay
#   • RGBA→RGB fix untuk beat visualizer (MoviePy compat)
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
FINAL_DURATION = 300   # detik — ganti ke 3600 untuk 1 jam
WAV_OUTPUT     = "lofi_output.wav"
VIDEO_OUTPUT   = "final_video.mp4"
CHANNEL_NAME   = "Driftory"

# ── Mood presets ──────────────────────────────────────────────────────
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

ROOT_FREQS = [65.41,73.42,82.41,87.31,98.00,110.00,123.47,130.81,146.83,164.81,174.61,196.00]
root       = ROOT_FREQS[mood["root_idx"]]

with open("hook.txt", "w", encoding="utf-8") as f:
    f.write(f"{hook_meta}\n{scale_name}\n{BPM}")

print(f"🎵 Mood: {mood_key} | Scale: {scale_name} | BPM: {BPM} | Hook: {hook_meta}")

# ── Scale definitions ─────────────────────────────────────────────────
SCALES = {
    "minor":  [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "major":  [0, 2, 4, 5, 7, 9, 11],
}
scale = SCALES[scale_name]

# ── Chord progressions (Roman numeral style, dari real lofi songs) ────
# Berdasarkan dataset jacbz/Lofi: progressi paling umum dari Hooktheory
PROGRESSIONS = {
    "minor":  [
        [[0,2,4],[5,0,2],[3,5,0],[4,6,1]],   # i-VI-III-VII
        [[0,2,4],[3,5,0],[6,1,3],[5,0,2]],   # i-III-VI-VII
        [[0,3,5],[6,1,3],[4,6,1],[5,0,2]],   # i-VI-iv-VII
    ],
    "dorian": [
        [[0,2,4],[3,5,0],[1,3,5],[4,6,1]],
        [[0,4,6],[3,5,0],[1,3,5],[4,6,1]],
    ],
    "major":  [
        [[0,2,4],[3,5,0],[4,6,1],[3,5,0]],   # I-IV-V-IV
        [[0,2,4],[5,0,2],[3,5,0],[4,6,1]],   # I-vi-IV-V
    ],
}
progression = random.choice(PROGRESSIONS[scale_name])

# ── Chord tone map — untuk chord-conditioned melody (jacbz insight) ───
# Melody hanya menggunakan chord tones + passing tones yang enak
def get_chord_tones(chord_degrees):
    """Return scale degrees yang 'safe' dimainkan di atas chord ini."""
    chord_set = set(chord_degrees)
    # Tambah tetangga terdekat sebagai passing tones
    passing = set()
    for d in chord_degrees:
        passing.add((d + 1) % len(scale))
        passing.add((d - 1) % len(scale))
    return list(chord_set | passing)

# ── Swing quantization ────────────────────────────────────────────────
SWING = 0.58   # 0.5 = straight, 0.67 = heavy swing
def swing_offset(eighth_idx):
    """Return time offset (detik) untuk eighth-note index dengan swing."""
    beat_idx = eighth_idx // 2
    sub_idx  = eighth_idx % 2
    beat_time = beat_idx * BEAT
    if sub_idx == 0:
        return beat_time
    else:
        return beat_time + BEAT * SWING

def note_freq(base, degree, octave=0):
    semitone = scale[degree % len(scale)] + (degree // len(scale)) * 12
    return base * (2 ** (semitone / 12)) * (2 ** octave)

# ── FM Rhodes synthesizer (velocity-sensitive, key-click, tremolo) ────
def rhodes_tone(freq, duration, velocity=0.8):
    n = int(SR * duration)
    if n <= 0:
        return np.zeros(1)
    t = np.linspace(0, duration, n, endpoint=False)

    # FM: harder hit = brighter (higher mod index)
    mod_ratio  = 2.0
    mod_index  = 1.4 + velocity * 0.9
    modulator  = np.sin(2 * np.pi * freq * mod_ratio * t)
    modulator2 = np.sin(2 * np.pi * freq * 3.0 * t) * 0.3
    carrier    = np.sin(2 * np.pi * freq * t + mod_index * (modulator + modulator2))

    # Richer harmonics
    h2   = 0.18 * np.sin(2 * np.pi * freq * 2 * t)
    h3   = 0.07 * np.sin(2 * np.pi * freq * 3 * t)
    h4   = 0.03 * np.sin(2 * np.pi * freq * 4 * t)
    wave = carrier + h2 + h3 + h4

    # Velocity-sensitive envelope
    atk  = min(int(0.002 * SR), n)
    dec  = min(int((0.08 + velocity * 0.08) * SR), n - atk)
    sus  = 0.32 + velocity * 0.18
    rel  = min(int((0.30 + velocity * 0.15) * SR), n - atk - dec)
    ss   = max(n - atk - dec - rel, 0)
    env  = np.concatenate([
        np.linspace(0, 1, atk),
        np.linspace(1, sus, dec) ** 1.8,
        np.full(ss, sus),
        np.linspace(sus, 0, rel) ** 2.2,
    ])[:n]

    # Subtle key-click transient (Rhodes fisik)
    click_len = min(int(0.001 * SR), n)
    wave[:click_len] += np.random.randn(click_len) * velocity * 0.06

    # Tremolo (speed random per note = natural)
    trem_rate  = random.uniform(4.8, 5.8)
    trem_depth = 0.028 + velocity * 0.015
    trem       = 1.0 + trem_depth * np.sin(2 * np.pi * trem_rate * t)

    return wave * env * trem * velocity * 0.85

# ── Chord voicing dengan humanized strum ─────────────────────────────
def strum_chord(degrees, duration, velocity=0.72, strum_ms=18):
    n    = int(SR * duration)
    wave = np.zeros(n)

    # Bass note satu oktav di bawah
    bf   = note_freq(root, degrees[0], -1)
    bass = rhodes_tone(bf, duration, velocity * 0.55)
    wave[:len(bass)] += bass * 0.48

    # Strum timing acak (bukan seragam)
    strum_offsets = sorted([random.uniform(0, strum_ms * 0.001) for _ in degrees])
    for i, deg in enumerate(degrees):
        oct_        = 1 if i == len(degrees) - 1 else 0
        freq        = note_freq(root, deg, oct_)
        strum_delay = int(strum_offsets[i] * SR)
        v           = velocity * random.uniform(0.78, 1.04)
        tone        = rhodes_tone(freq, duration, v)
        end         = min(strum_delay + len(tone), n)
        wave[strum_delay:end] += tone[:end - strum_delay]

    return wave / (len(degrees) + 1.2)

# ── Sub bass dengan walking pattern ──────────────────────────────────
def make_bass_note(freq, duration):
    n = int(SR * duration)
    if n <= 0:
        return np.zeros(1)
    t = np.linspace(0, duration, n, endpoint=False)

    sub  = np.sin(2 * np.pi * freq * t)
    oct2 = 0.22 * np.sin(2 * np.pi * freq * 2 * t)
    oct3 = 0.06 * np.sin(2 * np.pi * freq * 3 * t)
    wave = np.tanh((sub + oct2 + oct3) * 1.4)

    atk = min(int(0.006 * SR), n)
    dec = min(int(0.06  * SR), n - atk)
    sus = 0.62
    rel = min(int(0.10  * SR), n - atk - dec)
    ss  = max(n - atk - dec - rel, 0)
    env = np.concatenate([
        np.linspace(0, 1, atk),
        np.linspace(1, sus, dec),
        np.full(ss, sus),
        np.linspace(sus, 0, rel),
    ])[:n]

    b, a = signal.butter(3, 400 / (SR / 2), btype='low')
    return signal.lfilter(b, a, wave * env) * 0.40

def chord_root_freq(chord_degrees, octave=-1):
    return note_freq(root, chord_degrees[0], octave)

def approach_note_freq(target_freq, semitones=1):
    return target_freq * (2 ** (-semitones / 12))

# ── Drum synthesizer ──────────────────────────────────────────────────
def make_kick(variation=0):
    dur   = 0.55; n = int(SR * dur); t = np.linspace(0, dur, n)
    start = 195 if variation == 0 else 175
    end_f = 42  if variation == 0 else 38
    freq  = np.linspace(start, end_f, n)
    phase = np.cumsum(2 * np.pi * freq / SR)
    body  = np.sin(phase) * np.exp(-t * 8.5) * 0.90
    click_len = int(0.004 * SR)
    click = np.random.randn(click_len) * np.linspace(1, 0, click_len)
    body[:click_len] += click * 0.28
    body *= (1.0 + 0.04 * np.exp(-t * 40))
    return np.tanh(body * 1.7) / 1.7

def make_snare(ghost=False):
    vel_scale = random.uniform(0.08, 0.18) if ghost else random.uniform(0.80, 1.0)
    dur = 0.12 if ghost else 0.22
    n    = int(SR * dur); t = np.linspace(0, dur, n)
    tone = (
        np.sin(2*np.pi*185*t)*0.40 +
        np.sin(2*np.pi*255*t)*0.16 +
        np.sin(2*np.pi*310*t)*0.06
    ) * np.exp(-t * 28)
    noise = np.random.randn(n)
    b, a  = signal.butter(3, [800/(SR/2), 9000/(SR/2)], btype='band')
    noise = signal.lfilter(b, a, noise) * np.exp(-t * (18 if ghost else 13))
    return (tone * 0.35 + noise * 0.65) * np.exp(-t * 4.5) * 0.58 * vel_scale

def make_hihat(open_hat=False, vel=1.0):
    dur   = 0.14 if open_hat else 0.028
    n     = int(SR * dur); t = np.linspace(0, dur, n)
    noise = np.random.randn(n)
    b, a  = signal.butter(5, 9000/(SR/2), btype='high')
    metal = signal.lfilter(b, a, noise)
    metal += 0.25 * np.sin(2*np.pi*9800*t)  * np.exp(-t * 90)
    metal += 0.15 * np.sin(2*np.pi*13000*t) * np.exp(-t * 140)
    decay = 6.5 if open_hat else 110
    env   = np.exp(-t * decay)
    return metal * env * 0.10 * vel

def make_rim():
    dur  = 0.08; n = int(SR * dur); t = np.linspace(0, dur, n)
    tone = np.sin(2*np.pi*750*t) * np.exp(-t * 65) * 0.5
    click = np.random.randn(n) * np.exp(-t * 200) * 0.4
    b, a  = signal.butter(3, 3000/(SR/2), btype='high')
    return signal.lfilter(b, a, tone + click) * 0.22

# ── Probabilistic note duration (mtsandra insight) ────────────────────
# Distribusi: 55% eighth, 20% quarter, 10% half, 15% sixteenth
NOTE_DURATIONS  = {1: 0.55, 2: 0.20, 4: 0.10, 0.5: 0.15}
# Default rest: 16th note (70%) agar tidak silent terlalu lama
REST_DURATIONS  = {0.5: 0.70, 1: 0.20, 2: 0.10}

def pick_duration(is_rest=False):
    table = REST_DURATIONS if is_rest else NOTE_DURATIONS
    keys  = list(table.keys())
    probs = list(table.values())
    return random.choices(keys, weights=probs, k=1)[0]

# ── Chord-conditioned melody phrase (jacbz insight) ───────────────────
def generate_melody_phrase(chord_tones, scale_degrees, bars=2):
    """
    Generate phrase yang hanya menggunakan chord tones & passing tones.
    Statement (motif) → Response (transpose/invert) ala jazz improviser.
    """
    allowed   = chord_tones if random.random() < 0.65 else scale_degrees
    motif_len = random.randint(3, 5)
    motif_degs = [random.choice(allowed) for _ in range(motif_len)]
    motif_vels = [random.uniform(0.38, 0.62) for _ in range(motif_len)]

    notes         = []
    total_eighths = bars * 8
    e             = 0
    phrase_phase  = 0  # 0=statement, 1=response

    while e < total_eighths - 1:
        if phrase_phase == 0:
            for mi in range(len(motif_degs)):
                if e >= total_eighths - 1: break
                dur_e = pick_duration(is_rest=False)
                notes.append((e, motif_degs[mi], 2,
                              dur_e * BEAT / 2, motif_vels[mi]))
                e += dur_e
                if random.random() < 0.40:
                    e += pick_duration(is_rest=True)
            phrase_phase = 1
            e += pick_duration(is_rest=True) * random.choice([1, 2])
        else:
            frag_len = random.randint(2, 4)
            for fi in range(frag_len):
                if e >= total_eighths - 1: break
                base_deg = motif_degs[fi % len(motif_degs)]
                shift    = random.choice([-2, -1, 0, 1, 2])
                deg      = (base_deg + shift) % len(scale)
                vel      = motif_vels[fi % len(motif_vels)] * random.uniform(0.85, 1.05)
                dur_e    = pick_duration(is_rest=False)
                notes.append((e, deg, 2, dur_e * BEAT / 2, min(vel, 0.68)))
                e += dur_e
                if random.random() < 0.30:
                    e += pick_duration(is_rest=True)
            phrase_phase = 0
            e += pick_duration(is_rest=True) * random.choice([2, 3])

    return notes

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

# ── Build musik ───────────────────────────────────────────────────────
BASE_MINUTES = 5
base_dur     = BASE_MINUTES * 60
N            = int(SR * base_dur)
music        = np.zeros(N)
bars         = int(base_dur / BAR)

# ── Chord rhythm patterns ─────────────────────────────────────────────
CHORD_RHYTHMS = [
    [0, 1.5, 2, 3.5],   # classic lofi syncopation
    [0, 1.5, 3],         # sparse
    [0, 2, 2.5, 3.5],    # syncopated
    [0, 0.5, 2, 3],      # early attack
]

# ── 1. Rhodes chords ──────────────────────────────────────────────────
print("🎹 Generating Rhodes chords...")
for bar in range(bars):
    chord_deg = progression[bar % len(progression)]
    rhythm    = random.choice(CHORD_RHYTHMS)

    for beat_offset in rhythm:
        nudge = random.uniform(-0.012, 0.018)
        t_pos = bar * BAR + beat_offset * BEAT + nudge
        idx   = int(t_pos * SR)
        if not (0 <= idx < N): continue

        dur = BAR * random.uniform(0.55, 0.75) if beat_offset == 0 \
              else BEAT * random.uniform(0.55, 0.90)
        vel   = random.uniform(0.60, 0.78)
        chord = strum_chord(chord_deg, dur, velocity=vel)
        end   = min(idx + len(chord), N)
        music[idx:end] += chord[:end-idx] * 0.44

# ── 2. Chord-conditioned melody dengan section structure ──────────────
print("🎵 Generating chord-conditioned melody (section structure)...")

# Section structure (inspired by jacbz/Lofi: drum 8 bar, melody 30 bar)
SECTION_BARS = [
    ("intro",   4,  0.15),  # sparse
    ("verse",   16, 0.80),  # aktif
    ("bridge",  8,  0.50),  # lebih breathing
    ("verse2",  16, 0.85),  # paling kaya
    ("outro",   4,  0.20),  # fade ke sepi
]

melody_scale = list(range(len(scale)))

bar_idx = 0
si      = 0
while bar_idx < bars:
    sec_name, sec_len, activity = SECTION_BARS[si % len(SECTION_BARS)]
    actual_len = min(sec_len, bars - bar_idx)
    print(f"   ↳ [{sec_name}] bar {bar_idx}–{bar_idx+actual_len-1} (activity={activity:.0%})")

    inner = 0
    while inner < actual_len:
        if random.random() > activity:
            skip = random.choice([1, 2])
            inner   += skip
            bar_idx += skip
            continue

        phrase_bars = random.choice([2, 2, 4])
        pb          = min(phrase_bars, actual_len - inner)
        if pb <= 0: break

        # Current chord tones untuk kondisi melody
        cur_chord   = progression[bar_idx % len(progression)]
        chord_tones = get_chord_tones(cur_chord)

        notes = generate_melody_phrase(chord_tones, melody_scale, bars=pb)

        for (eighth_idx, degree, octave, dur, vel) in notes:
            t_pos = bar_idx * BAR + swing_offset(eighth_idx)
            idx   = int(t_pos * SR)
            if not (0 <= idx < N): continue
            freq = note_freq(root, degree, octave)
            tone = rhodes_tone(freq, dur, vel)
            end  = min(idx + len(tone), N)
            music[idx:end] += tone[:end-idx] * 0.22

        inner   += pb
        bar_idx += pb

    si += 1

# ── 3. Walking bass ───────────────────────────────────────────────────
print("🎸 Generating walking bass...")
for bar in range(bars):
    chord_deg   = progression[bar % len(progression)]
    next_chord  = progression[(bar + 1) % len(progression)]
    root_f      = chord_root_freq(chord_deg, octave=-1)
    next_root_f = chord_root_freq(next_chord, octave=-1)

    def add_bass_note(beat_offset, freq, duration=None):
        dur_  = duration or (BEAT * 0.82)
        nudge = random.uniform(-0.006, 0.008)
        t_pos = bar * BAR + beat_offset * BEAT + nudge
        idx   = int(t_pos * SR)
        if 0 <= idx < N:
            note = make_bass_note(freq, dur_)
            end  = min(idx + len(note), N)
            music[idx:end] += note[:end-idx]

    # Beat 1: root (always)
    add_bass_note(0, root_f, BEAT * 0.88)

    # Beat 2: fifth atau third dari chord
    fifth_f = root_f * (2 ** (7/12))
    third_f = root_f * (2 ** (scale[2]/12))
    add_bass_note(1 + random.uniform(-0.01, 0.01),
                  random.choice([fifth_f, third_f]), BEAT * 0.75)

    # Beat 3: walking note (skala)
    walk_f = root_f * (2 ** (scale[2]/12))
    add_bass_note(2 + random.uniform(-0.008, 0.008), walk_f, BEAT * 0.75)

    # Beat 4: chromatic approach ke root bar berikutnya
    if random.random() < 0.55:
        approach_f = approach_note_freq(next_root_f, semitones=random.choice([1, 2]))
    else:
        approach_f = root_f * (2 ** (scale[4]/12))
    add_bass_note(3 + random.uniform(-0.008, 0.012), approach_f, BEAT * 0.65)

    # Occasional 8th-note fill (beat 2.5 atau 3.5)
    if random.random() < 0.30:
        fill_f = root_f * (2 ** (random.choice(scale[:5]) / 12))
        add_bass_note(2.5 + random.uniform(-0.01, 0.01), fill_f, BEAT * 0.40)

# ── 4. Drums dengan humanized groove ─────────────────────────────────
print("🥁 Generating drums...")
kick_samples = [make_kick(0), make_kick(1)]
snare_sample = make_snare(ghost=False)
ghost_sample = make_snare(ghost=True)
hh_closed    = make_hihat(False)
hh_open      = make_hihat(True)
rim_sample   = make_rim()

def human_idx(t_pos, ms_range=9):
    nudge = random.gauss(0, ms_range * 0.001 * 0.5) * SR
    return int(t_pos * SR + nudge)

def add_drum(sample, idx, vel=1.0):
    if idx < 0 or idx >= N: return
    end = min(idx + len(sample), N)
    music[idx:end] += sample[:end-idx] * vel

for bar in range(bars):
    bar_t = bar * BAR

    # Kick: beat 1 selalu, beat 3 sering, kadang syncopation
    add_drum(random.choice(kick_samples),
             human_idx(bar_t + 0 * BEAT), random.uniform(0.88, 1.0))
    if random.random() < 0.82:
        add_drum(random.choice(kick_samples),
                 human_idx(bar_t + 2 * BEAT), random.uniform(0.75, 0.92))
    if random.random() < 0.30:
        add_drum(random.choice(kick_samples),
                 human_idx(bar_t + swing_offset(5)),
                 random.uniform(0.55, 0.72))

    # Snare: beat 2 dan 4 (core backbeat)
    add_drum(snare_sample, human_idx(bar_t + 1 * BEAT), random.uniform(0.82, 1.0))
    add_drum(snare_sample, human_idx(bar_t + 3 * BEAT), random.uniform(0.80, 0.97))

    # Ghost notes (1–3 posisi 16th random)
    ghost_positions = random.sample(
        [0.25, 0.5, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75],
        k=random.randint(1, 3)
    )
    for gp in ghost_positions:
        if random.random() < 0.55:
            add_drum(ghost_sample, human_idx(bar_t + gp * BEAT),
                     random.uniform(0.12, 0.28))

    # Hi-hats pada 8th-note grid (dengan swing)
    for e_idx in range(8):
        t_pos = bar_t + swing_offset(e_idx)
        vel   = random.uniform(0.50, 0.95)
        if e_idx in (3, 7) and random.random() < 0.20:
            hat = hh_open; vel *= 0.85
        else:
            hat = hh_closed
        if random.random() < 0.12:  # skip sesekali untuk groove
            continue
        add_drum(hat, human_idx(t_pos, ms_range=5), vel)

    # Rim shot sesekali (jazz feel)
    if random.random() < 0.18:
        rim_beat = random.choice([1, 3])
        add_drum(rim_sample, human_idx(bar_t + rim_beat * BEAT),
                 random.uniform(0.30, 0.55))

# ── Effects chain ─────────────────────────────────────────────────────
print("🎛️  Processing effects chain...")
music = lofi_eq(music)
music = room_reverb(music, wet=mood["reverb"])
music = sidechain_duck(music, strength=0.28)
music = vinyl_crackle(music, intensity=mood["crackle"])
music = tape_saturation(music, drive=mood["saturation"])
music = music / (np.max(np.abs(music)) + 1e-9) * 0.88

# Loop ke FINAL_DURATION
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
        max(0, min(255, int(col1[0] + (col2[0]-col1[0])*y/H))),
        max(0, min(255, int(col1[1] + (col2[1]-col1[1])*y/H))),
        max(0, min(255, int(col1[2] + (col2[2]-col1[2])*y/H))),
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

# BPM Visualizer (RGBA→RGB fix agar tidak crash di MoviePy)
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
    # FIX: flatten RGBA → RGB menggunakan warna gradient sebagai background
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
TW, TH = hbbox[2]-hbbox[0], hbbox[3]-hbbox[1]
CW     = cbbox[2]-cbbox[0]
BW     = bbbox[2]-bbbox[0]
pad    = 22
txt_w  = max(TW, CW, BW) + pad*2
txt_h  = TH + 40 + 22 + pad*2

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
