# Eyesy Mode: Death Disco Dancefloor by TRC
# "This Dance Floor Will Dance You To DEATH!"
#
# Creates an 8x8 grid that can morph into a spiral, with kinetic movement and audio-reactive colors.
# Includes a persistent trail effect that reacts to the audio trigger.
#
# Controls:
# eyesy.knob1: MORPH CONTROL: 0.0 to 0.97 = Manual Grid-to-Spiral. 0.98+ = Audio Amplitude Morph.
# eyesy.knob2: CONTROLS KINETIC ENERGY! Adjusts the intensity of audio-reactive tile movement and size pulsing.
# eyesy.knob3: Controls the intensity and speed of the base sinusoidal wobble (0.0-1.0).
# eyesy.knob4: Controls the Disco Mode activation (0.0 to 0.4 = Off, 0.6 to 1.0 = On).
# eyesy.knob5: Controls the static background color AND the base foreground color hue (H-sweep).

import pygame
import math
import time

# --- Globals and Utility Functions ---

# Standard conversion from HSV to RGB (0-1 range to 0-255 range)
def hsv_to_rgb(h, s, v):
    if s == 0.0: return (v * 255, v * 255, v * 255)
    i = int(h*6.0)
    f = (h*6.0) - i
    p = v*(1.0 - s)
    q = v*(1.0 - s*f)
    t = v*(1.0 - s*(1.0-f))
    
    r, g, b = 0, 0, 0
    i = i % 6
    if i == 0: r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    elif i == 5: r, g, b = v, p, q
    
    return (int(r * 255), int(g * 255), int(b * 255))

# Standard conversion from RGB (0-255 range) to HSV (0-1 range)
def rgb_to_hsv(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    v = max_val
    delta = max_val - min_val
    if max_val == 0: return 0.0, 0.0, 0.0 
    s = delta / max_val
    if delta == 0: h = 0.0 
    elif max_val == r: h = (g - b) / delta
    elif max_val == g: h = 2.0 + (b - r) / delta
    else: h = 4.0 + (r - g) / delta
    h /= 6.0
    if h < 0: h += 1.0
    return h, s, v

# Global state
disco_mode_active = False
trail_surface = None

# --- REQUIRED SETUP FUNCTION ---
def setup(screen, eyesy):
    global trail_surface
    # Create a surface for the trail effect
    trail_surface = pygame.Surface((eyesy.xres, eyesy.yres))
    trail_surface.fill((0, 0, 0))

# --- Core Drawing Functions ---

def draw_grid(screen, grid_start_x, grid_start_y, size, eyesy, audio_level, is_disco_mode, fg_color):
    """Draws the tiles, morphing between grid and spiral based on knob1 or audio amplitude."""
    # Logic for knob1 takeover: If knob is at the very top, audio amplitude drives the morph.
    if eyesy.knob1 > 0.98:
        morph_factor = audio_level
    else:
        morph_factor = eyesy.knob1 

    knob2 = eyesy.knob2 # Kinetic Intensity Control
    knob3 = eyesy.knob3 
    
    wobble_speed_base = 500.0 
    wobble_speed = wobble_speed_base - (wobble_speed_base * 0.9 * knob3)
    animation_time = pygame.time.get_ticks() / wobble_speed

    color_speed_factor = 0.05 + (audio_level * 0.1)
    # Slightly boosted kinetic coefficients for more "deathly" dancing
    kinetic_intensity_pos = knob2 * 0.5 
    kinetic_intensity_size = knob2 * 0.6 

    r, g, b = fg_color[0], fg_color[1], fg_color[2]
    fg_h, fg_s, fg_v = rgb_to_hsv(r, g, b)

    center_x = eyesy.xres / 2
    center_y = eyesy.yres / 2

    for row in range(8):
        for col in range(8):
            index = row * 8 + col
            
            # Grid Pos
            grid_x = grid_start_x + col * size
            grid_y = grid_start_y + row * size
            
            # Spiral Pos
            spiral_radius = size * 0.9 * math.sqrt(index) 
            spiral_theta = index * 2.39996 + (animation_time * 0.1 * knob3)
            spiral_x = center_x + spiral_radius * math.cos(spiral_theta) - (size / 2)
            spiral_y = center_y + spiral_radius * math.sin(spiral_theta) - (size / 2)
            
            # Morph
            base_x = grid_x * (1.0 - morph_factor) + spiral_x * morph_factor
            base_y = grid_y * (1.0 - morph_factor) + spiral_y * morph_factor

            # Wobble & Kinetic
            move_factor = knob3 
            x_wobble = math.sin(animation_time * 0.5 + col * 0.8 + row * 0.3) * (size * 0.05 * move_factor)
            y_wobble = math.cos(animation_time * 0.5 + row * 0.8 + col * 0.3) * (size * 0.05 * move_factor)
            x_kinetic = audio_level * size * kinetic_intensity_pos * math.sin(col * 1.5)
            y_kinetic = audio_level * size * kinetic_intensity_pos * math.cos(row * 1.5)

            final_x = base_x + x_wobble + x_kinetic
            final_y = base_y + y_wobble + y_kinetic

            # Pulse
            pulse_factor = 1.0 + (audio_level * kinetic_intensity_size)
            current_tile_size = size * pulse_factor
            
            # Colors
            if is_disco_mode: 
                hue = (pygame.time.get_ticks() * 0.001 * color_speed_factor + col * 0.1 + row * 0.05) % 1.0
                color = hsv_to_rgb(hue, 0.8, 0.8)
            else: 
                brightness_mult = 1.0 if (row + col) % 2 == 0 else 0.8 
                color = hsv_to_rgb(fg_h, fg_s, fg_v * brightness_mult)

            pygame.draw.rect(screen, color, (
                final_x - (current_tile_size - size) / 2,
                final_y - (current_tile_size - size) / 2,
                current_tile_size, 
                current_tile_size
            ))


def draw(screen, eyesy):
    """Main drawing loop for the visualizer mode."""
    global disco_mode_active, trail_surface
    
    # Calculate audio level 
    audio_level_norm = sum(abs(a) for a in eyesy.audio_in) / (len(eyesy.audio_in) * 32767.0)
    audio_level_norm = max(0.0, min(1.0, audio_level_norm))
    
    # --- Trail Logic ---
    fade_speed = 30 if eyesy.trig else 80
    
    if trail_surface is None or trail_surface.get_width() != eyesy.xres:
        trail_surface = pygame.Surface((eyesy.xres, eyesy.yres))
    
    trail_surface.set_alpha(fade_speed)
    trail_surface.fill((0, 0, 0))
    screen.blit(trail_surface, (0, 0))

    # Controls
    is_disco_mode = eyesy.knob4 >= 0.5 
    fg_color = hsv_to_rgb(eyesy.knob5, 0.9, 0.9)

    # --- Grid/Spiral Drawing ---
    grid_size = min(eyesy.xres, eyesy.yres)
    tile_size = grid_size / 8
    grid_x = (eyesy.xres - grid_size) / 2
    grid_y = (eyesy.yres - grid_size) / 2

    draw_grid(screen, grid_x, grid_y, tile_size, eyesy, audio_level_norm, is_disco_mode, fg_color)