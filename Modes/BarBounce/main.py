"""
Eyesy mode: Spectrum Bars with Bouncing Circles
- Bars rise from the bottom using audio input bands (simple banding of eyesy.audio_in)
- Circles bounce around screen and collide with bars and walls
- Knobs:
    knob1 -> number of bars (1..32)
    knob2 -> number of circles (0..12)
    knob3 -> palette selector (0..1..n)
    knob4 -> color selector within palette / color saturation
    knob5 -> background color picker (uses eyesy.color_picker_bg)

Format: defines setup(screen, eyesy) and draw(screen, eyesy)
"""

import pygame
import random
import math

# -----------------------------
# Configuration / helpers
# -----------------------------
MAX_BARS = 32
MAX_CIRCLES = 12
SMOOTHING = 0.85  # bar height smoothing
GRAVITY = 50.0     # small gravity to prevent circles from floating

# Expanded color palettes — now 8 total
PALETTES = [
    [(255, 90, 90), (255, 150, 90), (255, 220, 120), (255,255,255)],          # warm
    [(90, 160, 255), (120, 200, 255), (180,220,255), (255,255,255)],         # cool
    [(160, 255, 120), (120, 255, 180), (220, 255, 200), (255,255,255)],      # fresh
    [(255, 90, 200), (220, 120, 255), (180, 180, 255), (255,255,255)],       # neon
    [(255, 40, 40), (255, 120, 0), (255, 240, 0), (255,255,255)],            # fiery red/yellow
    [(0, 255, 60), (0, 200, 255), (0, 120, 255), (255,255,255)],             # bright cyan-green
    [(255, 0, 100), (200, 0, 200), (100, 0, 255), (255,255,255)],            # magenta-electric purple
    [(40, 40, 40), (120, 120, 120), (200, 200, 200), (255,255,255)],         # grayscale industrial
]

# -----------------------------
# State classes
# -----------------------------
class Circle:
    def __init__(self, x, y, r, color, vx=0, vy=0):
        self.x = x
        self.y = y
        self.r = r
        self.color = color
        self.vx = vx
        self.vy = vy

    def update(self, dt, xres, yres):
        # basic physics with small gravity
        self.vy += GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        # wall collisions
        if self.x - self.r < 0:
            self.x = self.r
            self.vx *= -0.8
        if self.x + self.r > xres:
            self.x = xres - self.r
            self.vx *= -0.8
        if self.y - self.r < 0:
            self.y = self.r
            self.vy *= -0.8
        if self.y + self.r > yres:
            self.y = yres - self.r
            self.vy *= -0.85

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.r))


# -----------------------------
# Eyesy mode API
# -----------------------------

def setup(screen, eyesy):
    # persistent state stored on eyesy.mode_state dict
    state = {}
    state['xres'] = eyesy.xres
    state['yres'] = eyesy.yres
    state['bars'] = 8
    state['circles_n'] = 4
    state['bar_heights'] = [0.0] * MAX_BARS
    state['palette_index'] = 0
    state['palette_shift'] = 0.0
    state['circles'] = []
    state['last_time'] = pygame.time.get_ticks()

    # initialize circles
    for i in range(state['circles_n']):
        r = random.uniform(6, 28)
        x = random.uniform(r, eyesy.xres - r)
        y = random.uniform(r, eyesy.yres/2)
        color = random.choice(PALETTES[state['palette_index']])
        vx = random.uniform(-120, 120)
        vy = random.uniform(-60, 60)
        state['circles'].append(Circle(x, y, r, color, vx, vy))

    # attach state
    eyesy.mode_state = state


