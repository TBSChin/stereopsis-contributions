# --- Kaleid-O-Tron, an Eyesy mode by TRC
#
# --- Knob 1: Number of kaleidoscope slices (3 to 24)
#     Knob 2: Rotation speed
#     Knob 3: Overall size / radius
#     Knob 4: Color mode (normal < 1.0, LFO at 1.0)
#     Knob 5: Background color
import pygame
import math

def setup(screen, eyesy):
    eyesy.t = 0
    eyesy.dir = 1


def draw(screen, eyesy):
    eyesy.color_picker_bg(eyesy.knob5)

    # ---- ROTATION SPEED & DIRECTION CONTROL ----
    if eyesy.trig:
        eyesy.dir *= -1

    speed = (eyesy.knob2 ** 2) * 0.2
    eyesy.t += speed * eyesy.dir
    # --------------------------------------------

    x_center = eyesy.xres / 2
    y_center = eyesy.yres / 2

    circles = 20

    # ----------------------------------------------------
    # OPTION C IMPLEMENTED: knob1 controls slice count
    # knob1 = 0.0 → 3 slices
    # knob1 = 1.0 → 24 slices (or whatever you want)
    # ----------------------------------------------------
    min_slices = 3
    max_slices = 24
    slices = int(min_slices + eyesy.knob1 * (max_slices - min_slices))
    if slices < 3:
        slices = 3
    # ----------------------------------------------------

    outer_radius = eyesy.knob3 * (min(eyesy.xres, eyesy.yres) * 1.05)

    # --- Optional audio EMI to push LFO when active ---
    audio_push = abs(eyesy.audio_in[0]) / 40000.0

    for i in range(1, circles):

        ring_pos = (i / circles) * outer_radius
        audio = abs(eyesy.audio_in[i]) / 2000.0
        R = int((audio + 0.15) * (eyesy.knob3 * 20)) + 4
        angle = eyesy.t + i * 0.25

        # ---- COLOR SECTION ----
        if eyesy.knob4 >= 0.999:
            lfo_pos = (eyesy.knob5 + audio_push) % 1.0
            color = eyesy.color_picker_lfo(lfo_pos)
        else:
            color = eyesy.color_picker((eyesy.knob4 + i * 0.05) % 1.0)
        # ------------------------

        for s in range(slices):
            a = angle + (2 * math.pi / slices) * s
            x = int(x_center + math.cos(a) * ring_pos)
            y = int(y_center + math.sin(a) * ring_pos)
            pygame.draw.circle(screen, color, (x, y), R)
