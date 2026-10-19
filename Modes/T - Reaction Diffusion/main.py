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
import random
import time

# Grid dimensions (small for performance - each cell renders as a circle)
W = 64
H = 36

# Diffusion rates
dA = 1.0
dB = 0.5

# Spring-damped audio envelope
env = 0.0
vel = 0.0

# Frame counter for periodic seeding
frame_count = 0

# Beat counter for 8-bar reseed
beat_count = 0

# Color offset - shifts on each reset for contrast between bursts
color_offset = 0.0

MIN_RESET_INTERVAL = 2.0  # Guaranteed reset at least every N seconds

last_reset_time = 0.0
last_draw_time = 0.0

# Echo surfaces - snapshots of previous reactions that fade over time
NUM_ECHOES = 2
echo_surfaces = None
echo_alpha = None
echo_idx = 0
reaction_surf = None

# Simulation grids
grid_a = None
grid_b = None
grid_a2 = None
grid_b2 = None

# Veil surface for persist trails
veil = None

# Screen cell dimensions - scaled so interior cells (1..W-2) span full screen
CELL_W = 1280.0 / (W - 2)
CELL_H = 720.0 / (H - 2)

# Center of screen
SCX = 640.0
SCY = 360.0


def setup(screen, eyesy):
    global grid_a, grid_b, grid_a2, grid_b2
    global veil, reaction_surf, echo_surfaces, echo_alpha

    # Initialize grids
    grid_a = [[1.0] * W for _ in range(H)]
    grid_b = [[0.0] * W for _ in range(H)]
    grid_a2 = [[1.0] * W for _ in range(H)]
    grid_b2 = [[0.0] * W for _ in range(H)]

    # Seed initial random spots of chemical B
    for _ in range(30):
        sx = random.randint(10, W - 10)
        sy = random.randint(10, H - 10)
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                ny = sy + dy
                nx = sx + dx
                if 0 <= ny < H and 0 <= nx < W:
                    grid_b[ny][nx] = 1.0

    # Reaction surface (live reaction draws here, colorkey makes black transparent)
    reaction_surf = pygame.Surface((1280, 720))
    reaction_surf.set_colorkey((0, 0, 0))

    # Echo surfaces - capture reaction snapshots before each reset
    echo_surfaces = []
    for _ in range(NUM_ECHOES):
        s = pygame.Surface((1280, 720))
        s.set_colorkey((0, 0, 0))
        s.fill((0, 0, 0))
        echo_surfaces.append(s)
    echo_alpha = [0.0] * NUM_ECHOES

    # Veil surface for persist trails
    veil = pygame.Surface((1280, 720))