def draw(screen, eyesy):
    # state shortcuts
    state = getattr(eyesy, 'mode_state', None)
    if state is None:
        setup(screen, eyesy)
        state = eyesy.mode_state

    xres = eyesy.xres
    yres = eyesy.yres

    # map knobs
    bars_n = max(1, int(1 + eyesy.knob1 * (MAX_BARS - 1)))
    circles_n = int(eyesy.knob2 * MAX_CIRCLES + 0.001)
    palette_index = int(eyesy.knob3 * (len(PALETTES) - 1) + 0.001)
    color_mix = eyesy.knob4  # used to interpolate colors

    # background color via eyesy helper (clears screen on Eyesy host)
    try:
        eyesy.color_picker_bg(eyesy.knob5)
    except Exception:
        screen.fill((10, 10, 10))

    state['palette_index'] = palette_index

    # --- compute frequency bands from audio input ---
    audio = list(eyesy.audio_in) if hasattr(eyesy, 'audio_in') else [0]*100
    mags = [abs(a) / 32767.0 for a in audio]

    band_vals = []
    samples_per_band = max(1, len(mags) // bars_n)
    for b in range(bars_n):
        start = b * samples_per_band
        end = start + samples_per_band
        band = mags[start:end]
        val = sum(band) / len(band) if band else 0.0
        band_vals.append(val)

    for i in range(bars_n):
        prev = state['bar_heights'][i]
        target = band_vals[i]
        state['bar_heights'][i] = prev * SMOOTHING + target * (1.0 - SMOOTHING)

    bar_w = xres / bars_n
    bar_rects = []
    max_bar_h = yres * 0.9
    for i in range(bars_n):
        h = state['bar_heights'][i] * max_bar_h * (0.6 + 0.8 * color_mix)
        x = int(i * bar_w)
        y = int(yres - h)
        rect = pygame.Rect(x, y, int(math.ceil(bar_w)), int(h))

        palette = PALETTES[state['palette_index']]
        p0 = palette[i % len(palette)]
        p1 = palette[(i+1) % len(palette)]
        t = min(1.0, state['bar_heights'][i] * 1.8)
        col = (
            int(p0[0] * (1-t) + p1[0] * t),
            int(p0[1] * (1-t) + p1[1] * t),
            int(p0[2] * (1-t) + p1[2] * t)
        )

        pygame.draw.rect(screen, col, rect)
        bar_rects.append(rect)

    while len(state['circles']) < circles_n:
        r = random.uniform(6, 28)
        x = random.uniform(r, xres - r)
        y = random.uniform(r, yres/2)
        palette = PALETTES[state['palette_index']]
        base_color = random.choice(palette)
        color = tuple(max(0, min(255, int(c * (0.6 + 0.8 * color_mix)))) for c in base_color)
        vx = random.uniform(-120, 120)
        vy = random.uniform(-80, 80)
        state['circles'].append(Circle(x, y, r, color, vx, vy))

    while len(state['circles']) > circles_n:
        state['circles'].pop()

    now = pygame.time.get_ticks()
    dt = (now - state.get('last_time', now)) / 1000.0
    dt = max(1.0/120.0, min(1.0/15.0, dt))
    state['last_time'] = now

    for i, c in enumerate(state['circles']):
        c.update(dt, xres, yres)

    for i in range(len(state['circles'])):
        for j in range(i+1, len(state['circles'])):
            a = state['circles'][i]
            b = state['circles'][j]
            dx = b.x - a.x
            dy = b.y - a.y
            dist = math.hypot(dx, dy)
            min_dist = a.r + b.r
            if dist > 0 and dist < min_dist:
                overlap = 0.5 * (min_dist - dist + 1)
                nx = dx / dist
                ny = dy / dist
                a.x -= nx * overlap
                a.y -= ny * overlap
                b.x += nx * overlap
                b.y += ny * overlap
                a.vx, b.vx = b.vx * 0.9, a.vx * 0.9
                a.vy, b.vy = b.vy * 0.9, a.vy * 0.9

    for c in state['circles']:
        for idx, rect in enumerate(bar_rects):
            nearest_x = max(rect.left, min(c.x, rect.right))
            nearest_y = max(rect.top, min(c.y, rect.bottom))
            dx = c.x - nearest_x
            dy = c.y - nearest_y
            if dx*dx + dy*dy <= c.r*c.r:
                if c.y < rect.centery:
                    c.y = rect.top - c.r - 0.5
                    c.vy = -abs(c.vy) * 0.85 - (state['bar_heights'][idx] * 200)
                    offset = (c.x - rect.centerx) / (rect.width/2.0)
                    c.vx += offset * 60

    for c in state['circles']:
        shadow = (max(0, c.color[0]//6), max(0, c.color[1]//6), max(0, c.color[2]//6))
        pygame.draw.circle(screen, shadow, (int(c.x+3), int(c.y+3)), int(c.r))
        c.draw(screen)

    #try:
    #    font = pygame.font.SysFont('Arial', 14)
    #    hud = font.render(f'Bars: {bars_n}  Circles: {len(state["circles"])}  Palette: {state["palette_index"]}', True, (240,240,240))
    #    screen.blit(hud, (8, 8))
    #except Exception:
        pass

    state['palette_shift'] += dt * 0.05


if __name__ == '__main__':
    pygame.init()
    X, Y = 640, 360
    screen = pygame.display.set_mode((X, Y))
    class Dummy:
        pass
    eyesy = Dummy()
    eyesy.audio_in = [0]*100
    eyesy.trig = False
    eyesy.xres = X
    eyesy.yres = Y
    eyesy.knob1 = 0.2
    eyesy.knob2 = 0.3
    eyesy.knob3 = 0.0
    eyesy.knob4 = 0.5
    eyesy.knob5 = 0.0
    eyesy.color_picker_bg = lambda v: screen.fill((int(40*v), int(20*v), int(80*v)))
    setup(screen, eyesy)
    clock = pygame.time.Clock()
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
        t = pygame.time.get_ticks()/1000.0
        for i in range(100):
            eyesy.audio_in[i] = int(30000 * abs(math.sin(t*2 + i*0.2)) * (1.0 if i<10 else 0.1))
        draw(screen, eyesy)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()
