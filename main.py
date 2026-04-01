# ==========================================================
# ZERO TOUCH AI - GENERATIVE LOFI ENGINE (GITHUB VERSION)
# Auto Generates 1 Hour Video
# ==========================================================

import numpy as np
import soundfile as sf
import random
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import os

# ==========================
# GLOBAL SETTINGS
# ==========================

SR = 44100
#FINAL_DURATION = 3600
FINAL_DURATION = 300
WAV_OUTPUT = "zero_touch_ai_lofi_1hour.wav"
VIDEO_OUTPUT = "final_video.mp4"

# ==========================
# RANDOM SETTINGS
# ==========================

BPM = random.randint(68, 84)
BEAT = 60 / BPM
BAR = BEAT * 4

root_notes = [196, 220, 246.94, 261.63, 293.66]
root = random.choice(root_notes)

scale_type = random.choice(["minor", "dorian", "major"])

if scale_type == "minor":
    scale = [0,2,3,5,7,8,10]
elif scale_type == "dorian":
    scale = [0,2,3,5,7,9,10]
else:
    scale = [0,2,4,5,7,9,11]

def note_freq(root, degree):
    return root * (2 ** (scale[degree] / 12))

def create_chord(root, degrees, t):
    wave = np.zeros_like(t)
    for d in degrees:
        wave += np.sin(2*np.pi*note_freq(root, d)*t)
    return wave / len(degrees)

# ==========================
# BUILD BASE 8 MIN SECTION
# ==========================

#BASE_MINUTES = 8
BASE_MINUTES = 5
base_duration = BASE_MINUTES * 60
total_samples = int(SR * base_duration)

t = np.linspace(0, base_duration, total_samples, endpoint=False)
music = np.zeros_like(t)

bars = int(base_duration / BAR)

progression_bank = [
    [[0,2,4],[5,0,2],[3,5,0],[6,1,3]],
    [[0,3,5],[4,6,1],[2,4,6],[5,0,2]],
    [[0,4,6],[3,5,0],[1,3,5],[4,6,1]],
]

progression = random.choice(progression_bank)

for bar in range(bars):
    start = int(bar * BAR * SR)
    end = min(int((bar+1) * BAR * SR), total_samples)
    section_time = t[start:end]
    chord_degrees = progression[bar % len(progression)]

    pad = create_chord(root, chord_degrees, section_time) * 0.25
    bass_freq = note_freq(root, chord_degrees[0])
    bass = np.sin(2*np.pi*bass_freq*section_time) * 0.15

    music[start:end] += pad + bass

# ==========================
# MELODY
# ==========================

for beat_num in range(int(base_duration / BEAT)):
    if random.random() < 0.65:
        idx = int(beat_num * BEAT * SR)
        if idx >= total_samples:
            continue

        length = int(SR * BEAT * random.uniform(0.4,0.8))
        end_idx = min(idx + length, total_samples)
        note_len = end_idx - idx

        degree = random.randint(0,6)
        freq = note_freq(root, degree)

        tone = np.sin(2*np.pi*freq*t[:note_len]) * 0.12
        music[idx:end_idx] += tone

# ==========================
# DRUMS
# ==========================

kick_base = np.sin(2*np.pi*55*t) * np.exp(-t*12)
snare_base = np.random.randn(len(t)) * np.exp(-t*30)
hihat_base = np.random.randn(len(t)) * 0.015

for beat_num in range(int(base_duration / BEAT)):
    idx = int(beat_num * BEAT * SR)
    if idx >= total_samples:
        continue

    end_idx = min(idx+2000,total_samples)
    length = end_idx - idx

    if beat_num % 4 == 0:
        music[idx:end_idx] += kick_base[:length] * 0.8

    if beat_num % 4 == 2:
        music[idx:end_idx] += snare_base[:length] * 0.5

    hat_end = min(idx+800,total_samples)
    hat_len = hat_end - idx
    music[idx:hat_end] += hihat_base[:hat_len]

# ==========================
# MASTER
# ==========================

music = np.tanh(music * 1.7)
music = music / np.max(np.abs(music)) * 0.9

loops = int(np.ceil(FINAL_DURATION / base_duration))
full = np.tile(music, loops)
full = full[:SR * FINAL_DURATION]

stereo = np.vstack([full, np.roll(full, 400)]).T
sf.write(WAV_OUTPUT, stereo, SR)

# ==========================
# VIDEO CREATION
# ==========================

width, height = 1280, 720
fps = 30

audio = AudioFileClip(WAV_OUTPUT)
duration = audio.duration

background = ColorClip((width, height), color=(0, 0, 0), duration=duration)

img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 80)
except:
    font = ImageFont.load_default()

channel_name = "ZERO TOUCH LOFI"

bbox = draw.textbbox((0,0), channel_name, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]

draw.text(
    ((width - text_width) / 2, (height - text_height) / 2),
    channel_name,
    font=font,
    fill=(255,255,255,255)
)

text_clip = ImageClip(np.array(img)).set_duration(duration)

balls = []
for i in range(6):
    x_phase = random.uniform(0, 10)
    y_phase = random.uniform(0, 10)

    ball = (
        ColorClip((60,60), color=(255,255,255))
        .set_opacity(0.25)
        .set_duration(duration)
        .set_position(lambda t, xp=x_phase, yp=y_phase: (
            width/2 + np.sin(t + xp) * 350,
            height/2 + np.cos(t + yp) * 200
        ))
    )
    balls.append(ball)

final = CompositeVideoClip([background] + balls + [text_clip])
final = final.set_audio(audio)

final.write_videofile(
    VIDEO_OUTPUT,
    fps=fps,
    codec="libx264",
    audio_codec="aac",
    preset="ultrafast"
)

print("✅ VIDEO CREATED:", VIDEO_OUTPUT)
