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
import random

# Screen dimensions
SCR_W = 1280
SCR_H = 720

# Global state
seeds_x = []
seeds_y = []
seeds_phase_x = []
seeds_phase_y = []
seeds_freq_x = []
seeds_freq_y = []
seeds_amp_x = []
seeds_amp_y = []
seeds_cx = []
seeds_cy = []
num_seeds = 0

# Perturbation from triggers (decaying offset)
perturb_x = []
perturb_y = []

# Spring-damped audio envelopes
env_l = 0.0
vel_l = 0.0
env_r = 0.0
vel_r = 0.0
env = 0.0
vel = 0.0

# Veil surface for persist trails
veil = None


def _init_seeds(count):
    global seeds_x, seeds_y, num_seeds
    global seeds_phase_x, seeds_phase_y, seeds_freq_x, seeds_freq_y
    global seeds_amp_x, seeds_amp_y, seeds_cx, seeds_cy
    global perturb_x, perturb_y
    num_seeds = count
    seeds_x = [0.0] * count
    seeds_y = [0.0] * count
    perturb_x = [0.0] * count
    perturb_y = [0.0] * count

    # Each seed gets unique orbit parameters
    seeds_phase_x = [random.random() * 6.283 for _ in range(count)]
    seeds_phase_y = [random.random() * 6.283 for _ in range(count)]
    # Unique frequencies so paths don't sync up
    seeds_freq_x = [0.08 + random.random() * 0.15 for _ in range(count)]
    seeds_freq_y = [0.06 + random.random() * 0.12 for _ in range(count)]
    # Amplitudes: large enough to sweep across most of the screen
    seeds_amp_x = [200 + random.random() * 350 for _ in range(count)]
    seeds_amp_y = [120 + random.random() * 220 for _ in range(count)]
    # Per-seed center offsets (spread across screen)
    seeds_cx = [300 + random.random() * 680 for _ in range(count)]
    seeds_cy = [180 + random.random() * 360 for _ in range(count)]


def setup(screen, eyesy):
    global veil
    veil = pygame.Surface((1280, 720))
    _init_seeds(25)


def draw(screen, eyesy):
    global seeds_x, seeds_y, num_seeds, perturb_x, perturb_y
    global env_l, vel_l, env_r, vel_r, env, vel
    t = time.time()

    # --- Audio: normalize int16 to float if needed ---
    audio_l = eyesy.audio_in
    audio_r = eyesy.audio_in_r
    peak_a = 0.0
    for i in range(0, 100, 10):
        v = audio_l[i]
        if v < 0:
            v = -v
        if v > peak_a:
            peak_a = v
        v = audio_r[i]
        if v < 0:
            v = -v
        if v > peak_a:
            peak_a = v
    if peak_a > 2.0:
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
    target_seeds = int(eyesy.knob1 * 25) + 15       # 15-40 seeds
    border_thresh = eyesy.knob2                       # 0-1 border visibility
    drift_speed = eyesy.knob3 * 2.9 + 0.1            # 0.1-3.0 drift multiplier
    knob4 = eyesy.knob4
    knob5 = eyesy.knob5

    # --- Recreate seeds if count changed significantly ---
    if abs(target_seeds - num_seeds) > 2:
        _init_seeds(target_seeds)

    # --- Trigger: scatter perturbation ---
    if eyesy.trig:
        for i in range(num_seeds):
            perturb_x[i] += (random.random() - 0.5) * 200.0
            perturb_y[i] += (random.random() - 0.5) * 150.0

    # --- Update seed positions: sinusoidal orbits + audio modulation ---
    speed = drift_speed
    for i in range(num_seeds):
        # Base Lissajous orbit — unique freq/phase per seed
        fx = seeds_freq_x[i] * speed
        fy = seeds_freq_y[i] * speed
        ax = seeds_amp_x[i] * (0.8 + env_l * 0.4)
        ay = seeds_amp_y[i] * (0.8 + env_r * 0.4)

        base_x = seeds_cx[i] + math.sin(t * fx + seeds_phase_x[i]) * ax
        base_y = seeds_cy[i] + math.cos(t * fy + seeds_phase_y[i]) * ay

        # Decay perturbation
        perturb_x[i] *= 0.95
        perturb_y[i] *= 0.95

        # Final position
        seeds_x[i] = base_x + perturb_x[i]
        seeds_y[i] = base_y + perturb_y[i]

        # Clamp to screen
        if seeds_x[i] < 20:
            seeds_x[i] = 20
        elif seeds_x[i] > SCR_W - 20:
            seeds_x[i] = SCR_W - 20
        if seeds_y[i] < 20:
            seeds_y[i] = 20
        elif seeds_y[i] > SCR_H - 20:
            seeds_y[i] = SCR_H - 20

    # --- Background ---
    eyesy.color_picker_bg(knob5)

    # --- Veil: gradual fade for persist trails ---
    veil.fill(eyesy.bg_color)
    veil.set_alpha(8)
    screen.blit(veil, (0, 0))

    # --- Compute nearest-neighbor distances for each seed ---
    nearest_dist = [999999.0] * num_seeds
    for i in range(num_seeds):
        for j in range(i + 1, num_seeds):
            dx = seeds_x[i] - seeds_x[j]
            dy = seeds_y[i] - seeds_y[j]
            d = math.sqrt(dx * dx + dy * dy)
            if d < nearest_dist[i]:
                nearest_dist[i] = d
            if d < nearest_dist[j]:
                nearest_dist[j] = d

    # --- Draw filled circles for each seed ---
    ns = num_seeds
    for i in range(ns):
        sx = int(seeds_x[i])
        sy = int(seeds_y[i])

        # Fill radius based on nearest neighbor distance
        fill_r = int(nearest_dist[i] * 0.45)
        if fill_r < 3:
            fill_r = 3
        if fill_r > 200:
            fill_r = 200

        # Color with per-seed offset and brightness pulsing
        phase_i = seeds_phase_x[i] if i < len(seeds_phase_x) else 0.0
        color_val = (knob4 + i / float(ns) + math.sin(t * 0.5) * 0.1 + env * 0.1) % 1.0
        col = eyesy.color_picker(color_val)
        brightness = 0.85 + 0.15 * math.sin(t * 2.0 + phase_i)
        col = (min(255, int(col[0] * brightness * 1.3)),
               min(255, int(col[1] * brightness * 1.3)),
               min(255, int(col[2] * brightness * 1.3)))

        pygame.draw.circle(screen, col, (sx, sy), fill_r)

    # --- Draw border lines between nearby seeds ---
    if border_thresh > 0.05:
        border_color_val = (knob4 + 0.5 + math.sin(t * 0.8) * 0.1) % 1.0
        border_col = eyesy.color_picker(border_color_val)
        line_width = 1 + int(env * 2)

        for i in range(ns):
            for j in range(i + 1, ns):
                dx = seeds_x[j] - seeds_x[i]
                dy = seeds_y[j] - seeds_y[i]
                d = math.sqrt(dx * dx + dy * dy)

                if d < 250 and d > 0.1:
                    # Midpoint
                    mx = seeds_x[i] + dx * 0.5
                    my = seeds_y[i] + dy * 0.5

                    # Perpendicular direction (normalized)
                    px = -dy / d
                    py = dx / d

                    # Line endpoints 60px apart along perpendicular
                    p1x = int(mx + px * 30)
                    p1y = int(my + py * 30)
                    p2x = int(mx - px * 30)
                    p2y = int(my - py * 30)

                    pygame.draw.line(screen, border_col, (p1x, p1y), (p2x, p2y), line_width)
