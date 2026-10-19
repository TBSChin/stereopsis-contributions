# This is what happens when you find a stranger in the Alps!
#\____________   __________________________________________/                     
#             \ |      @@@@@@*@@,@@@@@@@@*                                   
#              \|   @@(%@@@@@##//@@ @@###@@                 
#                  &@@**@@&@@@@@@&@.@@@/@ @.                
#                  (@#                   * &                
#                 .@@                     *@@                
#                 %/  @@@@@@@/   @@@@@@@, @#                
#                 ./ @@@@@@@@@  @@@@@@@@@@ @                
#                    @@@&&%%@    @@@@@@@@@                  
#                    /@...@        @ ,,(@                  
#                           @@(,@@                          
#                         @@@@.@@@@@                        
#                        @(        *@                                    
#                  @/  @     (@@.     @   @                 
#                   #@@*     (@@#      #@@                  
#                     @@@( .@@@@@@  .@@@#                   
#                       @@@@@@@@@@@@@@,                     
#                          @@@@@@@@(    
#
#                   ColorThing by TRC 2026
import pygame
import math
import colorsys
'''
CONTROLS:
Knob	Function
1	Geometry resolution
2	Chaos / tearing
3	Rotation + outward spiral
4	Base palette color
5	Palette cycling speed
'''
# Global state
phase = 0.0
env = 0.0
vel = 0.0
last_frame = None
hue_phase = 0.0
spiral_phase = 0.0


def setup(screen, eyesy):
    global phase, env, vel, last_frame, hue_phase, spiral_phase
    phase = 0.0
    env = 0.0
    vel = 0.0
    hue_phase = 0.0
    spiral_phase = 0.0
    last_frame = None


def draw(screen, eyesy):
    global phase, env, vel, last_frame, hue_phase, spiral_phase

    w = int(eyesy.xres)
    h = int(eyesy.yres)
    cx = w // 2
    cy = h // 2
    max_r = min(w, h) * 0.55

    # --- AUDIO ---
    audio = sum(abs(a) for a in eyesy.audio_in) / len(eyesy.audio_in)
    audio_norm = min(audio / 14000.0, 1.0)

    # Spring envelope
    force = audio_norm - env
    vel += force * 0.4
    vel *= 0.85
    env += vel

    # --- CONTROLS ---
    points = int(180 + eyesy.knob1 * 700)
    chaos = eyesy.knob2

    spin = eyesy.knob3 * 0.08          # angular motion
    spiral_rate = eyesy.knob3 * 0.6    # outward drift strength

    # --- PALETTE-RELATIVE COLOR CYCLING (KNOB 5) ---
    base_color = eyesy.color_picker(eyesy.knob4)
    r0, g0, b0 = [c / 255.0 for c in base_color]
    h0, s0, v0 = colorsys.rgb_to_hsv(r0, g0, b0)

    hue_phase += eyesy.knob5 * 0.02 + env * 0.01
    hue = (h0 + hue_phase) % 1.0

    r_c, g_c, b_c = colorsys.hsv_to_rgb(hue, s0, v0)
    color = (int(r_c * 255), int(g_c * 255), int(b_c * 255))

    # --- BACKGROUND ---
    screen.fill((0, 0, 0))

    # --- FEEDBACK (AUDIO-DRIVEN TUNNEL) ---
    if last_frame:
        # Base at neutral (1.0), audio pushes outward
        feedback_scale = 1.0 + (env - 0.5) * 0.08 + eyesy.knob3 * 0.05

        feedback = pygame.transform.scale(
            last_frame,
            (int(w * feedback_scale), int(h * feedback_scale))
        )

        if abs(spin) > 0.001:
            feedback = pygame.transform.rotate(feedback, spin * 20)

        fx = cx - feedback.get_width() // 2
        fy = cy - feedback.get_height() // 2
        screen.blit(feedback, (fx, fy))

    # --- SPIRAL PHYSICS ---
    spiral_phase += spiral_rate * (0.2 + env)

    # --- DRAW GEOMETRY ---
    phase += spin + vel * 0.2
    step = math.tau / points

    prev = None
    for i in range(points + 1):
        a = i * step + phase

        base_r = max_r * (0.2 + 0.8 * env)

        # Outward spiral offset
        spiral = spiral_phase * 0.15 * (i / points)

        tear = (
            math.sin(a * 3 + phase) +
            math.sin(a * 7 - phase * 1.3)
        ) * chaos * max_r * env * 0.12

        ripple = math.sin(a * 12 + phase * 2) * chaos * 40 * env

        r = base_r + spiral + tear + ripple

        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r

        if prev:
            pygame.draw.line(screen, color, prev, (int(x), int(y)), 3)
        prev = (int(x), int(y))

    last_frame = screen.copy()
