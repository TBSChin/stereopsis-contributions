# AudioSpiralScope by TRC 2026
# Knob Controls
# Knob 1 – Kaleidoscope Slices (6-24 slices)
# Knob 2 – Spiral Spacing (Density)
# Knob 3 – Swirl Speed / Intensity
# Knob 4 – Color Palette
# Knob 5 – Background Color
#
import pygame
import math

def setup(screen, eyesy):
    # Spiral direction: 1 or -1
    draw.direction = 1

def draw(screen, eyesy):
    eyesy.color_picker_bg(eyesy.knob5)

    # Flip swirl direction on trigger
    if eyesy.trig:
        draw.direction *= -1

    cx = int(eyesy.xres / 2)
    cy = int(eyesy.yres / 2)

    # Audio energy
    audio = sum(abs(a) for a in eyesy.audio_in) / len(eyesy.audio_in)
    audio_norm = min(audio / 14000.0, 1.0)

    t = pygame.time.get_ticks() * 0.001

    # Controls
    slices = int(6 + eyesy.knob1 * 18)
    spacing = 1.5 + eyesy.knob2 * 6
    thickness = int(1 + audio_norm * 5)

    # Fill entire screen
    max_radius = math.hypot(cx, cy)
    turns = int(max_radius / spacing)

    # Build ONE swirly spiral
    base_points = []
    for i in range(turns):
        base_angle = i * 0.22

        # Swirl modulation (direction flips on trig)
        swirl = (
            math.sin(i * 0.08 + t * (1.5 + eyesy.knob3))
            * (1.0 + audio_norm * 2.0)
            * draw.direction
        )

        angle = base_angle + swirl

        # Outward growth
        radius = i * spacing * (0.6 + audio_norm * 0.8)

        # Radial wobble
        wobble = math.sin(i * 0.15 + t * 2.0) * audio_norm * 10
        r = radius + wobble

        x = math.cos(angle) * r
        y = math.sin(angle) * r
        base_points.append((x, y))

    # Kaleidoscope draw
    for s in range(slices):
        rot = (math.tau / slices) * s
        mirror = -1 if s % 2 else 1
        color = eyesy.color_picker((eyesy.knob4 + s / slices) % 1.0)

        points = []
        for x, y in base_points:
            rx = mirror * (x * math.cos(rot) - y * math.sin(rot))
            ry = x * math.sin(rot) + y * math.cos(rot)
            points.append((int(cx + rx), int(cy + ry)))

        pygame.draw.lines(screen, color, False, points, thickness)
