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

# Lorenz system state
lx = 0.1
ly = 0.0
lz = 0.0
dt = 0.005
beta = 8.0 / 3.0

# Ring buffer for trail
MAX_TRAIL = 2500
trail_x = []
trail_y = []
trail_z = []
trail_head = 0
trail_count = 0

# Global rotation
rot_angle = 0.0
rot_dir = 1.0

# 3D tumble (pitch)
pitch_angle = 0.0

# Spring-damped audio envelope
env = 0.0
vel = 0.0

# Trigger rho spike
rho_spike = 0.0

# Veil surface for persist trails
veil = None

# Center and scale
CX = 640
CY = 360
BASE_SCALE = 10.0


def setup(screen, eyesy):
    global trail_x, trail_y, trail_z, trail_head, trail_count
    global veil, lx, ly, lz

    trail_x = [0.0] * MAX_TRAIL
    trail_y = [0.0] * MAX_TRAIL
    trail_z = [0.0] * MAX_TRAIL
    trail_head = 0
    trail_count = 0
    lx = 0.1
    ly = 0.0
    lz = 0.0

    veil = pygame.Surface((1280, 720))


def draw(screen, eyesy):
    global lx, ly, lz, trail_head, trail_count
    global rot_angle, rot_dir, env, vel, rho_spike, pitch_angle

    t = time.time()

    # -- Background --
    eyesy.color_picker_bg(eyesy.knob5)

    # -- Veil: gradual fade for persist trails --
    veil.fill(eyesy.bg_color)
    veil.set_alpha(20)
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

    # -- Trigger: rho spike --
    if eyesy.trig:
        rho_spike = 20.0
    if rho_spike > 0.0:
        rho_spike *= 0.85

    # -- Knob mappings --
    sigma = 10.0 + math.sin(t * 0.07) * 2.0 + env * 3.0
    # Knob1: rotation speed + zoom (low = slow/wide, high = fast/zoomed in)
    rot_speed_knob = 0.003 + eyesy.knob1 * 0.018
    zoom_knob = 0.6 + eyesy.knob1 * 2.0
    steps_per_frame = 120 + int(env * 80)
    # Knob2: line width (thin range only, 1-2px)
    thickness = 1 + int(eyesy.knob2)
    if thickness > 2:
        thickness = 2
    visible_length = int(500 + eyesy.knob3 * 2000)
    color_base = eyesy.knob4

    # -- Spring-damped rho: smooth audio response + slow drift --
    rho = 28.0 + math.sin(t * 0.05) * 5.0 + env * 20.0 + rho_spike

    # -- Beta drifts slowly for shape morphing --
    beta_dyn = (8.0 / 3.0) + math.sin(t * 0.04) * 0.5

    # -- Global rotation: steady swirl in one direction --
    rot_angle += (rot_speed_knob + env * 0.01) * rot_dir
    cos_r = math.cos(rot_angle)
    sin_r = math.sin(rot_angle)

    # -- 3D tumble: slow pitch reveals depth of butterfly lobes --
    pitch_angle = math.sin(t * 0.03) * 0.7 + math.sin(t * 0.017) * 0.3 + env * 0.2
    cos_p = math.cos(pitch_angle)
    sin_p = math.sin(pitch_angle)

    # -- Scale from knob1 zoom + audio (stronger breathing) --
    scale = BASE_SCALE * zoom_knob + env * 5.0

    # -- Line thickness from knob2 (set above) --

    # -- Integrate Lorenz system --
    for _ in range(steps_per_frame):
        dx_l = sigma * (ly - lx) * dt
        dy_l = (lx * (rho - lz) - ly) * dt
        dz_l = (lx * ly - beta_dyn * lz) * dt
        lx += dx_l
        ly += dy_l
        lz += dz_l

        # Store in ring buffer
        trail_x[trail_head] = lx
        trail_y[trail_head] = ly
        trail_z[trail_head] = lz
        trail_head = (trail_head + 1) % MAX_TRAIL
        if trail_count < MAX_TRAIL:
            trail_count += 1

    # -- Determine visible points --
    n = min(visible_length, trail_count)
    if n < 2:
        return

    # Read from ring buffer oldest to newest
    start_idx = (trail_head - n) % MAX_TRAIL

    # -- Fixed z range for color mapping (Lorenz z is always ~0-50) --
    z_min = 0.0
    z_range = 50.0

    # -- Center offset: slow steady circular orbit --
    cx_off = CX + math.sin(t * 0.05) * 10
    cy_off = CY + math.cos(t * 0.05) * 8

    # -- Build rotated point list and draw in segments --
    seg_size = 100
    idx = start_idx
    seg_points = []
    seg_z_sum = 0.0
    seg_z_count = 0

    for pt in range(n):
        tx = trail_x[idx]
        ty = trail_y[idx]
        tz = trail_z[idx] - 25.0

        # Apply global rotation to XY
        rx = tx * cos_r - ty * sin_r
        ry = tx * sin_r + ty * cos_r

        # Apply pitch rotation (tilts Y into Z, reveals depth)
        ry2 = ry * cos_p - tz * sin_p

        px = int(cx_off + rx * scale)
        py = int(cy_off - ry2 * scale)
        seg_points.append((px, py))
        seg_z_sum += tz
        seg_z_count += 1

        idx = (idx + 1) % MAX_TRAIL

        # Draw segment when full or at end
        if len(seg_points) >= seg_size or pt == n - 1:
            if len(seg_points) >= 2:
                # Color from z-depth + time cycling + audio
                z_norm = ((seg_z_sum / seg_z_count) - z_min) / z_range
                cv = (color_base * 0.8 + 0.16 + z_norm * 0.15 +
                      math.sin(t * 0.5) * 0.1 + env * 0.08) % 0.96
                if cv < 0.16:
                    cv = 0.16
                color = eyesy.color_picker(cv)
                pygame.draw.lines(screen, color, False, seg_points, thickness)

            # Keep last point for continuity
            seg_points = [seg_points[-1]]
            seg_z_sum = 0.0
            seg_z_count = 0

    # -- Head glow: bright dot at current tracing position --
    hx = lx
    hy = ly
    hz = lz - 25.0
    hrx = hx * cos_r - hy * sin_r
    hry = hx * sin_r + hy * cos_r
    hry2 = hry * cos_p - hz * sin_p
    hpx = int(cx_off + hrx * scale)
    hpy = int(cy_off - hry2 * scale)
    head_r = 3 + int(env * 4)
    head_color = eyesy.color_picker(color_base)
    if 0 <= hpx < 1280 and 0 <= hpy < 720:
        pygame.draw.circle(screen, head_color, (hpx, hpy), head_r)
