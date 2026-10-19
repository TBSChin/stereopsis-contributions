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


def setup(screen, eyesy):
    """Called once when mode is loaded."""
    pass


def draw(screen, eyesy):
    """Called every frame."""
    # Get parameters from knobs
    height_scale = 100 + eyesy.knob1 * 300  # 100-400 pixels
    thickness = max(1, int(eyesy.knob2 * 5))  # 1-5 pixels
    hue = eyesy.knob3
    y_offset = int((eyesy.knob4 - 0.5) * 400)  # -200 to +200

    # Background color from knob 5 (standard convention)
    eyesy.color_picker_bg(eyesy.knob5)

    # Get screen dimensions
    width = screen.get_width()
    height = screen.get_height()
    center_y = height // 2 + y_offset

    # Get color from color picker
    color = eyesy.color_picker(hue)

    # Get audio samples (normalize int16 to float if needed)
    audio = eyesy.audio_in
    peak = 0.0
    for i in range(0, min(100, len(audio)), 10):
        v = audio[i]
        if v < 0:
            v = -v
        if v > peak:
            peak = v
    if peak > 2.0:
        norm = 1.0 / 32767.0
        audio = [s * norm for s in audio]

    # Draw waveform
    points = []
    num_samples = len(audio)
    for i in range(num_samples):
        x = int(i * width / num_samples)
        y = int(center_y - audio[i] * height_scale)
        points.append((x, y))

    # Draw as connected lines
    if len(points) >= 2:
        pygame.draw.lines(screen, color, False, points, thickness)

    # Draw center line (subtle)
    pygame.draw.line(
        screen,
        (50, 50, 50),
        (0, center_y),
        (width, center_y),
        1
    )

