import pygame
import math
import time

grid_radii = {}

def setup(screen, eyesy):
    global start_time, reactive_amp, grid_radii
    start_time = time.time()
    reactive_amp = 0.0
    grid_radii = {}

def draw_waveform_rings(screen, eyesy, t, reactive_amp):
    width = int(eyesy.xres)
    height = int(eyesy.yres)
    cx = width // 2
    cy = height // 2

    max_radius = int(math.hypot(cx, cy))

    spacing = int((24 + eyesy.knob2 * 24) * 3)
    num_rings = max_radius // spacing

    angle_freq = 2 + eyesy.knob1 * 20
    base_wave_speed = 0.6

    for ring in range(1, num_rings):
        base_r = ring * spacing
        points = []

        # Alternate spin direction
        direction = 1 if ring % 2 == 0 else -1
        wave_speed = t * base_wave_speed * direction

        for deg in range(0, 360, 4):
            angle = math.radians(deg)
            dx = math.cos(angle)
            dy = math.sin(angle)

            phase = angle * angle_freq + wave_speed
            mod = math.sin(phase)
            r = base_r + mod * (10 + 80 * reactive_amp)

            x = int(cx + dx * r)
            y = int(cy + dy * r)
            points.append((x, y))

        # Fade toward edge by setting color brightness
        fade = 1.0 - (base_r / max_radius)
        fade = max(0.0, min(1.0, fade))
        brightness = int(100 * fade)  # scale brightness from 0 to 100
        ring_color = (brightness, brightness, brightness)

        if len(points) > 2:
            pygame.draw.aalines(screen, ring_color, True, points, 1)


def draw(screen, eyesy):
    global start_time, reactive_amp, grid_radii
    t = time.time() - start_time

    width = int(eyesy.xres)
    height = int(eyesy.yres)
    cx = width // 2
    cy = height // 2

    eyesy.color_picker_bg(eyesy.knob5)

    # Audio input and smoothing
    audio_level = sum(abs(v) for v in eyesy.audio_in) / len(eyesy.audio_in)
    raw_audio_norm = min(1.0, audio_level / 32768)
    reactive_amp += (raw_audio_norm - reactive_amp) * 0.1
    reactive_amp *= 0.995

    # Grid resolution
    step = int(24 + eyesy.knob2 * 24)
    cols = int(width // step)
    rows = int(height // step)

    # Wave and color config
    wave_speed = t * 0.6
    base_freq = 0.05 + eyesy.knob1 * 0.2
    amp_mod = 1.0 + reactive_amp * 1.5

    base_color = eyesy.knob4
    color_spread = eyesy.knob3

    # 🌀 Draw spinning waveform contour rings
    draw_waveform_rings(screen, eyesy, t, reactive_amp)

    for j in range(rows):
        for i in range(cols):
            x = int(i * step + step / 2)
            y = int(j * step + step / 2)

            dx = x - cx
            dy = y - cy
            dist = math.hypot(dx, dy)

            base_wave = (math.sin(dist * base_freq - wave_speed) + 1) / 2
            wave = (math.sin(dist * base_freq * amp_mod - wave_speed) + 1) / 2

            # Color
            color_val = base_color + (base_wave - 0.5) * color_spread
            color_val = max(0.0, min(1.0, color_val))
            color = eyesy.color_picker(color_val)

            # Max radius scales with audio
            base_max = 0.35
            extra = 0.75 * reactive_amp
            max_radius = int(step * (base_max + extra))
            target_radius = max(2, int(max_radius * wave))

            key = (i, j)
            prev_radius = grid_radii.get(key, target_radius)

            # Limit radius change to ±1 per frame
            max_step = 1.0
            delta = target_radius - prev_radius
            if abs(delta) > max_step:
                delta = max_step if delta > 0 else -max_step
            smooth_radius = prev_radius + delta

            grid_radii[key] = smooth_radius

            pygame.draw.circle(screen, color, (x, y), int(smooth_radius))
