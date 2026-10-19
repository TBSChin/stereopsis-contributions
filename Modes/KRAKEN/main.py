# RELEASE THE KRAKEN!!
#
# Knob 1 – Tentacle Flailiness
#   Range: from noodly (centered) to straight and still (far left or right).
#   At center, tentacles extend mostly straight. Left or right causes them to wiggle.
#
# Knob 2 – Kraken Scale Random LFO Modulator
#   Controls: speed and intensity of the Kraken’s pulsing size (scale).
#   Inverted: all the way up = calm and slow, all the way down = fast and chaotic.
#
# Knob 4 – Bubble Trail Color
#   All the way down: white bubbles
#   Between 0–0.99: bubble color chosen via HSV color picker
#   All the way up: fully random RGB per bubble
#
# Knob3 – Reserved for future use
#
# Knob 5 – Background Style
#   0.0: Black as the deepest depths
#   0.01–0.3: Organic shimmering sea colors (blue/green)
#   0.4–0.8: Smooth hue fade via HSV
#   0.8-0.98: Random color flashes (seizire mode)
#   0.98–1.0: Smooth looping rainbow LFO
#
import pygame
import math
import random

KRAKEN_COLOR = (10, 80, 60)
NORMAL_EYE_COLOR = (255, 255, 255)
ANGRY_EYE_COLOR = (255, 50, 50)
PUPIL_COLOR = (0, 0, 0)
TEETH_COLOR = (255, 255, 255)

NUM_TENTACLES = 9
TENTACLE_LENGTH = 60
TENTACLE_SEGMENTS = 13
bubbles = []

angry = False
angry_timer = 0
random_phase = random.uniform(0, 100)

def setup(screen, eyesy):
    global t_offsets, x_pos, y_pos, x_vel, y_vel, angry, angry_timer
    t_offsets = [random.uniform(0, 2 * math.pi) for _ in range(NUM_TENTACLES)]
    x_pos = eyesy.xres / 2
    y_pos = eyesy.yres / 2
    x_vel = 0
    y_vel = 0
    angry = False
    angry_timer = 0
    
def draw(screen, eyesy):
    global x_pos, y_pos, x_vel, y_vel, bubbles, angry, angry_timer, random_phase

    time = pygame.time.get_ticks() / 1000.0
    dynamic_background(screen, eyesy, time)

    audio = eyesy.audio_in
    left = sum(audio[:50]) / 50
    right = sum(audio[50:]) / 50
    amplitude = sum([abs(v) for v in audio]) / len(audio) / 32768

    if angry_timer > 0:
        angry_timer -= 1
    elif random.random() < 0.01:
        angry = True
        angry_timer = random.randint(10, 30)
    else:
        angry = False

    dx = (right - left) / 32768 * 100
    dy = math.sin(time * 3) * amplitude * 14.92
    move_scale = 0.3 if not angry else 1.2

    kraken_scale = 1 + eyesy.knob2 * 1.5
    
    x_vel += dx * move_scale
    y_vel += dy * move_scale
    x_vel *= 0.9
    y_vel *= 0.9
    x_pos += x_vel
    y_pos += y_vel

    x_pos = max(40, min(eyesy.xres - 40, x_pos))
    y_pos = max(40, min(eyesy.yres - 40, y_pos))
    center = (int(x_pos), int(y_pos))
    face_offset = int(x_vel * 0.99)

    lfo = 0.5 + 0.5 * math.sin(time * 2 + eyesy.knob2 * 10)
    #kraken_scale = 0.5 + lfo * 1.5
    
    # Random LFO-based kraken scale (knob2 modulates speed and variation)
    lfo_speed = 1.0 + (1.0 - eyesy.knob2) * 4.0
    lfo_variation = 0.5 + (1.0 - eyesy.knob2) * 0.5
    kraken_scale = 1.7 + lfo_variation * math.sin(time * lfo_speed + random_phase)
    
    for i in range(NUM_TENTACLES):
        angle = i * (2 * math.pi / NUM_TENTACLES)
        base_x = center[0] + 30 * kraken_scale * math.cos(angle)
        base_y = center[1] + 30 * kraken_scale * math.sin(angle)

        if angry:
            flailiness = 0.0
        else:
            flailiness = 0.6 + eyesy.knob1 * -1.1

        draw_tentacle(screen, base_x, base_y, angle, time + t_offsets[i], flailiness, kraken_scale)

    pygame.draw.circle(screen, KRAKEN_COLOR, center, int(40 * kraken_scale))

    draw_eyes(screen, center, face_offset, angry, kraken_scale)
    mouth_open = 1.0 if eyesy.trig else 0.1
    draw_mouth(screen, center, face_offset, mouth_open, kraken_scale)

    bubble_origin = (center[0] + face_offset, center[1] + 20)
    if random.random() < amplitude * 2.5:
        bubbles.append({
            'x': bubble_origin[0] + random.randint(-5, 5),
            'y': bubble_origin[1],
            'radius': random.randint(4, 8),
            'speed': random.uniform(1.0, 2.5),
            'life': 100,
            'color': tuple(int(c) for c in bubble_color_from_knob(eyesy.knob4))
        })

    new_bubbles = []
    for b in bubbles:
        b['y'] -= b['speed']
        b['life'] -= 2
        if b['life'] > 0:
            alpha = max(0, min(255, b['life'] * 2))
            s = pygame.Surface((b['radius']*2, b['radius']*2), pygame.SRCALPHA)
            r, g, b_color = b['color']
            pygame.draw.circle(s, (r, g, b_color, int(alpha)), (b['radius'], b['radius']), b['radius'], 1)
            screen.blit(s, (b['x'] - b['radius'], b['y'] - b['radius']))
            new_bubbles.append(b)
    bubbles = new_bubbles

