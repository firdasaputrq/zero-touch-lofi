# ============================================================
# DRIFTORY - GENERATIVE LOFI ENGINE v2
# Modern Lofi Piano • Dynamic Gradient • Animated Text
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
FINAL_DURATION = 300 #3600        # detik (1 jam)
WAV_OUTPUT     = "lofi_output.wav"
VIDEO_OUTPUT   = "final_video.mp4"
CHANNEL_NAME   = "Driftory"

# ── Hook text: (untuk metadata, untuk video layar) ───────────
HOOKS = {
    "minor": [
        ("rainy night feels 🌧️",    "rainy night feels"),
        ("slow down, unwind 🌙",     "slow down, unwind"),
        ("drift into calm 🌊",       "drift into calm"),
        ("soft & still 🕯️",         "soft & still"),
        ("late night peace ✨",      "late night peace"),
        ("just breathe 😮‍💨",         "just breathe"),
        ("quiet hours 🌑",           "quiet hours"),
    ],
    "dorian": [
        ("deep focus mode 🎯",       "deep focus mode"),
        ("locked in 🔒",             "locked in"),
        ("study & flow 📖",          "study & flow"),
        ("zone out, work in 💻",     "zone out, work in"),
        ("mind sharp 🧠",            "mind sharp"),
        ("grind in silence 🖊️",     "grind in silence"),
        ("stay focused 🎧",          "stay focused"),
    ],
    "major": [
        ("good vibes only ☀️",       "good vibes only"),
        ("bright & easy 🌤️",        "bright & easy"),
        ("feel good beats 🌸",       "feel good beats"),
        ("warm afternoon 🌻",        "warm afternoon"),
        ("light & breezy 🎶",        "light & breezy"),
        ("smile & flow 😊",          "smile & flow"),
        ("happy little groove 🎵",   "happy little groove"),
    ],
}

# ── Music setup ───────────────────────────────────────────────
BPM        = random.randint(68, 84)
BEAT       = 60.0 / BPM
BAR        = BEAT * 4
root_notes = [130.81, 146.83, 164.81, 174.61, 196.00]
root       = random.choice(root_notes)
scale_type = random.choice(["minor", "dorian", "major"])
hook_meta, hook_video = random.choice(HOOKS[scale_type])

# Simpan hook untuk dibaca uploader.py
with open("hook.txt", "w", encoding="utf-8") as f:
    f.write(f"{hook_meta}\n{scale_type}\n{BPM}")

print(f"🎵 Scale: {scale_type}  |  BPM: {BPM}  |  Hook: {hook_meta}")

SCALES = {
    "minor":  [0,2,3,5,7,8,10],
    "dorian": [0,2,3,5,7,9,10],
    "major":  [0,2,4,5,7,9,11],
}
scale = SCALES[scale_type]

def note_freq(base, degree, octave=0):
    return base * (2 ** (scale[degree % len(scale)] / 12)) * (2 ** octave)

# ── Piano synthesis ───────────────────────────────────────────
def piano_tone(freq, duration, velocity=0.8):
    n  = int(SR * duration)
    t  = np.linspace(0, duration, n, endpoint=False)
    harmonics = [(1,1.0),(2,0.45),(3,0.20),(4,0.10),(5,0.05),(6,0.02)]
    wave = sum(np.sin(2*np.pi*freq*h*t)*a for h,a in harmonics)
    wave /= sum(a for _,a in harmonics)
    # ADSR envelope
    atk = min(int(0.008*SR), n)
    dec = min(int(0.10*SR),  n-atk)
    sus = 0.55
    rel = min(int(0.20*SR),  n-atk-dec)
    ss  = max(n-atk-dec-rel, 0)
    env = np.concatenate([
        np.linspace(0, 1, atk),
        np.linspace(1, sus, dec),
        np.full(ss, sus),
        np.linspace(sus, 0, rel),
    ])[:n]
    return wave * env * velocity

def piano_chord(root, degrees, duration, velocity=0.75):
    n    = int(SR * duration)
    wave = np.zeros(n)
    # Bass note (satu oktaf di bawah)
    bf = note_freq(root, degrees[0], -1)
    b  = piano_tone(bf, duration, velocity*0.55)
    wave[:len(b)] += b * 0.5
    # Voicing mid & high dengan strum humanization
    for i, deg in enumerate(degrees):
        oct_  = 1 if i == len(degrees)-1 else 0
        freq  = note_freq(root, deg, oct_)
        delay = int(random.uniform(0, 0.012)*SR)
        v     = velocity * random.uniform(0.75, 1.0)
        tone  = piano_tone(freq, duration, v)
        end   = min(delay+len(tone), n)
        wave[delay:end] += tone[:end-delay]
    return wave / (len(degrees)+1)

# ── Drum synthesis ────────────────────────────────────────────
def make_kick():
    dur=0.50; n=int(SR*dur); t=np.linspace(0,dur,n)
    freq  = np.linspace(120, 38, n)
    phase = np.cumsum(2*np.pi*freq/SR)
    body  = np.sin(phase)*np.exp(-t*14)
    cn    = int(0.004*SR)
    body[:cn] += np.random.randn(cn)*np.exp(-np.linspace(0,12,cn))*0.4
    return body*0.85