def draw(screen, eyesy):
    global grid_a, grid_b, grid_a2, grid_b2
    global env, vel, frame_count, beat_count, color_offset, echo_idx
    global last_reset_time, last_draw_time

    now = time.time()
    frame_count += 1

    # --- Reseed on mode re-entry (gap > 1 second) ---
    if last_draw_time > 0 and now - last_draw_time > 1.0:
        last_reset_time = 0.0  # Force immediate reset
    last_draw_time = now

    t = now

    # -- Background --
    eyesy.color_picker_bg(eyesy.knob5)
    # -- Veil: gradual fade for persist trails --
    veil.fill(eyesy.bg_color)
    veil.set_alpha(10)
    screen.blit(veil, (0, 0))

    # -- Audio (normalize int16 to float if needed) --
    rms = 0.0
    audio = eyesy.audio_in
    peak_a = 0.0
    for i in range(0, 100, 10):
        v = audio[i]
        if v < 0:
            v = -v
        if v > peak_a:
            peak_a = v
    if peak_a > 2.0:
        norm = 1.0 / 32767.0
        audio = [s * norm for s in audio]
    for i in range(0, 100, 4):
        s = audio[i]
        rms += s * s
    rms = math.sqrt(rms / 25.0)

    # -- Spring-damped envelope --
    force = rms - env
    vel += force * 0.4
    vel *= 0.85
    env += vel
    if env < 0.0:
        env = 0.0
    elif env > 1.0:
        env = 1.0

    # -- Knob mappings --
    f_base = 0.01 + eyesy.knob1 * 0.05
    k_base = 0.04 + eyesy.knob2 * 0.03
    steps = int(1 + eyesy.knob3 * 2)
    color_base = eyesy.knob4

    # -- Cyclic parameter sweep: k oscillates so patterns grow, dissolve, reform --
    k = k_base + math.sin(t * 0.15) * 0.01 + env * 0.01

    # -- Audio-driven feed rate --
    f = f_base + env * 0.02
    if f > 0.08:
        f = 0.08

    # -- Full grid reset + fresh seed --
    do_reset = False

    if eyesy.trig:
        beat_count += 1
        # Every 4 beats (1 bar): full reset
        if beat_count % 4 == 0:
            do_reset = True

    # Guaranteed minimum reset interval (failsafe)
    if last_reset_time == 0.0:
        last_reset_time = now
    if not do_reset and (now - last_reset_time) >= MIN_RESET_INTERVAL:
        do_reset = True

    if do_reset:
        last_reset_time = now

        # Capture current reaction as echo before wiping (reaction_surf has last frame's content)
        echo_surfaces[echo_idx].fill((0, 0, 0))
        echo_surfaces[echo_idx].blit(reaction_surf, (0, 0))
        echo_alpha[echo_idx] = 220.0
        echo_idx = (echo_idx + 1) % NUM_ECHOES

        # Shift color so each burst contrasts with the previous one
        color_offset += random.uniform(0.25, 0.45)

        # Wipe grids completely clean
        for y in range(H):
            for x in range(W):
                grid_a[y][x] = 1.0
                grid_b[y][x] = 0.0
                grid_a2[y][x] = 1.0
                grid_b2[y][x] = 0.0
        # Drop fresh seeds - dramatic new reaction unfolds from scratch
        num_spots = random.randint(15, 25)
        for _ in range(num_spots):
            sx = random.randint(5, W - 5)
            sy = random.randint(5, H - 5)
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    ny = sy + dy
                    nx = sx + dx
                    if 0 <= ny < H and 0 <= nx < W:
                        grid_b[ny][nx] = 1.0

    # -- Continuous seeding: add small spots to keep reaction alive --
    if frame_count % 10 == 0:  # Every 10 frames
        sx = random.randint(5, W - 5)
        sy = random.randint(5, H - 5)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                ny = sy + dy
                nx = sx + dx
                if 0 <= ny < H and 0 <= nx < W:
                    grid_b[ny][nx] = 1.0

    # -- Run simulation steps --
    for _ in range(steps):
        for y in range(1, H - 1):
            row_a = grid_a[y]
            row_b = grid_b[y]
            row_a_up = grid_a[y - 1]
            row_a_dn = grid_a[y + 1]
            row_b_up = grid_b[y - 1]
            row_b_dn = grid_b[y + 1]
            out_a = grid_a2[y]
            out_b = grid_b2[y]

            for x in range(1, W - 1):
                a = row_a[x]
                b = row_b[x]

                # Laplacian
                lap_a = row_a_up[x] + row_a_dn[x] + row_a[x - 1] + row_a[x + 1] - 4.0 * a
                lap_b = row_b_up[x] + row_b_dn[x] + row_b[x - 1] + row_b[x + 1] - 4.0 * b

                # Gray-Scott equations
                abb = a * b * b
                out_a[x] = a + dA * lap_a - abb + f * (1.0 - a)
                out_b[x] = b + dB * lap_b + abb - (k + f) * b

        # Swap buffers
        grid_a, grid_a2 = grid_a2, grid_a
        grid_b, grid_b2 = grid_b2, grid_b

    # -- Rotation angle for slight drift --
    rot_rad = math.sin(t * 0.2) * 0.035
    cos_r = math.cos(rot_rad)
    sin_r = math.sin(rot_rad)

    # -- Brightness multiplier from audio --
    bright_mult = 0.7 + env * 0.5

    # -- Time-based color shift --
    t_color = math.sin(t * 0.3) * 0.08

    # -- Render grid cells onto reaction surface --
    reaction_surf.fill((0, 0, 0))
    for y in range(H):
        row_b = grid_b[y]
        for x in range(W):
            bval = row_b[x]
            if bval < 0.0:
                bval = 0.0
            elif bval > 1.0:
                bval = 1.0

            if bval > 0.08:
                # Screen position - offset so interior cells fill screen edge to edge
                raw_x = (x - 1) * CELL_W + CELL_W * 0.5 - SCX
                raw_y = (y - 1) * CELL_H + CELL_H * 0.5 - SCY

                # Apply rotation around center
                sx = int(SCX + raw_x * cos_r - raw_y * sin_r)
                sy = int(SCY + raw_x * sin_r + raw_y * cos_r)

                if 0 <= sx < 1280 and 0 <= sy < 720:
                    # Circle radius based on B concentration
                    radius = 2 + int(bval * 4)

                    # Color cycling: knob base + B concentration + time drift
                    cv = (color_base + color_offset + bval * 0.3 + t_color) % 1.0
                    r, g, bc = eyesy.color_picker(cv)

                    # Apply brightness from audio + concentration
                    bm = bval * bright_mult
                    r = int(r * bm)
                    g = int(g * bm)
                    bc = int(bc * bm)
                    if r > 255:
                        r = 255
                    if g > 255:
                        g = 255
                    if bc > 255:
                        bc = 255

                    pygame.draw.circle(reaction_surf, (r, g, bc), (sx, sy), radius)

    # -- Draw fading echoes of previous reactions --
    for i in range(NUM_ECHOES):
        if echo_alpha[i] > 3.0:
            echo_alpha[i] -= 0.7
            echo_surfaces[i].set_alpha(int(echo_alpha[i]))
            screen.blit(echo_surfaces[i], (0, 0))

    # -- Draw live reaction on top --
    screen.blit(reaction_surf, (0, 0))
