# --- RANDUMBIZER VCR O+-TR ---
# EYESY OS v3 Mode
#
# A Randomizer variant with VCR on-screen display overlay.
# Cycles through installed modes on musical bar divisions,
# with PLAY/STOP state, set timer, and retro VCR HUD.
#
# Controls:
#   Knob 1: Knob drift speed (how fast randomized knob values evolve)
#   Knob 2: Trigger injection rate (how often trig is toggled)
#   Knob 3: Mode switch interval (4 / 8 / 16 / 32 bars)
#   Knob 4: Trail/veil opacity
#   Knob 5: Unused
#
# Play/Stop:
#   Inferred from trigger activity (Ableton Link, MIDI, or audio).
#   Triggers arriving = PLAY. No triggers for ~2 seconds = STOP.
#   Set timer counts up in real time during PLAY.
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

import os
import sys
import pygame
import random
import time
import glob


# --- KnobCountdown (from Randomizer O+-TR by Critter & Guitari) ---
# Smooth random walk interpolator for knob values.
# Drifts by +/-0.01 per frame, flips direction every 9-13 frames.

class KnobCountdown:
    def __init__(self, knob):
        self.knob = knob
        self.countdown_value = 0
        self.fake_val = 0
        self.fake_val_old = 1
        self.direction = 1
        self.dir_counter = 0
        self.dir_counter_max = random.choice([9, 10, 11, 12, 13])

    def update(self, eyesy):
        if self.fake_val_old != self.fake_val:
            self.dir_counter += 1
            if self.dir_counter >= self.dir_counter_max:
                self.direction = random.choice([-1, 1])
                self.dir_counter = 0
            self.fake_val_old = self.fake_val

        if self.direction == -1:
            self.countdown_value -= 0.01
            if self.countdown_value <= 0:
                self.countdown_value = self.fake_val

        if self.direction == 1:
            self.countdown_value += 0.01
            if self.countdown_value >= 1:
                self.countdown_value = self.fake_val

        return self.countdown_value


# --- Configuration ---
PLAY_TIMEOUT = 5.0             # Seconds without trigger = STOP
BAR_DIVISIONS = [16, 32, 64, 128]  # Beat counts for 4/8/16/32 bars
VCR_FONT_SIZE = 40
VCR_MARGIN = 50                # Pixels from screen edges
VCR_COLOR = (255, 255, 255)    # White text

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
count1 = 0
count2 = 0

# KnobCountdown instances
knob1_cd = None
knob2_cd = None
knob3_cd = None
knob4_cd = None
knob5_cd = None

# VCR state
is_playing = False
play_start_time = 0.0
last_trigger_time = 0.0
accumulated_time = 0.0
beat_counter = 0
last_beat_count_time = 0.0

# VCR layout (computed in setup)
char_h = 0
char_advance = 0
clock_w = 0
timer_w = 0

# VCR font and cached text surfaces
vcr_font = None
cached_play_surf = None
cached_play_shadow = None
cached_stop_surf = None
cached_stop_shadow = None
cached_slp_surf = None
cached_slp_shadow = None
cached_at_surf = None
cached_at_shadow = None
cached_timer_text = ""
cached_timer_surf = None
cached_timer_shadow = None

# Veil
veil = None

# Blink state (frame-counted, immune to target mode time corruption)
blink_frame = 0
blink_on = True

# Self-trigger fallback state
self_trig_active = False           # Whether fallback is currently active
self_trig_armed = True             # Hysteresis: ready to fire
self_trig_cooldown = 0             # Frames remaining before next trigger allowed
last_engine_trig_time = 0.0        # time.time() of last eyesy.trig
last_any_trigger_time = 0.0        # time.time() of last trigger (any source)
last_draw_time = 0.0               # For detecting mode re-entry


