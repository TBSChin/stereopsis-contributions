# --- RANDUMBIZER LFO SWEEP O+-TR ---
# EYESY OS v3 Mode
#
# A Randomizer variant with tempo-synced sine LFO knob sweeps.
# Cycles through installed modes on musical bar divisions.
# Replaces external CC LFO control (Push 3 Standalone crash workaround).
#
# Controls:
#   Knob 1: LFO speed multiplier (0.25x slow - 4.0x fast)
#   Knob 2: Trigger injection rate (how often trig is toggled)
#   Knob 3: Mode switch interval (4 / 8 / 16 / 32 bars)
#   Knob 4: Trail/veil opacity
#   Knob 5: Unused
#
# Play/Stop:
#   Inferred from trigger activity (Ableton Link, MIDI, or audio).
#   Triggers arriving = PLAY. No triggers for ~5 seconds = STOP.
#
# Based on Randomizer O+-TR by Critter & Guitari.
# -------------------------------------------------------
#
# New code copyright (c) 2025 Martin Defatte
# SPDX-License-Identifier: BSD-2-Clause
#
# Randomizer base code copyright (c) Critter & Guitari
# SPDX-License-Identifier: BSD-3-Clause
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notices, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notices, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
# 3. Neither the name of Critter & Guitari nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# -------------------------------------------------------

import sys
import pygame
import random
import time
import math


# --- Configuration ---
PLAY_TIMEOUT = 5.0             # Seconds without trigger = STOP
BAR_DIVISIONS = [16, 32, 64, 128]  # Beat counts for 4/8/16/32 bars
TWO_PI = 2.0 * math.pi

# LFO rates in quarter-note beats (one per target mode knob)
# Non-power-of-2 relationships create polyrhythmic sweeps
# LCM(32,48,20,64,96) = 960 beats = 240 bars before pattern repeats
LFO_RATES = [32, 48, 20, 64, 96]

# Phase offsets (~60 degrees apart) so knobs don't peak simultaneously
LFO_OFFSETS = [0.0, 1.05, 2.09, 3.14, 4.19]

# Self-trigger fallback (audio onset detection when eyesy.trig isn't firing)
# Thresholds tuned for hardware sensitivity (lower than emulator needs)
SELF_TRIG_THRESHOLD = 0.20     # Normalized peak to fire (0.0-1.0)
SELF_TRIG_REARM = 0.08         # Re-arm below this
SELF_TRIG_COOLDOWN_FRAMES = 15 # Min frames between self-triggers (~500ms at 30fps)
SELF_TRIG_ACTIVATE_TIME = 3.0  # Seconds without engine trigger before fallback activates

# Guaranteed minimum trigger rate (ensures mode switching even if audio detection fails)
MIN_TRIGGER_INTERVAL = 4.0     # Fire at least every N seconds
MIN_BEAT_INTERVAL = 0.25       # Min seconds between counted beats (caps at 240 BPM)

# --- Globals ---
# Randomizer state
i = 0
old_i = -1
mode_trigger = False
count2 = 0

# LFO state
lfo_phases = [0.0, 0.0, 0.0, 0.0, 0.0]
beat_period = 0.5              # Default 120 BPM until triggers establish tempo
last_beat_time = 0.0
last_frame_time = 0.0

# Play/Stop state
is_playing = False
play_start_time = 0.0
last_trigger_time = 0.0
beat_counter = 0
last_beat_count_time = 0.0

# Veil
veil = None

# Self-trigger fallback state
self_trig_active = False           # Whether fallback is currently active
self_trig_armed = True             # Hysteresis: ready to fire
self_trig_cooldown = 0             # Frames remaining before next trigger allowed
last_engine_trig_time = 0.0        # time.time() of last eyesy.trig
last_any_trigger_time = 0.0        # time.time() of last trigger (any source)
last_draw_time = 0.0               # For detecting mode re-entry


