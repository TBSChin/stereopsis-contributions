# Mode: RetroRorschach
# Description: A bi-directional, audio-reactive Muirhead-Newell maze design
# with symmetrical mirroring.
'''
CONTROLS:

Knob 1 (The Scroll): Re-centered bi-directional motion. 12 o'clock is still; turn right to ascend, left to descend.

Knob 2 (The Ink): Controls density. Low is sparse and skeletal; high is a thick, solid blot.

Knob 3 (The Glitch): Adjusts mutation rate. Higher values cause horizontal "tears" and structural breaks in the symmetry.

Knobs 4 & 5: Your foreground and background color palette.
'''

import pygame
import random

MAZE_WIDTH = 32
MAZE_HEIGHT = 36

maze = []
scroll_accum = 0.0
entropy = 0.05

# ---------------- MAZE CORE ----------------

def mk_bit(a, b, c, d, e):
    bkin = [a, b]
    dkin = [c, d]
    cblock = [a, c, d]

    baseb = bkin.count(b)
    based = dkin.count(d)
    bkin0 = baseb + (1 if b == 0 else 0)
    bkin1 = baseb + (1 if b == 1 else 0)
    dkin0 = based + (1 if d == 0 else 0)
    dkin1 = based + (1 if d == 1 else 0)

    if bkin0 == 0: return 1
    if bkin1 == 0: return 0
    if dkin0 == 0: return 1
    if dkin1 == 0: return 0
    if (bkin0 + dkin0) > 4: return 1
    if (bkin1 + dkin1) > 4: return 0
    if cblock.count(cblock[0]) == 3:
        return 1 - cblock[0]

    return random.choice([0, 1])

def gen_maze_row(row1, row2, entropy, knob2, knob3):
    """
    row1 = nearest row
    row2 = row behind that
    """
    new_row = []
    padded1 = [1, 0] + row1 + [0, 1]
    padded2 = [1, 0] + row2 + [0, 1]

    for i in range(MAZE_WIDTH):
        a = padded1[i]
        b = padded1[i+1]
        c = padded1[i+2]
        d = padded2[i+2]   
        e = padded2[i+3]

        bit = mk_bit(a, b, c, d, e)

        if random.random() < entropy:
            bit = 1 - bit

        new_row.append(bit)

    # ---------- DENSITY HOMEOSTASIS ----------
    target_density = 0.25 + knob2 * 0.5  
    band = 0.08
    density = sum(new_row) / MAZE_WIDTH

    if density < target_density - band:
        new_row[random.randrange(MAZE_WIDTH)] = 1
    elif density > target_density + band:
        new_row[random.randrange(MAZE_WIDTH)] = 0

    # ---------- COHERENT MUTATION ----------
    if random.random() < (0.02 + knob3 * 0.18):
        start = random.randrange(MAZE_WIDTH - 3)
        val = random.choice([0, 1])
        for i in range(start, start + random.randint(2, 4)):
            new_row[i] = val

    return new_row

# ---------------- SETUP ----------------

def reset_maze():
    seed = [random.choice([0, 1]) for _ in range(MAZE_WIDTH)]
    return [seed[:] for _ in range(MAZE_HEIGHT)]

def setup(screen, eyesy):
    global maze, entropy
    maze = reset_maze()
    entropy = 0.04

# ---------------- DRAW ----------------

def draw(screen, eyesy):
    global maze, scroll_accum, entropy

    eyesy.color_picker_bg(eyesy.knob5)

    # --- AUDIO ---
    audio_level = sum(abs(v) for v in eyesy.audio_in) / len(eyesy.audio_in)
    audio_norm = min(audio_level / 12000.0, 1.0)

    # --- BI-DIRECTIONAL AUDIO MOTION (KNOB 1) ---
    # 0.5 is center (stop), < 0.5 is down, > 0.5 is up
    direction = eyesy.knob1 - 0.5
    speed = (audio_norm * direction) * 3.0 
    scroll_accum += speed

    # Scroll UP logic
    if scroll_accum >= 1.0:
        scroll_accum = 0.0
        
        # entropy breathes with sound
        entropy += (audio_norm - 0.4) * 0.02
        entropy = max(0.01, min(entropy, 0.18))

        maze.pop(0) # Remove top row
        maze.append(gen_maze_row(maze[-1], maze[-2], entropy, eyesy.knob2, eyesy.knob3))

    # Scroll DOWN logic
    elif scroll_accum <= -1.0:
        scroll_accum = 0.0

        entropy += (audio_norm - 0.4) * 0.02
        entropy = max(0.01, min(entropy, 0.18))

        maze.pop(-1) # Remove bottom row
        # Generate new row based on the current top two rows
        maze.insert(0, gen_maze_row(maze[0], maze[1], entropy, eyesy.knob2, eyesy.knob3))

    # --- COLOR ---
    base = eyesy.color_picker(eyesy.knob4)
    bright = 0.6 + audio_norm * 1.4
    color = (
        min(int(base[0] * bright), 255),
        min(int(base[1] * bright), 255),
        min(int(base[2] * bright), 255),
    )

    # --- DRAW ---
    cell_w = eyesy.xres / (MAZE_WIDTH * 2)
    cell_h = eyesy.yres / MAZE_HEIGHT

    for y, row in enumerate(maze):
        for x, v in enumerate(row):
            if not v:
                continue

            pygame.draw.rect(
                screen, color,
                (x * cell_w, y * cell_h, cell_w, cell_h)
            )

            mx = (MAZE_WIDTH * 2 - x - 1) * cell_w
            pygame.draw.rect(
                screen, color,
                (mx, y * cell_h, cell_w, cell_h)
            )