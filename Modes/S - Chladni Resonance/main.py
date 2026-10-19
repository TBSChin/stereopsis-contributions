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

# Scanning resolution for contour detection
# Pi CM3+ optimized: larger step = fewer points = faster
SCAN_STEP = 16
PLATE_W = 720
PLATE_H = 720

# Spring-damped audio envelope
env = 0.0
vel = 0.0

# Continuous mode drift
n_float = 3.0
m_float = 5.0

# Spring-damped intermediary for smooth rendering
smooth_n = 3.0
smooth_m = 5.0

# Trigger snap targets
snap_n = 0.0
snap_m = 0.0
snap_decay = 0

# Dramatic mode pairs for trigger snaps
SNAP_PAIRS = [
    (7, 3), (5, 8), (9, 4), (6, 11), (8, 5),
    (3, 7), (11, 6), (4, 9), (7, 12), (10, 3)
]
snap_idx = 0

# Veil surface for persist trails
veil = None

# Pre-computed cosine tables (recomputed each frame)
PI = math.pi


def setup(screen, eyesy):
    global veil
    veil = pygame.Surface((1280, 720))


def draw(screen, eyesy):
    global env, vel, n_float, m_float
    global snap_n, snap_m, snap_decay, snap_idx
    global smooth_n, smooth_m

    t = time.time()

    # -- Background --
    eyesy.color_picker_bg(eyesy.knob5)

    # -- Veil: gradual fade for persist trails --
    veil.fill(eyesy.bg_color)
    veil.set_alpha(15)
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

    # -- Trigger: snap to dramatic mode pair --
    if eyesy.trig:
        snap_idx = (snap_idx + 1) % len(SNAP_PAIRS)
        snap_n = float(SNAP_PAIRS[snap_idx][0])
        snap_m = float(SNAP_PAIRS[snap_idx][1])
        snap_decay = 120

    # -- Knob mappings --
    n_base = 1.0 + eyesy.knob1 * 10.0
    m_base = 1.0 + eyesy.knob2 * 10.0
    color_base = eyesy.knob4

    # -- Continuous mode drift: always morphing --
    drift_mult = 0.2 + eyesy.knob3 * 1.8
    n_float += (math.sin(t * 0.12) * 0.0008 + env * 0.002) * drift_mult
    m_float += (math.cos(t * 0.09) * 0.0008 + env * 0.0015) * drift_mult

    # Blend knob base with drift
    n_val = n_base + n_float * 0.3
    m_val = m_base + m_float * 0.3

    # Apply snap if active
    if snap_decay > 0:
        blend = (snap_decay / 120.0) * 0.6
        n_val = n_val * (1.0 - blend) + snap_n * blend
        m_val = m_val * (1.0 - blend) + snap_m * blend
        snap_decay -= 1

    # Spring-damped intermediary for smooth rendering
    smooth_n += (n_val - smooth_n) * 0.04
    smooth_m += (m_val - smooth_m) * 0.04

    # -- Global rotation (smooth constant, no wobble for tiled pattern) --
    rot = t * 0.08
    cos_rot = math.cos(rot)
    sin_rot = math.sin(rot)

    # -- Color cycling --
    cv_base = (color_base * 0.8 + 0.16 + math.sin(t * 0.5) * 0.1 + env * 0.1) % 0.96
    if cv_base < 0.16:
        cv_base = 0.16

    # Bright and dim colors for glow
    color_bright = eyesy.color_picker(cv_base)
    dim_cv = (cv_base + 0.05) % 0.96
    if dim_cv < 0.16:
        dim_cv = 0.16
    color_dim_base = eyesy.color_picker(dim_cv)

    # Audio brightness modulation
    bright_mult = 0.7 + env * 0.5
    color_dim = (
        max(0, min(255, int(color_dim_base[0] * bright_mult * 0.4))),
        max(0, min(255, int(color_dim_base[1] * bright_mult * 0.4))),
        max(0, min(255, int(color_dim_base[2] * bright_mult * 0.4)))
    )

    # -- Compute Chladni contour points by scanning for zero crossings --
    # f(x,y) = cos(n*pi*x/L)*cos(m*pi*y/L) - cos(m*pi*x/L)*cos(n*pi*y/L)
    # Points computed WITHOUT rotation, then tiled, then rotated as one unit
    cx_screen = 640
    cy_screen = 360
    half_plate = 360  # PLATE_W / 2

    # Pre-compute cos lookup per row for n and m
    n_pi_over_L = smooth_n * PI / PLATE_H
    m_pi_over_L = smooth_m * PI / PLATE_H

    # Base contour points (unrotated, relative to pattern center)
    base_points = []

    # Pre-compute cosine arrays
    x_vals = range(0, PLATE_W, SCAN_STEP)
    y_vals = range(0, PLATE_H, SCAN_STEP)
    nx = len(x_vals)
    ny = len(y_vals)

    cos_xn = [math.cos(x * n_pi_over_L) for x in x_vals]
    cos_xm = [math.cos(x * m_pi_over_L) for x in x_vals]
    cos_yn = [math.cos(y * n_pi_over_L) for y in y_vals]
    cos_ym = [math.cos(y * m_pi_over_L) for y in y_vals]

    # Row scan: detect horizontal zero crossings (no rotation yet)
    for j in range(ny):
        c_ny = cos_yn[j]
        c_my = cos_ym[j]
        py_raw = y_vals[j] - half_plate

        prev_f = None
        for i in range(nx):
            f = cos_xn[i] * c_my - cos_xm[i] * c_ny

            if prev_f is not None and f * prev_f < 0.0:
                px_raw = x_vals[i] - half_plate
                base_points.append((px_raw, py_raw))

            prev_f = f

    # Column scan: detect vertical zero crossings (no rotation yet)
    for i in range(nx):
        c_nx = cos_xn[i]
        c_mx = cos_xm[i]
        px_raw = x_vals[i] - half_plate

        prev_f = None
        for j in range(ny):
            f = c_nx * cos_ym[j] - c_mx * cos_yn[j]

            if prev_f is not None and f * prev_f < 0.0:
                py_raw = y_vals[j] - half_plate
                base_points.append((px_raw, py_raw))

            prev_f = f

    # -- Tile 3x3, then rotate entire composition around screen center --
    tile_offsets = [
        (0, 0),        # center
        (-720, 0),     # left
        (720, 0),      # right
        (0, -720),     # top
        (0, 720),      # bottom
        (-720, -720),  # top-left
        (720, -720),   # top-right
        (-720, 720),   # bottom-left
        (720, 720),    # bottom-right
    ]

    radius = 3 + int(env * 2)
    for tx, ty in tile_offsets:
        for bx, by in base_points:
            # Position relative to screen center (before rotation)
            px = tx + bx
            py = ty + by
            # Rotate around screen center
            rx = px * cos_rot - py * sin_rot
            ry = px * sin_rot + py * cos_rot
            # Final screen position
            sx = int(cx_screen + rx)
            sy = int(cy_screen + ry)
            if 0 <= sx < 1280 and 0 <= sy < 720:
                pygame.draw.circle(screen, color_bright, (sx, sy), radius)