def setup(screen, eyesy):
    global vcr_font, veil, char_h, char_advance, clock_w, timer_w
    global knob1_cd, knob2_cd, knob3_cd, knob4_cd, knob5_cd
    global i, old_i
    global cached_play_surf, cached_play_shadow
    global cached_stop_surf, cached_stop_shadow
    global cached_slp_surf, cached_slp_shadow
    global cached_at_surf, cached_at_shadow

    # Load VCR font
    font_files = sorted(glob.glob(eyesy.mode_root + '/font/*.[ot]tf'))
    if font_files:
        try:
            vcr_font = pygame.font.Font(font_files[0], VCR_FONT_SIZE)
            print("VCR font: " + os.path.basename(font_files[0]))
        except Exception as e:
            print("VCR font load failed: " + str(e))
            vcr_font = pygame.font.Font(None, VCR_FONT_SIZE)
    else:
        print("No VCR font found, using default.")
        vcr_font = pygame.font.Font(None, VCR_FONT_SIZE)

    # Create veil surface
    veil = pygame.Surface((eyesy.xres, eyesy.yres))

    # Pre-compute VCR text dimensions for fixed positioning
    if vcr_font:
        char_h = vcr_font.size("0")[1]
        char_advance = vcr_font.size("00")[0] - vcr_font.size("0")[0]
        clock_w = vcr_font.size("--:--")[0]
        timer_w = vcr_font.size("00:00:00")[0]

        # Pre-render static text surfaces (avoids font.render() every frame)
        shadow = (0, 0, 0)
        cached_play_surf = vcr_font.render("PLAY", True, VCR_COLOR)
        cached_play_shadow = vcr_font.render("PLAY", True, shadow)
        cached_stop_surf = vcr_font.render("STOP", True, VCR_COLOR)
        cached_stop_shadow = vcr_font.render("STOP", True, shadow)
        cached_slp_surf = vcr_font.render("SLP", True, VCR_COLOR)
        cached_slp_shadow = vcr_font.render("SLP", True, shadow)
        cached_at_surf = vcr_font.render("AT", True, VCR_COLOR)
        cached_at_shadow = vcr_font.render("AT", True, shadow)

    # Initialize KnobCountdown instances
    knob1_cd = KnobCountdown(eyesy.knob1)
    knob2_cd = KnobCountdown(eyesy.knob2)
    knob3_cd = KnobCountdown(eyesy.knob3)
    knob4_cd = KnobCountdown(eyesy.knob4)
    knob5_cd = KnobCountdown(eyesy.knob5)

    # Pick an initial random mode (avoiding self)
    if len(eyesy.mode_names) > 2:
        top_mode = eyesy.mode
        i = random.randrange(0, len(eyesy.mode_names))
        while eyesy.mode_names[i] == top_mode:
            i = random.randrange(0, len(eyesy.mode_names))
        old_i = i


