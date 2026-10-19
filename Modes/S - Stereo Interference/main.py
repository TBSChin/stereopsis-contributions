# BSD 2-Clause License
#
# Copyright (c) 2026, Martin Defatte
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Author: Martin Defatte
# Website: https://guerrilladigital.cc
# Pysey Video Synthesizer: https://pysey-synth.com

import pygame
import math
import time

# Spring-damped audio envelopes
env_l = 0.0
vel_l = 0.0
env_r = 0.0
vel_r = 0.0
env = 0.0
vel = 0.0

# Rotation direction (flipped by trigger)
rot_dir_l = 1.0
rot_dir_r = -1.0

# Veil surface for persist trails
veil = None


def setup(screen, eyesy):
    global veil
    veil = pygame.Surface((1280, 720))


def draw(screen, eyesy):
    global env_l, vel_l, env_r, vel_r, env, vel
    global rot_dir_l, rot_dir_r
    t = time.time()

    # --- Audio: normalize int16 to float if needed ---
    audio_l = eyesy.audio_in
    audio_r = eyesy.audio_in_r
    peak = 0.0
    for i in range(0, 100, 10):
        v = audio_l[i]
        if v < 0:
            v = -v
        if v > peak:
            peak = v
        v = audio_r[i]
        if v < 0:
            v = -v
        if v > peak:
            peak = v
    if peak > 2.0:
        norm = 1.0 / 32767.0
        audio_l = [s * norm for s in audio_l]
        audio_r = [s * norm for s in audio_r]

    # --- Audio: spring-damped envelopes ---
    left_rms = sum(abs(audio_l[i]) for i in range(0, 100, 4)) / 25.0
    right_rms = sum(abs(audio_r[i]) for i in range(0, 100, 4)) / 25.0
    combined = (left_rms + right_rms) * 0.5

    force_l = left_rms - env_l
    vel_l += force_l * 0.4
    vel_l *= 0.85
    env_l += vel_l
    env_l = max(0.0, min(1.0, env_l))

    force_r = right_rms - env_r
    vel_r += force_r * 0.4
    vel_r *= 0.85
    env_r += vel_r
    env_r = max(0.0, min(1.0, env_r))

    force_c = combined - env
    vel += force_c * 0.4
    vel *= 0.85
    env += vel
    env = max(0.0, min(1.0, env))

    # --- Knob mappings ---
    ring_count = int(eyesy.knob1 * 30) + 30        # 30-60 rings per set
    veil_alpha = int(eyesy.knob2 * 40) + 10          # 10-50 veil alpha
    sensitivity = eyesy.knob3 * 4.0 + 0.5           # 0.5-4.5
    knob4 = eyesy.knob4
    knob5 = eyesy.knob5

    # --- Trigger: flip rotation direction ---
    if eyesy.trig:
        rot_dir_l *= -1.0
        rot_dir_r *= -1.0

    # --- Background color ---
    bg = eyesy.color_picker_bg(knob5)

    # --- Veil: gradual fade for persist trails ---
    veil.fill(bg)
    veil.set_alpha(veil_alpha)
    screen.blit(veil, (0, 0))

    # --- Ring centers driven by stereo envelopes ---
    left_cx = 640 + int(env_l * sensitivity * 200)
    left_cy = 360 + int(math.sin(t * 0.3) * 30)
    right_cx = 640 - int(env_r * sensitivity * 200)
    right_cy = 360 + int(math.cos(t * 0.35) * 30)

    # --- Ring spacing ---
    base_spacing = max(6, int(1280.0 / ring_count))

    # --- Audio wave amplitude for ring waviness ---
    wave_amp = 10.0 + env * 40.0

    # --- Per-sample ripple data (10 samples for per-ring offsets) ---
    sample_offsets = []
    for s in range(10):
        idx = s * 10
        sample_offsets.append(audio_l[idx] * 15.0)

    sample_offsets_r = []
    for s in range(10):
        idx = s * 10
        sample_offsets_r.append(audio_r[idx] * 15.0)

    # --- Line width ---
    lw = 2 + int(env * 2)

    # --- Rotation speeds ---
    rot_speed_l = 0.5 * rot_dir_l
    rot_speed_r = 0.5 * rot_dir_r

    # --- Pre-compute segment trig arrays (shared by both ring sets) ---
    seg_count = 64
    angle_step = 2.0 * math.pi / seg_count
    n_seg = seg_count + 1

    # Rotated segment positions for left and right
    rot_angle_l = t * 0.1 * rot_dir_l
    rot_angle_r = t * 0.1 * rot_dir_r
    cos_rot_l = math.cos(rot_angle_l)
    sin_rot_l = math.sin(rot_angle_l)
    cos_rot_r = math.cos(rot_angle_r)
    sin_rot_r = math.sin(rot_angle_r)

    # Base segment cos/sin (no rotation offset)
    cos_seg = [math.cos(s * angle_step) for s in range(n_seg)]
    sin_seg = [math.sin(s * angle_step) for s in range(n_seg)]

    # Rotated segment positions: cos(angle + rot) = cos(a)*cos(r) - sin(a)*sin(r)
    cos_seg_l = [cos_seg[s] * cos_rot_l - sin_seg[s] * sin_rot_l for s in range(n_seg)]
    sin_seg_l = [sin_seg[s] * cos_rot_l + cos_seg[s] * sin_rot_l for s in range(n_seg)]
    cos_seg_r = [cos_seg[s] * cos_rot_r - sin_seg[s] * sin_rot_r for s in range(n_seg)]
    sin_seg_r = [sin_seg[s] * cos_rot_r + cos_seg[s] * sin_rot_r for s in range(n_seg)]

    # Wave modulation uses angle*2.0: pre-compute double-angle sin/cos
    cos_2seg = [math.cos(s * angle_step * 2.0) for s in range(n_seg)]
    sin_2seg = [math.sin(s * angle_step * 2.0) for s in range(n_seg)]

    sin_t_color = math.sin(t * 0.4) * 0.05

    # --- Draw left ring set ---
    for i in range(1, ring_count + 1):
        base_radius = i * base_spacing
        ripple = sample_offsets[i % 10] * (1.0 + env_l)
        color_val = (knob4 + i * 0.01 + sin_t_color + env_l * 0.1) % 1.0
        col = eyesy.color_picker(color_val)

        # Per-ring wave phase: sin(phase + angle*2) via addition formula
        phase = i * 0.3 + t * rot_speed_l
        sin_phase = math.sin(phase)
        cos_phase = math.cos(phase)

        points = []
        for s in range(n_seg):
            r = base_radius + (sin_phase * cos_2seg[s] + cos_phase * sin_2seg[s]) * wave_amp + ripple
            if r < 1:
                r = 1
            px = int(left_cx + cos_seg_l[s] * r)
            py = int(left_cy + sin_seg_l[s] * r)
            points.append((px, py))

        if len(points) > 2:
            pygame.draw.lines(screen, col, False, points, lw)

    # --- Draw right ring set (complementary colors, opposite rotation) ---
    for i in range(1, ring_count + 1):
        base_radius = i * base_spacing
        ripple = sample_offsets_r[i % 10] * (1.0 + env_r)
        color_val = ((knob4 + 0.5) + i * 0.01 + sin_t_color + env_r * 0.1) % 1.0
        col = eyesy.color_picker(color_val)

        phase = i * 0.3 + t * rot_speed_r
        sin_phase = math.sin(phase)
        cos_phase = math.cos(phase)

        points = []
        for s in range(n_seg):
            r = base_radius + (sin_phase * cos_2seg[s] + cos_phase * sin_2seg[s]) * wave_amp + ripple
            if r < 1:
                r = 1
            px = int(right_cx + cos_seg_r[s] * r)
            py = int(right_cy + sin_seg_r[s] * r)
            points.append((px, py))

        if len(points) > 2:
            pygame.draw.lines(screen, col, False, points, lw)