def make_snare():
    dur=0.25; n=int(SR*dur); t=np.linspace(0,dur,n)
    tone  = np.sin(2*np.pi*185*t)*np.exp(-t*22)*0.35
    noise = np.random.randn(n)*np.exp(-t*12)*0.65
    b,a   = signal.butter(2, 2000/(SR/2), btype='high')
    return signal.lfilter(b,a,tone+noise)*np.exp(-t*8)*0.55

def make_hihat(open_hat=False):
    dur=0.12 if open_hat else 0.04
    n=int(SR*dur); t=np.linspace(0,dur,n)
    noise = np.random.randn(n)
    b,a   = signal.butter(4, 9000/(SR/2), btype='high')
    return signal.lfilter(b,a,noise)*np.exp(-t*(8 if open_hat else 40))*0.18

# ── Audio effects ─────────────────────────────────────────────
def lofi_filter(audio):
    b,a   = signal.butter(4, 9000/(SR/2), btype='low')
    out   = signal.filtfilt(b,a,audio)
    b2,a2 = signal.butter(2,[80/(SR/2),300/(SR/2)],btype='band')
    return out + signal.filtfilt(b2,a2,out)*0.20

def add_reverb(audio, wet=0.28):
    ir_len = int(SR*1.2)
    t_ir   = np.arange(ir_len)/SR
    ir     = np.zeros(ir_len)
    for ms,amp in [(22,.50),(37,.35),(55,.25),(80,.18),(120,.12)]:
        ir[int(ms*SR/1000)] = amp*random.uniform(0.8,1.0)
    tail_s = int(0.05*SR)
    ir[tail_s:] += np.random.randn(ir_len-tail_s)*np.exp(-t_ir[tail_s:]*5)*0.25
    wet_s  = fftconvolve(audio, ir)[:len(audio)]
    peak   = np.max(np.abs(wet_s))+1e-9
    wet_s  = wet_s/peak*np.max(np.abs(audio))
    return audio*(1-wet)+wet_s*wet

def vinyl_warmth(audio):
    audio = audio + np.random.randn(len(audio))*0.004
    t     = np.arange(len(audio))/SR
    shift = (np.sin(2*np.pi*0.6*t)*0.00025*SR).astype(int)
    return audio[np.clip(np.arange(len(audio))+shift, 0, len(audio)-1)]

# ── Build music ───────────────────────────────────────────────
BASE_MINUTES = 5 #8
base_dur = BASE_MINUTES * 60
N        = int(SR * base_dur)
music    = np.zeros(N)

progression_bank = [
    [[0,2,4],[5,0,2],[3,5,0],[6,1,3]],
    [[0,3,5],[4,6,1],[2,4,6],[5,0,2]],
    [[0,4,6],[3,5,0],[1,3,5],[4,6,1]],
]
progression = random.choice(progression_bank)
bars        = int(base_dur / BAR)

def swing_time(beat_num, swing=0.58):
    bar_n = beat_num // 4
    sub   = beat_num % 4
    if sub % 2 == 0:
        return bar_n*BAR + (sub//2)*BEAT*2
    return bar_n*BAR + (sub//2)*BEAT*2 + BEAT*swing*2

print("🎹 Generating piano chords...")
for bar in range(bars):
    chord = piano_chord(root, progression[bar % len(progression)],
                        BAR + random.uniform(-0.01, 0.01))
    idx = int(bar*BAR*SR)
    end = min(idx+len(chord), N)
    music[idx:end] += chord[:end-idx]*0.50

print("🎵 Generating melody...")
for beat_num in range(int(base_dur/BEAT)*2):
    if random.random() < 0.42:
        t_pos = swing_time(beat_num)
        idx   = int(t_pos*SR)+int(random.uniform(-0.01,0.01)*SR)
        if idx < 0 or idx >= N: continue
        dur   = BEAT*random.uniform(0.3, 0.85)
        freq  = note_freq(root, random.choice([0,2,3,4,5,6]), random.choice([1,2]))
        tone  = piano_tone(freq, dur, random.uniform(0.38, 0.68))
        end   = min(idx+len(tone), N)
        music[idx:end] += tone[:end-idx]*0.26

print("🥁 Generating drums...")
kick_s=make_kick(); snare_s=make_snare()
hh_c=make_hihat(False); hh_o=make_hihat(True)

for beat_num in range(int(base_dur/BEAT)):
    idx      = int(swing_time(beat_num)*SR)
    if idx >= N: continue
    b_in_bar = beat_num % 4
    if b_in_bar == 0 or (b_in_bar==2 and random.random()<0.85):
        e = min(idx+len(kick_s),N);  music[idx:e] += kick_s[:e-idx]
    if b_in_bar in (1,3):
        e = min(idx+len(snare_s),N); music[idx:e] += snare_s[:e-idx]
    hat = hh_o if (beat_num%2==1 and random.random()<0.25) else hh_c
    hi  = max(0, idx+int(random.uniform(-0.005,0.005)*SR))
    e   = min(hi+len(hat),N);        music[hi:e] += hat[:e-hi]

print("🎛️ Applying lofi filter, reverb, vinyl warmth...")
music = lofi_filter(music)
music = add_reverb(music, wet=0.28)
music = vinyl_warmth(music)
music = np.tanh(music*1.4)
music = music/(np.max(np.abs(music))+1e-9)*0.88

loops  = int(np.ceil(FINAL_DURATION/base_dur))
full   = np.tile(music, loops)[:SR*FINAL_DURATION]
stereo = np.vstack([full, np.roll(full, 350)]).T
sf.write(WAV_OUTPUT, stereo, SR)
print("✅ Audio selesai")

# ── Video ─────────────────────────────────────────────────────
W, H = 1280, 720
FPS  = 24

audio_clip = AudioFileClip(WAV_OUTPUT)
duration   = audio_clip.duration

# 1. Gradient background (ungu → biru gelap, static)
grad = np.zeros((H, W, 3), dtype=np.uint8)
for y in range(H):
    ratio = y / H
    r = int(28 + ratio*10)
    g = int(15 + ratio*8)
    b = int(80 - ratio*25)
    grad[y] = [max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b))]
