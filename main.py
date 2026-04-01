# ============================================================
# DRIFTORY - GENERATIVE LOFI ENGINE v6
# 100% Python • No API • No GPU • Berjalan di GitHub Actions
# FM Rhodes Synth • Layered Drums • Sidechain • Tape Saturation
# Vinyl Crackle • Room Reverb • Stereo Widening • 1-Jam Auto Loop
# UPGRADE v6: Swing groove, phrase melody, walking bass, humanized drums
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
FINAL_DURATION = 300
WAV_OUTPUT     = "lofi_output.wav"
VIDEO_OUTPUT   = "final_video.mp4"
CHANNEL_NAME   = "Driftory"

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

SCALES = {
    "minor":  [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "major":  [0, 2, 4, 5, 7, 9, 11],
}
scale = SCALES[scale_name]

# ── Swing quantization helper ─────────────────────────────────────────
SWING = 0.58   # 0.5 = straight, 0.67 = heavy swing
def swing_offset(eighth_idx):
    """Return time offset in seconds for a given eighth-note index with swing."""
    beat_idx   = eighth_idx // 2
    sub_idx    = eighth_idx % 2
    beat_time  = beat_idx * BEAT
    if sub_idx == 0:
        return beat_time
    else:
        return beat_time + BEAT * SWING

def note_freq(base, degree, octave=0):
    semitone = scale[degree % len(scale)] + (degree // len(scale)) * 12
    return base * (2 ** (semitone / 12)) * (2 ** octave)

# ── FM Rhodes synthesizer v2 — richer harmonics, velocity-sensitive ───
def rhodes_tone(freq, duration, velocity=0.8):
    n  = int(SR * duration)
    t  = np.linspace(0, duration, n, endpoint=False)

    # FM: velocity affects modulation index (harder hit = brighter)
    mod_ratio = 2.0
    mod_index = 1.4 + velocity * 0.9
    modulator  = np.sin(2 * np.pi * freq * mod_ratio * t)
    modulator2 = np.sin(2 * np.pi * freq * 3.0 * t) * 0.3
    carrier    = np.sin(2 * np.pi * freq * t + mod_index * (modulator + modulator2))

    # Richer harmonics
    h2   = 0.18 * np.sin(2 * np.pi * freq * 2 * t)
    h3   = 0.07 * np.sin(2 * np.pi * freq * 3 * t)
    h4   = 0.03 * np.sin(2 * np.pi * freq * 4 * t)
    wave = carrier + h2 + h3 + h4

    # Velocity-sensitive envelope (harder = longer sustain)
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

    # Subtle key-click at attack
    click_len = min(int(0.001 * SR), n)
    click     = np.random.randn(click_len) * velocity * 0.06
    wave[:click_len] += click

    # Tremolo (speed varies slightly per note for naturalness)
    trem_rate = random.uniform(4.8, 5.8)
    trem_depth = 0.028 + velocity * 0.015
    trem      = 1.0 + trem_depth * np.sin(2 * np.pi * trem_rate * t)

    return wave * env * trem * velocity * 0.85

# ── Chord voicing — spread voicing, humanized strum & timing ─────────
def strum_chord(degrees, duration, velocity=0.72, strum_ms=18):
    n    = int(SR * duration)
    wave = np.zeros(n)

    # Bass note an octave down, slightly ahead of the strum
    bf   = note_freq(root, degrees[0], -1)
    bass = rhodes_tone(bf, duration, velocity * 0.55)
    wave[:len(bass)] += bass * 0.48

    # Inner voices with slight random strum offset
    strum_offsets = sorted([random.uniform(0, strum_ms * 0.001) for _ in degrees])
    for i, deg in enumerate(degrees):
        oct_        = 1 if i == len(degrees) - 1 else 0
        freq        = note_freq(root, deg, oct_)
        strum_delay = int(strum_offsets[i] * SR)
        v           = velocity * random.uniform(0.78, 1.04)
        tone        = rhodes_tone(freq, duration, v)
        end         = min(strum_delay + len(tone), n)
        wave[strum_delay:end] += tone[:end - strum_delay]

    # Small random timing nudge for the whole chord (human feel)
    nudge = int(random.uniform(-0.006, 0.009) * SR)
    if nudge > 0:
        wave = np.concatenate([np.zeros(nudge), wave[:-nudge]])
    elif nudge < 0:
        wave = np.concatenate([wave[-nudge:], np.zeros(-nudge)])

    return wave / (len(degrees) + 1.2)

# ── Sub bass — walking jazz-style ────────────────────────────────────
def make_bass_note(freq, duration):
    n    = int(SR * duration)
    t    = np.linspace(0, duration, n, endpoint=False)

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

def approach_note(target_freq, semitones=1):
    """Chromatic approach note a half-step below."""
    return target_freq * (2 ** (-semitones / 12))

# ── Drum synthesizer v2 — more character ─────────────────────────────
def make_kick(variation=0):
    dur   = 0.55; n = int(SR * dur); t = np.linspace(0, dur, n)
    if variation == 0:
        freq  = np.linspace(195, 42, n)
    else:
        freq  = np.linspace(175, 38, n)  # slightly deeper on alt hit
    phase = np.cumsum(2 * np.pi * freq / SR)
    body  = np.sin(phase) * np.exp(-t * 8.5) * 0.90
    click_len = int(0.004 * SR)
    click = np.random.randn(click_len) * np.linspace(1, 0, click_len)
    body[:click_len] += click * 0.28
    # Subtle pitch mod for analog feel
    body *= (1.0 + 0.04 * np.exp(-t * 40))
    return np.tanh(body * 1.7) / 1.7

def make_snare(ghost=False):
    if ghost:
        vel_scale = random.uniform(0.08, 0.18)
        dur = 0.12
    else:
        vel_scale = random.uniform(0.80, 1.0)
        dur = 0.22
    n    = int(SR * dur); t = np.linspace(0, dur, n)
    tone = (
        np.sin(2*np.pi*185*t)*0.40 +
        np.sin(2*np.pi*255*t)*0.16 +
        np.sin(2*np.pi*310*t)*0.06
    ) * np.exp(-t * 28)
    noise = np.random.randn(n)
    b, a  = signal.butter(3, [800/(SR/2), 9000/(SR/2)], btype='band')
    noise = signal.lfilter(b, a, noise) * np.exp(-t * (18 if ghost else 13))
    result = (tone * 0.35 + noise * 0.65) * np.exp(-t * 4.5) * 0.58
    return result * vel_scale

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
    """Rimshot — adds jazz feel."""
    dur  = 0.08; n = int(SR * dur); t = np.linspace(0, dur, n)
    tone = np.sin(2*np.pi*750*t) * np.exp(-t * 65) * 0.5
    click = np.random.randn(n) * np.exp(-t * 200) * 0.4
    b, a  = signal.butter(3, 3000/(SR/2), btype='high')
    return signal.lfilter(b, a, tone + click) * 0.22

# ── Phrase-based melody generator ────────────────────────────────────
def generate_melody_phrase(scale_degrees, bars=2):
    """
    Generate a 2-bar melodic phrase with motivic development.
    Returns list of (eighth_idx, degree, octave, duration_beats, velocity).
    """
    # Build a short motif (3-5 notes) then develop it
    motif_len  = random.randint(3, 5)
    motif_degs = [random.choice(scale_degrees) for _ in range(motif_len)]
    motif_vels = [random.uniform(0.38, 0.62) for _ in range(motif_len)]

    notes = []
    eighths_per_bar = 8
    total_eighths   = bars * eighths_per_bar
    e = 0
    phrase_phase = 0  # 0=statement, 1=response/development

    while e < total_eighths - 1:
        if phrase_phase == 0:
            # Statement: play motif with gaps
            for mi, (deg, vel) in enumerate(zip(motif_degs, motif_vels)):
                if e >= total_eighths - 1: break
                dur_e = random.choice([1, 1, 2, 2, 3])
                notes.append((e, deg, 2, dur_e * BEAT / 2, vel))
                e += dur_e
                # small gap sometimes
                if random.random() < 0.35:
                    e += random.choice([1, 2])
            phrase_phase = 1
            e += random.choice([1, 2, 3])  # breath
        else:
            # Response: transposed or inverted fragment
            frag_len = random.randint(2, 3)
            for fi in range(frag_len):
                if e >= total_eighths - 1: break
                # Transpose motif up or down by 1-2 scale degrees
                base_deg = motif_degs[fi % len(motif_degs)]
                shift    = random.choice([-2, -1, 0, 1, 2])
                deg      = (base_deg + shift) % len(scale)
                vel      = motif_vels[fi % len(motif_vels)] * random.uniform(0.85, 1.05)
                dur_e    = random.choice([1, 2, 2])
                notes.append((e, deg, 2, dur_e * BEAT / 2, min(vel, 0.68)))
                e += dur_e
                if random.random() < 0.3:
                    e += 1
            phrase_phase = 0
            e += random.choice([2, 3, 4])

    return notes

# ── Effect chain (unchanged, proven) ──────────────────────────────────
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

PROGRESSIONS = {
    "minor":  [
        [[0,2,4],[5,0,2],[3,5,0],[4,6,1]],
        [[0,2,4],[3,5,0],[6,1,3],[5,0,2]],
        [[0,3,5],[6,1,3],[4,6,1],[5,0,2]],
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

# ── Rhodes chords with rhythmic variation ─────────────────────────────
print("🎹 Generating Rhodes chords...")

# Chord rhythm patterns (in beats): where to hit per bar
CHORD_RHYTHMS = [
    [0, 1.5, 2, 3.5],          # classic lofi on-off
    [0, 1.5, 3],                # sparse
    [0, 2, 2.5, 3.5],           # syncopated
    [0, 0.5, 2, 3],             # early attack
]

for bar in range(bars):
    chord_deg = progression[bar % len(progression)]
    rhythm    = random.choice(CHORD_RHYTHMS)

    for beat_offset in rhythm:
        # Humanize timing
        nudge  = random.uniform(-0.012, 0.018)
        t_pos  = bar * BAR + beat_offset * BEAT + nudge
        idx    = int(t_pos * SR)
        if not (0 <= idx < N): continue

        # Note duration varies with rhythm position
        if beat_offset == 0:
            dur = BAR * random.uniform(0.55, 0.75)
        else:
            dur = BEAT * random.uniform(0.55, 0.90)

        vel   = random.uniform(0.60, 0.78)
        chord = strum_chord(chord_deg, dur, velocity=vel)
        end   = min(idx + len(chord), N)
        music[idx:end] += chord[:end-idx] * 0.44

# ── Phrase-based melody ───────────────────────────────────────────────
print("🎵 Generating melody phrases...")

melody_scale = list(range(len(scale)))   # all degrees
melody_pen   = [0, 2, 4, 5, 6]          # pentatonic-ish subset

# Generate phrases every 2 bars, sometimes rest
bar_idx = 0
while bar_idx < bars:
    # Rest for 0 or 1 bar occasionally
    if random.random() < 0.25:
        bar_idx += random.choice([1, 2])
        continue

    phrase_bars = random.choice([2, 2, 4])
    use_degrees = melody_pen if random.random() < 0.65 else melody_scale

    notes = generate_melody_phrase(use_degrees, bars=min(phrase_bars, bars - bar_idx))

    for (eighth_idx, degree, octave, dur, vel) in notes:
        t_pos = bar_idx * BAR + swing_offset(eighth_idx)
        idx   = int(t_pos * SR)
        if not (0 <= idx < N): continue
        freq = note_freq(root, degree, octave)
        tone = rhodes_tone(freq, dur, vel)
        end  = min(idx + len(tone), N)
        music[idx:end] += tone[:end-idx] * 0.22

    bar_idx += phrase_bars

# ── Walking bass ──────────────────────────────────────────────────────
print("🎸 Generating walking bass...")

for bar in range(bars):
    chord_deg    = progression[bar % len(progression)]
    root_f       = chord_root_freq(chord_deg, octave=-1)
    next_chord   = progression[(bar + 1) % len(progression)]
    next_root_f  = chord_root_freq(next_chord, octave=-1)

    # Beat 1: root
    beats_played = []

    def add_bass(beat_offset, freq, duration=None):
        dur_  = duration or (BEAT * 0.82)
        nudge = random.uniform(-0.006, 0.008)
        t_pos = bar * BAR + beat_offset * BEAT + nudge
        idx   = int(t_pos * SR)
        if 0 <= idx < N:
            note = make_bass_note(freq, dur_)
            end  = min(idx + len(note), N)
            music[idx:end] += note[:end-idx]
        beats_played.append(beat_offset)

    # Beat 1: always root
    add_bass(0, root_f, BEAT * 0.88)

    # Beat 2: fifth or third of chord
    fifth_f = root_f * (2 ** (7/12))
    third_f = root_f * (2 ** (scale[2]/12))
    add_bass(1 + random.uniform(-0.01, 0.01),
             random.choice([fifth_f, third_f]),
             BEAT * 0.75)

    # Beat 3: walking note (scale step toward beat 4)
    walk_up = root_f * (2 ** (scale[2]/12))   # minor/major third
    add_bass(2 + random.uniform(-0.008, 0.008),
             walk_up, BEAT * 0.75)

    # Beat 4: approach note to next bar's root (chromatic or diatonic)
    if random.random() < 0.55:
        approach_f = approach_note(next_root_f, semitones=random.choice([1, 2]))
    else:
        approach_f = root_f * (2 ** (scale[4]/12))  # fifth as approach
    add_bass(3 + random.uniform(-0.008, 0.012),
             approach_f, BEAT * 0.65)

    # Occasional 8th-note fill on beat 2.5 or 3.5
    if random.random() < 0.30:
        fill_f = root_f * (2 ** (random.choice(scale[:5]) / 12))
        add_bass(2.5 + random.uniform(-0.01, 0.01), fill_f, BEAT * 0.40)

# ── Drums with humanized groove ───────────────────────────────────────
print("🥁 Generating drums...")

kick_samples  = [make_kick(0), make_kick(1)]
snare_sample  = make_snare(ghost=False)
ghost_sample  = make_snare(ghost=True)
hh_closed     = make_hihat(False)
hh_open       = make_hihat(True)
rim_sample    = make_rim()

# Per-beat timing pool (subtle humanization in ms)
def human_idx(t_pos, ms_range=9):
    nudge = random.gauss(0, ms_range * 0.001 * 0.5) * SR
    return int(t_pos * SR + nudge)

def add_drum(buf, sample, idx, vel=1.0):
    end = min(idx + len(sample), N)
    if idx >= 0:
        buf[idx:end] += sample[:end-idx] * vel

# Hi-hat pattern builder (16th-note grid with swing)
for bar in range(bars):
    bar_t = bar * BAR

    # Kick: beat 1 always, beat 3 often, occasional syncopation
    add_drum(music, random.choice(kick_samples),
             human_idx(bar_t + 0 * BEAT), random.uniform(0.88, 1.0))

    if random.random() < 0.82:
        add_drum(music, random.choice(kick_samples),
                 human_idx(bar_t + 2 * BEAT), random.uniform(0.75, 0.92))

    # Syncopated kick on beat 2.5 sometimes
    if random.random() < 0.30:
        add_drum(music, random.choice(kick_samples),
                 human_idx(bar_t + swing_offset(5)),   # eighth 5 = beat 2.5 swung
                 random.uniform(0.55, 0.72))

    # Snare: beats 2 and 4 (core backbeat)
    add_drum(music, snare_sample,
             human_idx(bar_t + 1 * BEAT), random.uniform(0.82, 1.0))
    add_drum(music, snare_sample,
             human_idx(bar_t + 3 * BEAT), random.uniform(0.80, 0.97))

    # Ghost notes: 1-3 random 16th positions
    ghost_positions = random.sample([0.25, 0.5, 0.75, 1.25, 1.75,
                                     2.25, 2.75, 3.25, 3.75], k=random.randint(1,3))
    for gp in ghost_positions:
        if random.random() < 0.55:
            add_drum(music, ghost_sample,
                     human_idx(bar_t + gp * BEAT),
                     random.uniform(0.12, 0.28))

    # Hi-hats on 8th-note grid (swung)
    for e_idx in range(8):
        t_pos = bar_t + swing_offset(e_idx)
        vel   = random.uniform(0.50, 0.95)

        # Beat 2 & 4 upbeats: open hat sometimes
        if e_idx in (3, 7) and random.random() < 0.20:
            hat = hh_open; vel *= 0.85
        else:
            hat = hh_closed

        # Skip occasional 8th for groove
        if random.random() < 0.12:
            continue

        add_drum(music, hat, human_idx(t_pos, ms_range=5), vel)

    # Rim on beat 2 or 4 occasionally (replaces or layers snare)
    if random.random() < 0.18:
        rim_beat = random.choice([1, 3])
        add_drum(music, rim_sample,
                 human_idx(bar_t + rim_beat * BEAT),
                 random.uniform(0.30, 0.55))

# ── Effects chain ─────────────────────────────────────────────────────
print("🎛️  Processing effects chain...")
music = lofi_eq(music)
music = room_reverb(music, wet=mood["reverb"])
music = sidechain_duck(music, strength=0.28)
music = vinyl_crackle(music, intensity=mood["crackle"])
music = tape_saturation(music, drive=mood["saturation"])
music = music / (np.max(np.abs(music)) + 1e-9) * 0.88

loops  = int(np.ceil(FINAL_DURATION / base_dur))
full   = np.tile(music, loops)[:SR * FINAL_DURATION]
stereo = stereo_widen(full, width_ms=7.2, chorus_depth=0.0007)
sf.write(WAV_OUTPUT, stereo, SR)
print(f"✅ Audio selesai: {WAV_OUTPUT}")

# ── VIDEO (unchanged from your working version) ────────────────────────
print("\n🎬 Rendering video...")

W, H       = 1280, 720
FPS        = 24
audio_clip = AudioFileClip(WAV_OUTPUT)
duration   = audio_clip.duration

col1, col2 = mood["grad"]
grad = np.zeros((H, W, 3), dtype=np.uint8)
for y in range(H):
    grad[y] = [
        max(0,min(255, int(col1[0] + (col2[0]-col1[0])*y/H))),
        max(0,min(255, int(col1[1] + (col2[1]-col1[1])*y/H))),
        max(0,min(255, int(col1[2] + (col2[2]-col1[2])*y/H))),
    ]
bg_clip = ImageClip(grad).set_duration(duration)

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
    bg_color = tuple(grad[H-48, W//2].tolist())
    bg = Image.new("RGB", img.size, bg_color)
    bg.paste(img, mask=img.split()[3])
    return np.array(bg)

beat_clip = (VideoClip(make_beat_frame, duration=duration, ismask=False)
             .set_position((W//2-65, H-65)))

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
