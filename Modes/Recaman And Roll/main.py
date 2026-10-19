import pygame
import math

def recaman_sequence(n):
    seq = [0]
    for i in range(1, n):
        prev = seq[-1] - i
        if prev > 0 and prev not in seq:
            seq.append(prev)
        else:
            seq.append(seq[-1] + i)
    return seq

sequence = []
arc_index = 0
max_terms = 100

def setup(screen, eyesy):
    global sequence, arc_index
    sequence = recaman_sequence(max_terms)
    arc_index = 0

def draw(screen, eyesy):
    global sequence, arc_index

    eyesy.color_picker_bg(eyesy.knob5)
    base_color = eyesy.color_picker(eyesy.knob4)

    screen_width = eyesy.xres
    screen_height = eyesy.yres
    center_y = screen_height / 2

    # Scale so arcs fill screen horizontally
    max_seq_val = max(sequence)
    available_width = screen_width - 200  # margins
    scale = available_width / max_seq_val

    # Audio level
    audio_level = sum(abs(a) for a in eyesy.audio_in) / len(eyesy.audio_in)
    audio_norm = min(audio_level / 15000.0, 1.0)

    # Use Knob1 to control base thickness
    base_thickness = int(1 + eyesy.knob1 * 15)  # from 1 to ~16

    # Grow arc index based on audio
    arc_index += int(audio_norm * 5) + 1
    arc_index = min(arc_index, len(sequence) - 1)

    for i in range(arc_index):
        a = sequence[i]
        b = sequence[i + 1]
        x1 = a * scale + 100
        x2 = b * scale + 100
        radius = abs(x2 - x1) / 2
        center_x = (x1 + x2) / 2

        rect = pygame.Rect(center_x - radius, center_y - radius, 2 * radius, 2 * radius)

        # Alternate arc direction
        if i % 2 == 0:
            start_angle = math.pi
            end_angle = 2 * math.pi
        else:
            start_angle = 0
            end_angle = math.pi

        # Color variation
        r = (base_color[0] + i * 4 + int(audio_norm * 120)) % 256
        g = (base_color[1] + i * 7 + int(audio_norm * 180)) % 256
        b = (base_color[2] + i * 5 + int(audio_norm * 220)) % 256

        arc_color = (r, g, b)

        # Final thickness combines knob and audio energy
        thickness = base_thickness + int(audio_norm * 8)

        pygame.draw.arc(screen, arc_color, rect, start_angle, end_angle, thickness)

    # Reset on trigger
    if arc_index >= len(sequence) - 1 and eyesy.trig:
        arc_index = 0