def setup(screen, eyesy):
    global veil, i, old_i

    # Create veil surface
    veil = pygame.Surface((eyesy.xres, eyesy.yres))

    # Pick an initial random mode (avoiding self)
    if len(eyesy.mode_names) > 2:
        top_mode = eyesy.mode
        i = random.randrange(0, len(eyesy.mode_names))
        while eyesy.mode_names[i] == top_mode:
            i = random.randrange(0, len(eyesy.mode_names))
        old_i = i


def draw(screen, eyesy):
    global i, old_i, mode_trigger, count2
    global lfo_phases, beat_period, last_beat_time, last_frame_time
    global is_playing, play_start_time, last_trigger_time
    global beat_counter, last_beat_count_time, veil
    global self_trig_active, self_trig_armed, self_trig_cooldown, last_engine_trig_time
    global last_any_trigger_time, last_draw_time

    now = time.time()

    # --- Pick new random mode on re-entry (gap > 1 second) ---
    if last_draw_time > 0 and now - last_draw_time > 1.0 and len(eyesy.mode_names) > 2:
        top_mode = eyesy.mode
        i = random.randrange(0, len(eyesy.mode_names))
        while i == old_i or eyesy.mode_names[i] == top_mode:
            i = random.randrange(0, len(eyesy.mode_names))
        beat_counter = 0
    last_draw_time = now

    # Safety: need at least 3 modes
    if len(eyesy.mode_names) <= 2:
        screen.fill((0, 0, 0))
        return

    # --- Backup state ---
    xres_backup = eyesy.xres
    yres_backup = eyesy.yres
    knob1_backup = eyesy.knob1
    knob2_backup = eyesy.knob2
    knob3_backup = eyesy.knob3
    knob4_backup = eyesy.knob4
    knob5_backup = eyesy.knob5
    top_mode = eyesy.mode
    mode_root_backup = eyesy.mode_root

    # --- Self-trigger fallback ---
    trigger_fired = False

    if last_engine_trig_time == 0.0:
        last_engine_trig_time = now

    if eyesy.trig:
        trigger_fired = True
        last_engine_trig_time = now
        if self_trig_active:
            self_trig_active = False
            self_trig_armed = True
            self_trig_cooldown = 0
    else:
        if not self_trig_active and (now - last_engine_trig_time) > SELF_TRIG_ACTIVATE_TIME:
            self_trig_active = True
            self_trig_armed = True
            self_trig_cooldown = 0

        if self_trig_active:
            # Use both stereo channels, normalize int16 to float if needed
            peak = 0.0
            audio_l = eyesy.audio_in
            audio_r = eyesy.audio_in_r
            for si in range(0, 100, 4):
                av = abs(audio_l[si])
                if av > peak:
                    peak = av
                av = abs(audio_r[si])
                if av > peak:
                    peak = av
            if peak > 2.0:
                peak = peak / 32767.0

            if self_trig_cooldown > 0:
                self_trig_cooldown -= 1

            if self_trig_armed and self_trig_cooldown == 0 and peak > SELF_TRIG_THRESHOLD:
                trigger_fired = True
                self_trig_armed = False
                self_trig_cooldown = SELF_TRIG_COOLDOWN_FRAMES
            elif not self_trig_armed and peak < SELF_TRIG_REARM:
                self_trig_armed = True

    # --- Guaranteed minimum trigger rate (failsafe for hardware) ---
    if last_any_trigger_time == 0.0:
        last_any_trigger_time = now
    if not trigger_fired and (now - last_any_trigger_time) >= MIN_TRIGGER_INTERVAL:
        trigger_fired = True  # Force a trigger
    if trigger_fired:
        last_any_trigger_time = now

    # --- Beat period estimation (BPM tracking from trigger timing) ---
    if trigger_fired:
        if last_beat_time > 0:
            new_period = now - last_beat_time
            if 0.15 < new_period < 2.0:  # 30-400 BPM sanity range
                beat_period = beat_period * 0.7 + new_period * 0.3
        beat_period = max(beat_period, 0.25)  # Floor at 240 BPM
        last_beat_time = now

    # --- Play/Stop detection (before trigger injection) ---
    if trigger_fired:
        last_trigger_time = now
        if not is_playing:
            is_playing = True
            play_start_time = now
            beat_counter = 0
            last_beat_count_time = now
        # Rate-limit beat counting (audio triggers can fire many times/sec)
        if (now - last_beat_count_time) >= MIN_BEAT_INTERVAL:
            beat_counter += 1
            last_beat_count_time = now

    if is_playing and last_trigger_time > 0 and (now - last_trigger_time) > PLAY_TIMEOUT:
        is_playing = False

    # --- Mode switching (musical time, only during PLAY) ---
    if is_playing:
        # Determine bar division from real K3
        if eyesy.knob3 < 0.25:
            switch_target = BAR_DIVISIONS[0]   # 4 bars = 16 beats
        elif eyesy.knob3 < 0.50:
            switch_target = BAR_DIVISIONS[1]   # 8 bars = 32 beats
        elif eyesy.knob3 < 0.75:
            switch_target = BAR_DIVISIONS[2]   # 16 bars = 64 beats
        else:
            switch_target = BAR_DIVISIONS[3]   # 32 bars = 128 beats

        if beat_counter >= switch_target:
            beat_counter = 0
            mode_trigger = True

    # --- Pick new mode ---
    if mode_trigger and len(eyesy.mode_names) > 2:
        i = random.randrange(0, len(eyesy.mode_names))
        while i == old_i or eyesy.mode_names[i] == top_mode:
            i = random.randrange(0, len(eyesy.mode_names))
        mode_trigger = False

    # --- Load target mode ---
    mode_name = eyesy.mode_names[i]
    while mode_name == top_mode:
        i = random.randrange(0, len(eyesy.mode_names))
        mode_name = eyesy.mode_names[i]

    eyesy.mode_root = eyesy.MODES_PATH + mode_name + "/"

    # --- Trigger injection (K2) ---
    count2max = knob2_backup * 100
    count2 += 1
    if count2 > count2max:
        count2 = 0
        if eyesy.trig:
            eyesy.trig = False
        else:
            eyesy.trig = True

    # --- LFO sine sweep computation ---
    dt = now - last_frame_time
    if dt <= 0 or dt > 0.1:
        dt = 1.0 / 30.0
    last_frame_time = now

    # K1 controls LFO speed: 0.1x (glacial) to 2.0x (double time)
    speed_mult = 0.1 + knob1_backup * 1.9

    for k in range(5):
        freq = speed_mult / (LFO_RATES[k] * beat_period)
        lfo_phases[k] += TWO_PI * freq * dt

    # Inject sine LFO values (0.0 to 1.0) into target mode knobs
    eyesy.knob1 = 0.5 + 0.5 * math.sin(lfo_phases[0] + LFO_OFFSETS[0])
    eyesy.knob2 = 0.5 + 0.5 * math.sin(lfo_phases[1] + LFO_OFFSETS[1])
    eyesy.knob3 = 0.5 + 0.5 * math.sin(lfo_phases[2] + LFO_OFFSETS[2])
    eyesy.knob4 = 0.5 + 0.5 * math.sin(lfo_phases[3] + LFO_OFFSETS[3])
    eyesy.knob5 = 0.5 + 0.5 * math.sin(lfo_phases[4] + LFO_OFFSETS[4])

    # --- Call target mode ---
    try:
        mode = sys.modules[mode_name]
        mode.draw(screen, eyesy)
    except:
        pass

    # --- Restore state ---
    old_i = i
    eyesy.xres = xres_backup
    eyesy.yres = yres_backup
    eyesy.knob1 = knob1_backup
    eyesy.knob2 = knob2_backup
    eyesy.knob3 = knob3_backup
    eyesy.knob4 = knob4_backup
    eyesy.knob5 = knob5_backup
    eyesy.mode_root = mode_root_backup

    # --- Veil overlay (real K4) ---
    veil.fill((eyesy.bg_color[0], eyesy.bg_color[1], eyesy.bg_color[2]))
    veil.set_alpha(int(eyesy.knob4 * 200))
    screen.blit(veil, (0, 0))