def draw(screen, eyesy):
    global i, old_i, mode_trigger, count1, count2
    global knob1_cd, knob2_cd, knob3_cd, knob4_cd, knob5_cd
    global is_playing, play_start_time, last_trigger_time, accumulated_time
    global cached_timer_text, cached_timer_surf, cached_timer_shadow
    global beat_counter, last_beat_count_time, veil, blink_frame, blink_on
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

    # --- Frame-counted blink (immune to target mode corrupting time) ---
    # 15 frames = ~0.5 sec at 30 FPS (typical VCR blink rate)
    blink_frame += 1
    if blink_frame >= 15:
        blink_frame = 0
        blink_on = not blink_on

    # Safety: need at least 3 modes
    if len(eyesy.mode_names) <= 2:
        screen.fill((0, 0, 0))
        if vcr_font:
            screen.blit(vcr_font.render("NEED 3+ MODES", True, VCR_COLOR),
                        (VCR_MARGIN, VCR_MARGIN))
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

    # --- Play/Stop detection (before trigger injection) ---
    if trigger_fired:
        last_trigger_time = now
        if not is_playing:
            # Transition to PLAY (continue accumulating, don't reset)
            is_playing = True
            play_start_time = now
            beat_counter = 0
            last_beat_count_time = now
        # Rate-limit beat counting (audio triggers can fire many times/sec)
        if (now - last_beat_count_time) >= MIN_BEAT_INTERVAL:
            beat_counter += 1
            last_beat_count_time = now

    if is_playing and last_trigger_time > 0 and (now - last_trigger_time) > PLAY_TIMEOUT:
        # Transition to STOP (bank accumulated time)
        accumulated_time += now - play_start_time
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

    # --- Knob randomization (K1) ---
    count1max = knob1_backup * 100
    count1 += 1
    if count1 > count1max:
        knob1_cd.fake_val = random.uniform(0.0, 1.0)
        knob2_cd.fake_val = random.uniform(0.0, 1.0)
        knob3_cd.fake_val = random.uniform(0.0, 1.0)
        knob4_cd.fake_val = random.uniform(0.0, 1.0)
        knob5_cd.fake_val = random.uniform(0.0, 1.0)
        count1 = 0

    # Inject fake knob values
    eyesy.knob1 = knob1_cd.update(eyesy)
    eyesy.knob2 = knob2_cd.update(eyesy)
    eyesy.knob3 = knob3_cd.update(eyesy)
    eyesy.knob4 = knob4_cd.update(eyesy)
    eyesy.knob5 = knob5_cd.update(eyesy)

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

    # --- VCR overlay (rendered directly on screen with cached text surfaces) ---
    if vcr_font:
        xr = eyesy.xres
        yr = eyesy.yres
        m = VCR_MARGIN
        sx, sy = 2, 2
        bg = (0, 0, 0)
        pad = 6

        # Top-left: PLAY or STOP (cached surfaces)
        if is_playing:
            status_surf = cached_play_surf
            status_shadow = cached_play_shadow
        else:
            status_surf = cached_stop_surf
            status_shadow = cached_stop_shadow
        status_w = status_surf.get_width()
        pygame.draw.rect(screen, bg, (m - pad, m - pad,
                         status_w + sx + pad * 2, char_h + sy + pad * 2))
        screen.blit(status_shadow, (m + sx, m + sy))
        screen.blit(status_surf, (m, m))

        # Top-right: --:-- (drawn as manual shapes for precise VCR look)
        cw = char_advance
        ch = char_h
        total_cw = 5 * cw
        clk_x = xr - total_cw - m
        clk_y = m

        dw = int(cw * 0.6)
        dh = 4
        d_xpad = (cw - dw) // 2

        dot = 5
        dot_xpad = (cw - dot) // 2
        dot_y1 = int(ch * 0.20)
        dot_y2 = int(ch * 0.60)

        d_ypad = (dot_y1 + dot_y2 + dot) // 2 - dh // 2

        # Bg box (always visible)
        pygame.draw.rect(screen, bg, (clk_x - pad, clk_y - pad,
                         total_cw + sx + pad * 2, ch + sy + pad * 2))

        # Colon dots (cell 2, always visible)
        cx = clk_x + 2 * cw
        pygame.draw.rect(screen, (0, 0, 0),
                         (cx + dot_xpad + sx, clk_y + dot_y1 + sy, dot, dot))
        pygame.draw.rect(screen, (0, 0, 0),
                         (cx + dot_xpad + sx, clk_y + dot_y2 + sy, dot, dot))
        pygame.draw.rect(screen, VCR_COLOR,
                         (cx + dot_xpad, clk_y + dot_y1, dot, dot))
        pygame.draw.rect(screen, VCR_COLOR,
                         (cx + dot_xpad, clk_y + dot_y2, dot, dot))

        # Dashes (cells 0, 1, 3, 4 - blink on/off)
        if blink_on:
            for ci in [0, 1, 3, 4]:
                dx = clk_x + ci * cw + d_xpad
                dy = clk_y + d_ypad
                pygame.draw.rect(screen, (0, 0, 0),
                                 (dx + sx, dy + sy, dw, dh))
                pygame.draw.rect(screen, VCR_COLOR,
                                 (dx, dy, dw, dh))

        # Bottom-left: SLP (cached surfaces)
        by = yr - char_h - m
        slp_w = cached_slp_surf.get_width()
        pygame.draw.rect(screen, bg, (m - pad, by - pad,
                         slp_w + sx + pad * 2, char_h + sy + pad * 2))
        screen.blit(cached_slp_shadow, (m + sx, by + sy))
        screen.blit(cached_slp_surf, (m, by))

        # AT indicator (self-trigger fallback active, cached surfaces)
        if self_trig_active:
            at_x = m + slp_w + pad * 3
            at_w = cached_at_surf.get_width()
            pygame.draw.rect(screen, bg, (at_x - pad, by - pad,
                             at_w + sx + pad * 2, char_h + sy + pad * 2))
            screen.blit(cached_at_shadow, (at_x + sx, by + sy))
            screen.blit(cached_at_surf, (at_x, by))

        # Bottom-right: HH:MM:SS (re-render only when seconds change)
        if is_playing:
            elapsed = accumulated_time + (now - play_start_time)
        else:
            elapsed = accumulated_time
        h = int(elapsed // 3600)
        mn = int((elapsed % 3600) // 60)
        s = int(elapsed % 60)
        timer_text = "%02d:%02d:%02d" % (h, mn, s)
        if timer_text != cached_timer_text:
            cached_timer_text = timer_text
            cached_timer_surf = vcr_font.render(timer_text, True, VCR_COLOR)
            cached_timer_shadow = vcr_font.render(timer_text, True, (0, 0, 0))
        timer_x = xr - timer_w - m
        timer_y = yr - char_h - m
        pygame.draw.rect(screen, bg, (timer_x - pad, timer_y - pad,
                         timer_w + sx + pad * 2, char_h + sy + pad * 2))
        screen.blit(cached_timer_shadow, (timer_x + sx, timer_y + sy))
        screen.blit(cached_timer_surf, (timer_x, timer_y))
