# Knob 1 → Tile size
# Knob 2 → Line thickness
# Knob 3 → Shape mode (arcs, lines, trangles, random lines)
# Knob 4 → Color palette (Dynamic color cycling that stops or slows with low audio)
# Knob 5 → Background color

import pygame
import random
import math
import time

tile_states = []
prev_num_columns = -1
color_time = 0.0
guitar_env = 0.0
guitar_cooldown = 0.0
guitar_last = None


def guitar_response(eyesy):
    """Mono-safe, gated envelope and pick onsets, independent of frame rate."""
    global guitar_env, guitar_cooldown, guitar_last
    now = time.monotonic()
    dt = min(0.1, max(0.001, now - guitar_last)) if guitar_last is not None else 1.0 / 30.0
    guitar_last = now
    def rms(samples):
        return math.sqrt(sum((float(v) / 32768.0) ** 2 for v in samples) / len(samples)) if len(samples) else 0.0
    level = max(rms(eyesy.audio_in), rms(getattr(eyesy, 'audio_in_r', [])))
    # Fixed noise gate, then gentle compression: quiet notes count, loud chords
    # retain headroom instead of pinning the effect at maximum.
    drive = 1.0 - math.exp(-max(0.0, level - 0.0015) / 0.035)
    guitar_cooldown = max(0.0, guitar_cooldown - dt)
    attack = (drive > 0.07 and drive > guitar_env * 1.35 + 0.035 and guitar_cooldown <= 0.0)
    if attack:
        guitar_cooldown = 0.12
    tau = 0.018 if drive > guitar_env else 0.18
    guitar_env += (drive - guitar_env) * (1.0 - math.exp(-dt / tau))
    return guitar_env, attack, dt

def generate_random_lines(size):
    lines = []
    for _ in range(3):
        x1 = random.randint(0, int(size))
        y1 = random.randint(0, int(size))
        x2 = random.randint(0, int(size))
        y2 = random.randint(0, int(size))
        lines.append((x1, y1, x2, y2))
    return lines

def setup(screen, eyesy):
    global tile_states, prev_num_columns, color_time, guitar_env, guitar_cooldown, guitar_last

    width = eyesy.xres
    height = eyesy.yres

    desired_tile_size = int(30 + eyesy.knob1 * 80)
    num_columns = max(1, int(width / desired_tile_size))
    tile_size = width / num_columns
    num_rows = int(height / tile_size) + 1

    tile_states = []
    for row in range(num_rows):
        for col in range(num_columns):
            tile_states.append({
                'row': row,
                'col': col,
                'flip': random.choice([True, False]),
                'random_lines': generate_random_lines(tile_size),
                'triangle_type': random.randint(0, 3)
            })
    prev_num_columns = num_columns
    color_time = 0.0
    guitar_env = guitar_cooldown = 0.0
    guitar_last = None