def draw_tentacle(screen, x, y, base_angle, time, noodliness, scale):
    angle = base_angle
    points = [(int(x), int(y))]
    widths = []
    effective_length = TENTACLE_LENGTH * 2.4 * scale
    length_per_segment = effective_length / TENTACLE_SEGMENTS

    for i in range(TENTACLE_SEGMENTS):
        offset = math.sin(time * 2 + i * 0.5) * noodliness
        angle += offset
        x += length_per_segment * math.cos(angle)
        y += length_per_segment * math.sin(angle)
        points.append((int(x), int(y)))
        t = i / TENTACLE_SEGMENTS
        widths.append(int((6 * (1 - t) + 2 * t) * scale))

    for i in range(TENTACLE_SEGMENTS):
        pygame.draw.line(screen, KRAKEN_COLOR, points[i], points[i+1], widths[i])

def draw_mouth(screen, center, face_offset, mouth_open, kraken_scale):
    mx = center[0] + face_offset
    my = center[1] + int(10 * kraken_scale)
    width = int(25 * kraken_scale)
    height = int((10 + 15 * mouth_open) * kraken_scale)
    pygame.draw.ellipse(screen, (0, 0, 0), (mx - width//2, my, width, height))

    num_teeth = 6
    for i in range(num_teeth):
        tx = mx - width//2 + i * (width // (num_teeth - 1))
        ty = my + 2 + height // 2
        tooth_height = (5 + 5 * mouth_open) * kraken_scale
        points = [
            (tx, ty),
            (tx - int(3 * kraken_scale), int(ty + tooth_height)),
            (tx + int(3 * kraken_scale), int(ty + tooth_height))
        ]
        pygame.draw.polygon(screen, TEETH_COLOR, points)

def draw_eyes(screen, center, offset_x, angry, scale):
    eye_offset_x = int(15 * scale)
    eye_y = center[1] - int(10 * scale)
    eye_color = ANGRY_EYE_COLOR if angry else NORMAL_EYE_COLOR

    for dx in [-eye_offset_x, eye_offset_x]:
        ex = center[0] + dx + offset_x
        ey = eye_y
        pygame.draw.circle(screen, eye_color, (ex, ey), int(8 * scale))
        pygame.draw.circle(screen, PUPIL_COLOR, (ex, ey), int(4 * scale))

        if angry:
            if dx < 0:
                points = [
                    (ex + int(6 * scale), ey - int(4 * scale)),
                    (ex - int(6 * scale), ey - int(6 * scale)),
                    (ex - int(6 * scale), ey - int(2 * scale)),
                    (ex + int(6 * scale), ey)
                ]
            else:
                points = [
                    (ex - int(6 * scale), ey - int(4 * scale)),
                    (ex + int(6 * scale), ey - int(6 * scale)),
                    (ex + int(6 * scale), ey - int(2 * scale)),
                    (ex - int(6 * scale), ey)
                ]
            pygame.draw.polygon(screen, (0, 0, 0), points)

def hsv_to_rgb(h, s, v):
    i = int(h * 6)
    f = h * 6 - i
    p = int(255 * v * (1 - s))
    q = int(255 * v * (1 - f * s))
    t = int(255 * v * (1 - (1 - f) * s))
    v = int(255 * v)
    i = i % 6
    if i == 0: return (v, t, p)
    if i == 1: return (q, v, p)
    if i == 2: return (p, v, t)
    if i == 3: return (p, q, v)
    if i == 4: return (t, p, v)
    if i == 5: return (v, p, q)

def dynamic_background(screen, eyesy, time):
    knob = eyesy.knob5

    if knob <= 0.01:
        screen.fill((0, 0, 0))
    elif knob <= 0.3:
        t = pygame.time.get_ticks() / 500.0
        blue = int(80 + 80 * math.sin(t))
        green = int(30 + 40 * math.sin(t + 1.5))
        green = max(0, min(255, green))
        blue = max(0, min(255, blue))
        screen.fill((0, green, blue))
    elif knob <= 0.9:
        hue = (knob - 0.2) / 0.3
        color = hsv_to_rgb(hue, 1.0, 1.0)
        screen.fill(color)
    elif knob >= 0.98:
        speed = knob * 2.0
        hue = (math.sin(time * speed) + 1) / 2
        color = hsv_to_rgb(hue, 1.0, 1.0)
        screen.fill(color)
    else:
        screen.fill((
            random.randint(50, 255),
            random.randint(50, 255),
            random.randint(50, 255)
        ))

def bubble_color_from_knob(knob4):
    if knob4 <= 0.01:
        return (255, 255, 255)
    elif knob4 >= 0.99:
        return (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
    else:
        hue = knob4
        return hsv_to_rgb(hue, 1.0, 1.0)
