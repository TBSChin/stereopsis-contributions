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

# Constants
TWO_PI = 2.0 * math.pi
CX = 640
CY = 360
AMP_X = 800
AMP_Y = 450
NUM_POINTS = 360
NUM_CURVES = 4

# Musical frequency ratios
RATIOS = [
    (1, 1), (1, 2), (2, 3), (3, 4), (3, 5),
    (4, 5), (5, 6), (5, 7), (7, 8)
]

# Trig lookup
TABLE_SIZE = 1000
sin_table = []
cos_table = []

# Smooth ratio interpolation state
current_a = 1.0
current_b = 1.0
target_a = 1.0
target_b = 1.0

# Rotation state
rotation_angle = 0.0
rot_dir = 1.0

# Phase drift
extra_phase = 0.0
target_phase = 0.0

# Eased rotation target
target_rot_dir = 1.0

# Trigger ratio cycling
current_ratio_idx = 0
beat_count = 0

# Spring-damped audio envelope
env = 0.0
vel = 0.0

# Veil surface for persist trails
veil = None


def setup(screen, eyesy):
    global sin_table, cos_table, veil

    # Pre-compute trig tables
    sin_table = [0.0] * TABLE_SIZE
    cos_table = [0.0] * TABLE_SIZE
    for i in range(TABLE_SIZE):
        angle = i * TWO_PI / TABLE_SIZE
        sin_table[i] = math.sin(angle)
        cos_table[i] = math.cos(angle)

    veil = pygame.Surface((1280, 720))


def fast_sin(t):
    """Table lookup sin."""
    idx = int((t % TWO_PI) / TWO_PI * TABLE_SIZE) % TABLE_SIZE
    return sin_table[idx]


def fast_cos(t):
    """Table lookup cos."""
    idx = int((t % TWO_PI) / TWO_PI * TABLE_SIZE) % TABLE_SIZE
    return cos_table[idx]


def draw(screen, eyesy):
    global current_a, current_b, target_a, target_b
    global rotation_angle, rot_dir, extra_phase, target_phase, target_rot_dir
    global current_ratio_idx, env, vel, beat_count

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

    # -- Trigger: set targets on every other beat --
    if eyesy.trig:
        beat_count += 1
        if beat_count % 2 == 0:
            target_rot_dir = -rot_dir
            target_phase = extra_phase + math.pi / 3.0
            current_ratio_idx = (current_ratio_idx + 1) % len(RATIOS)

    # Ease rotation direction (smooth flip instead of instant)
    rot_dir += (target_rot_dir - rot_dir) * 0.05
    # Ease phase toward target
    extra_phase += (target_phase - extra_phase) * 0.06

    # -- Knob mappings --
    knob_ratio_idx = int(eyesy.knob1 * (len(RATIOS) - 1))
    ratio_idx = (knob_ratio_idx + current_ratio_idx) % len(RATIOS)
    target_a = float(RATIOS[ratio_idx][0])
    target_b = float(RATIOS[ratio_idx][1])

    base_delta = eyesy.knob2 * TWO_PI
    scale_factor = 0.8 + eyesy.knob3 * 0.8
    color_base = eyesy.knob4

    # -- Smooth ratio interpolation (takes ~80 frames to transition) --
    current_a += (target_a - current_a) * 0.012
    current_b += (target_b - current_b) * 0.012

    # -- Secondary harmonic drift overlaid on ratios --
    a_freq = current_a + math.sin(t * 0.08) * 0.08
    b_freq = current_b + math.cos(t * 0.06) * 0.08

    # -- Continuous phase drift (applied to target so easing still works) --
    target_phase += math.sin(t * 0.15) * 0.005 + env * 0.02

    # -- Audio-driven rotation speed (fixed slow drift) --
    rot_speed = 0.008 + env * 0.015
    rotation_angle += rot_speed * rot_dir + math.sin(t * 0.08) * 0.002
    cos_r = math.cos(rotation_angle)
    sin_r = math.sin(rotation_angle)

    # -- Amplitude breathing via spring envelope --
    amp_scale = 0.7 + env * 0.6
    ax = AMP_X * amp_scale * scale_factor
    ay = AMP_Y * amp_scale * scale_factor

    # -- Line thickness from audio --
    base_thickness = 1 + int(env * 3)
    if base_thickness > 4:
        base_thickness = 4

    # -- Center drifts with time --
    cx_off = CX + math.sin(t * 0.12) * 15.0
    cy_off = CY + math.cos(t * 0.09) * 10.0

    # -- Draw 5 curves with per-curve offsets --
    for curve in range(NUM_CURVES):
        curve_delta = base_delta + extra_phase + curve * 0.25

        # Color cycling: per-curve offset + time drift + audio
        cv = (color_base + curve * 0.15 + math.sin(t * 0.4 + curve) * 0.08 + env * 0.1) % 0.80
        cv = cv + 0.16
        if cv > 0.96:
            cv = cv - 0.80
        color = eyesy.color_picker(cv)

        # Per-curve amplitude variation
        curve_ax = ax * (0.85 + curve * 0.04)
        curve_ay = ay * (0.85 + curve * 0.04)

        # Build point list
        points = []
        for i in range(NUM_POINTS):
            param = i * TWO_PI / NUM_POINTS

            # Audio shimmer per point
            audio_idx = i % 100
            shimmer = audio[audio_idx] * 0.04

            # Parametric Lissajous with drifting frequencies
            raw_x = curve_ax * fast_sin(a_freq * param + curve_delta + shimmer)
            raw_y = curve_ay * fast_sin(b_freq * param + shimmer * 0.5)

            # Apply global rotation
            rx = raw_x * cos_r - raw_y * sin_r
            ry = raw_x * sin_r + raw_y * cos_r

            px = int(cx_off + rx)
            py = int(cy_off + ry)
            points.append((px, py))

        # Close curve
        points.append(points[0])

        # Draw with thickness
        if len(points) >= 2:
            pygame.draw.lines(screen, color, False, points, base_thickness)