def draw(screen, eyesy):
    global tile_states, prev_num_columns, color_time

    width = eyesy.xres
    height = eyesy.yres

    eyesy.color_picker_bg(eyesy.knob5)

    desired_tile_size = int(30 + eyesy.knob1 * 80)
    num_columns = max(1, int(width / desired_tile_size))
    tile_size = width / num_columns
    num_rows = int(height / tile_size) + 1

    if num_columns != prev_num_columns:
        tile_states = []
        for row in range(num_rows):
            for col in range(num_columns):
                tile_states.append({
                    'row': row,
                    'col': col,
                    'flip': random.choice([True, False]),
                    'random_lines': generate_random_lines(tile_size),
                    'triangle_type': random.randint(0, 3)
                })
        prev_num_columns = num_columns

    energy, attack, dt = guitar_response(eyesy)
    color_time += energy * 3.0 * dt
    # Pick attacks rearrange a substantial subset; sustained notes continue
    # evolving the pattern slowly. Manual/MIDI triggers still work.
    event = attack or bool(eyesy.trig)
    probability = (0.30 + 0.50 * energy) if event else (1.0 - math.exp(-energy * 1.4 * dt))
    for tile in tile_states:
        if random.random() < probability:
            tile['flip'] = not tile['flip']
            tile['random_lines'] = generate_random_lines(tile_size)
            tile['triangle_type'] = random.randint(0, 3)

    k3 = eyesy.knob3
    if k3 < 0.25:
        shape_mode = "arc"
    elif k3 < 0.5:
        shape_mode = "line"
    elif k3 < 0.75:
        shape_mode = "triangle"
    else:
        shape_mode = "random"

    sel = eyesy.knob4 * 8
    thickness = int(1 + eyesy.knob2 * 10)

    for i, tile in enumerate(tile_states):
        row = tile['row']
        col = tile['col']
        x = col * tile_size
        y = row * tile_size
        rect = pygame.Rect(int(x), int(y), int(tile_size), int(tile_size))
        flip = tile['flip']

        if sel >= 7:
            color = (
                int(127 + 127 * math.sin(i * 0.1 + color_time)),
                int(127 + 127 * math.sin(i * 0.05 + color_time)),
                int(127 + 127 * math.sin(i * 0.01 + color_time))
            )
        elif 1 <= sel < 2:
            color = (int(127 + 127 * math.sin(i * 0.1 + color_time)), 42, 75)
        elif 2 <= sel < 3:
            color = (75, int(127 + 127 * math.sin(i * 0.1 + color_time)), 42)
        elif 3 <= sel < 4:
            color = (42, 75, int(127 + 127 * math.sin(i * 0.1 + color_time)))
        elif 4 <= sel < 5:
            color = (int(127 + 127 * math.sin(i * 0.1 + color_time)), 255, 127)
        elif 5 <= sel < 6:
            color = (255, int(127 + 127 * math.sin(i * 0.1 + color_time)), 127)
        elif 6 <= sel < 7:
            color = (205, 200, int(127 + 127 * math.sin(i * 0.1 + color_time)))
        else:
            color = (
                int(127 + 127 * math.sin(i * 0.1 + color_time)),
                int(127 + 127 * math.sin(i * 0.1 + color_time)),
                int(127 + 127 * math.sin(i * 0.1 + color_time))
            )

        if shape_mode == "arc":
            if flip:
                pygame.draw.arc(screen, color, rect, 0, math.pi / 2, thickness)
                pygame.draw.arc(screen, color, rect, math.pi, 3 * math.pi / 2, thickness)
            else:
                pygame.draw.arc(screen, color, rect, math.pi / 2, math.pi, thickness)
                pygame.draw.arc(screen, color, rect, 3 * math.pi / 2, 2 * math.pi, thickness)

        elif shape_mode == "line":
            if flip:
                pygame.draw.line(screen, color, (x, y), (x + tile_size, y + tile_size), thickness)
            else:
                pygame.draw.line(screen, color, (x + tile_size, y), (x, y + tile_size), thickness)

        elif shape_mode == "triangle":
            t = tile['triangle_type']
            if t == 0:
                points = [(x, y), (x + tile_size, y), (x, y + tile_size)]
            elif t == 1:
                points = [(x + tile_size, y), (x + tile_size, y + tile_size), (x, y + tile_size)]
            elif t == 2:
                points = [(x, y), (x + tile_size, y), (x + tile_size, y + tile_size)]
            else:
                points = [(x, y), (x, y + tile_size), (x + tile_size, y + tile_size)]
            pygame.draw.polygon(screen, color, points, 0)

        elif shape_mode == "random":
            if flip:
                for line_pts in tile['random_lines']:
                    rx1, ry1, rx2, ry2 = line_pts
                    pygame.draw.line(screen, color, (x + rx1, y + ry1), (x + rx2, y + ry2), thickness)
            else:
                pygame.draw.line(screen, color, (x, y), (x + tile_size, y + tile_size), thickness)
