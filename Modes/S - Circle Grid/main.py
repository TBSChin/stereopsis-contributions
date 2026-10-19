"""Circle Grid

A grid of circles that react to audio.
Knobs:
- Knob1: Grid size (number of circles)
- Knob2: Circle base size
- Knob3: Color/Hue
- Knob4: Audio reactivity
- Knob5: Rotation
"""
import pygame
import math


# State
rotation = 0


def setup(screen, eyesy):
    """Called once when mode is loaded."""
    global rotation
    rotation = 0


def draw(screen, eyesy):
    """Called every frame."""
    global rotation

    # Get parameters
    grid_size = 3 + int(eyesy.knob1 * 10)  # 3-13 circles per row
    base_radius = 10.0 + eyesy.knob2 * 50.0  # 10-60 base radius
    hue = eyesy.knob3
    audio_react = eyesy.knob4 * 2.0  # 0-2 reactivity
    rotation_speed = (eyesy.knob5 - 0.5) * 0.1  # -0.05 to 0.05

    # Update rotation
    rotation += rotation_speed

    # Screen dimensions
    w = 1280
    h = 720
    hw = 640.0
    hh = 360.0

    # Calculate grid spacing
    spacing_x = float(w) / (grid_size + 1)
    spacing_y = float(h) / (grid_size + 1)

    # Pre-compute rotation
    cos_r = math.cos(rotation)
    sin_r = math.sin(rotation)

    # Get audio data (normalize int16 to float if needed)
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

    # Draw circles
    for row in range(grid_size):
        # Color per row
        cv = (hue + row * 0.05) % 1.0
        color = eyesy.color_picker(cv)
        r = int(color[0])
        g = int(color[1])
        b = int(color[2])

        cy = spacing_y * (row + 1) - hh

        for col in range(grid_size):
            cx = spacing_x * (col + 1) - hw

            # 2D rotation matrix
            px = int(hw + cx * cos_r - cy * sin_r)
            py = int(hh + cx * sin_r + cy * cos_r)

            # Radius from audio
            index = (row * grid_size + col) % 100
            sample = abs(float(audio[index]))
            radius = int(base_radius + sample * base_radius * audio_react)
            if radius < 1:
                radius = 1

            pygame.draw.circle(screen, (r, g, b), (px, py), radius)

    # Trigger effect: flash ring
    if eyesy.trig:
        tc = eyesy.color_picker(hue)
        pygame.draw.circle(screen, (int(tc[0]), int(tc[1]), int(tc[2])), (640, 360), 288, 3)