bg_clip = ImageClip(grad).set_duration(duration)

# 2. Boxes (20 kotak animasi, speed 4)
SPEED      = 4.0
NUM_BOXES  = 20
box_colors = [(180,160,255),(140,180,255),(160,140,220),(200,160,240),(120,160,240)]

box_data = [{
    'x0':  random.uniform(0, W),
    'y0':  random.uniform(0, H),
    'vx':  (random.random()-0.5)*2 * SPEED,
    'vy':  (random.random()-0.5)*2 * SPEED,
    's':   random.randint(20, 65),
    'op':  random.uniform(0.08, 0.22),
    'col': random.choice(box_colors),
} for _ in range(NUM_BOXES)]

boxes_clips = []
for b in box_data:
    clip = (ColorClip((b['s'], b['s']), color=b['col'])
            .set_opacity(b['op'])
            .set_duration(duration)
            .set_position(lambda t, bd=b: (
                (bd['x0'] + bd['vx']*t*30) % W,
                (bd['y0'] + bd['vy']*t*30) % H
            )))
    boxes_clips.append(clip)

# 3. Text clip (render sekali, posisi Lissajous 60% jangkauan)
try:
    font_hook = ImageFont.truetype("DejaVuSans-Bold.ttf", 54)
    font_ch   = ImageFont.truetype("DejaVuSans.ttf", 24)
except:
    font_hook = ImageFont.load_default()
    font_ch   = ImageFont.load_default()

# Ukur dimensi teks
tmp   = Image.new("RGBA", (W, H), (0,0,0,0))
d     = ImageDraw.Draw(tmp)
hbbox = d.textbbox((0,0), hook_video, font=font_hook)
TW, TH = hbbox[2]-hbbox[0], hbbox[3]-hbbox[1]
cbbox  = d.textbbox((0,0), CHANNEL_NAME, font=font_ch)
CW     = cbbox[2]-cbbox[0]

# Render text ke transparent image
pad     = 24
txt_w   = max(TW, CW) + pad*2
txt_h   = TH + 40 + pad*2
txt_img = Image.new("RGBA", (txt_w, txt_h), (0,0,0,0))
td      = ImageDraw.Draw(txt_img)

# Glow effect
for dx,dy in [(-3,0),(3,0),(0,-3),(0,3),(-2,-2),(2,2)]:
    td.text((txt_w//2-TW//2+dx, pad+dy), hook_video, font=font_hook, fill=(160,130,255,45))
# Hook text utama
td.text((txt_w//2-TW//2, pad), hook_video, font=font_hook, fill=(255,255,255,230))
# Channel name
td.text((txt_w//2-CW//2, pad+TH+14), CHANNEL_NAME, font=font_ch, fill=(180,160,220,170))

# Lissajous path — radius 30% dari sisa ruang, tidak keluar layar
RX = (W - txt_w) * 0.30
RY = (H - txt_h) * 0.28
CX = W/2 - txt_w/2
CY = H/2 - txt_h/2

text_clip = (ImageClip(np.array(txt_img))
             .set_duration(duration)
             .set_position(lambda t: (
                 CX + RX * np.sin(t * 0.18),
                 CY + RY * np.sin(t * 0.13)
             )))

# ── Composite & render ────────────────────────────────────────
print("🎬 Rendering video...")
final = CompositeVideoClip([bg_clip] + boxes_clips + [text_clip], size=(W, H))
final = final.set_audio(audio_clip)
final.write_videofile(
    VIDEO_OUTPUT, fps=FPS,
    codec="libx264", audio_codec="aac",
    preset="ultrafast", threads=4
)
print("✅ VIDEO SELESAI:", VIDEO_OUTPUT)
