# Knob 1 (Sun Color): Controls the color of the sun. When turned to its maximum, the sun's color also reacts to the audio input by brightening towards white.
#
# Knob 2 (Grid Color): Controls the color of both the horizontal and vertical perspective lines. When turned to its maximum, the base color for the grid is determined by the audio volume, and it also brightens towards white with louder audio.
#
# Knob 3 (Horizontal Grid Speed): Controls the movement speed of the horizontal perspective lines. When turned to its maximum, the speed is influenced by the audio input.
#
# Knob 4 (Bottom Gradient Color): Controls the color at the bottom of the background gradient.
#
# Knob 5 (Background Color): Controls the overall background color, acting as the "sky" color.
#
import pygame
import math
import random
import sys

# Global variables
stars = []

# Constants for perspective grid
FULL_Z = 15000
FOCAL_LENGTH = 1666

class grid_X_lines:
    def __init__(self, num_lines, vel_z_initial_scale):
        if num_lines <= 1:
            raise ValueError("Number of Lines (num_lines) must be greater than 1")
        self.num_lines = num_lines
        self.vel_z_initial_scale = vel_z_initial_scale
        self.lines_z_positions = []

        self.dz_step = (FULL_Z - FOCAL_LENGTH) / self.num_lines
        for n in range(self.num_lines):
            starting_pos = FULL_Z - (n * self.dz_step)
            self.lines_z_positions.append(starting_pos)
        
        self.lines_z_positions.append(FOCAL_LENGTH)
        self.lines_z_positions.sort(reverse=True)

    def update(self, eyesy_speed_value):
        vel_z = eyesy_speed_value * self.vel_z_initial_scale
        
        num_wrapped_this_frame = 0
        for i in range(len(self.lines_z_positions)):
            self.lines_z_positions[i] -= vel_z
            
            if self.lines_z_positions[i] < FOCAL_LENGTH:
                self.lines_z_positions[i] = FULL_Z + (num_wrapped_this_frame * self.dz_step)
                num_wrapped_this_frame += 1

        self.lines_z_positions.sort(reverse=True)

    def draw(self, color, surface, min_visible_y, screen_height, perspective_origin_y):
        for z_pos in self.lines_z_positions:
            if z_pos <= 0:
                continue 

            projected_y = perspective_origin_y + ((screen_height - perspective_origin_y) * FOCAL_LENGTH / z_pos)
            
            if projected_y >= min_visible_y and projected_y <= screen_height:
                pygame.draw.line(surface, color, (0, int(projected_y)), (int(surface.get_width()), int(projected_y)), 1)


x_lines_grid = None

def interpolate_color(color1, color2, factor):
    r = int(color1[0] * (1 - factor) + color2[0] * factor)
    g = int(color1[1] * (1 - factor) + color2[1] * factor)
    b = int(color1[2] * (1 - factor) + color2[2] * factor)
    return (r, g, b)

def setup(screen, eyesy):
    global stars, x_lines_grid

    stars = []
    horizon_y_for_stars = eyesy.yres / 2 + 50
    for _ in range(50):
        x = random.randint(0, int(eyesy.xres))
        y = random.randint(0, int(horizon_y_for_stars))
        speed_star = random.uniform(0.5, 2.5)
        stars.append((x, y, speed_star))

    x_lines_grid = grid_X_lines(num_lines=40, vel_z_initial_scale=500.0)


def draw(screen, eyesy):
    global stars, x_lines_grid

    bg_color = eyesy.color_picker_bg(eyesy.knob5)
    screen.fill(bg_color)

    audio_data = eyesy.audio_in 
    if not audio_data: 
        normalized_audio = 0
    else:
        avg_abs_audio = sum(abs(val) for val in audio_data) / len(audio_data)
        normalized_audio = avg_abs_audio / 32767.0

    current_knob1_base_color = eyesy.color_picker(eyesy.knob1)
    if eyesy.knob1 >= 0.99: 
        sun_color = interpolate_color(current_knob1_base_color, (255,255,255), normalized_audio)
    else:
        sun_color = current_knob1_base_color

    if eyesy.knob2 >= 0.99: 
        base_grid_color_from_audio = eyesy.color_picker(normalized_audio)
        grid_color = interpolate_color(base_grid_color_from_audio, (255,255,255), normalized_audio)
    else:
        base_grid_color_from_knob = eyesy.color_picker(eyesy.knob2)
        grid_color = base_grid_color_from_knob

    if eyesy.knob3 >= 0.99:
        speed = normalized_audio * 5 + 0.5 
    else:
        speed = eyesy.knob3 * 10 
        
    bottom_gradient_color = eyesy.color_picker(eyesy.knob4)

    cx = eyesy.xres / 2
    cy = eyesy.yres / 2

    visual_horizon_y = cy + 50 
    grid_origin_y = cy + 15 

    gradient_start_y = int(visual_horizon_y) 
    gradient_end_y = int(eyesy.yres) 
    gradient_height = gradient_end_y - gradient_start_y

    top_gradient_color = bg_color 
    
    for y_pixel in range(gradient_start_y, gradient_end_y):
        factor = (y_pixel - gradient_start_y) / float(gradient_height - 1)
        current_color = interpolate_color(top_gradient_color, bottom_gradient_color, factor)
        pygame.draw.line(screen, current_color, (0, y_pixel), (int(eyesy.xres), y_pixel), 1)

    new_stars = [] 
    radius = 175 
    sun_center_x = int(cx)
    sun_center_y = int(cy - 100) # MODIFIED: Sun center Y position

    for (old_x, old_y, old_star_speed) in stars: 
        current_x = old_x
        current_y = old_y + old_star_speed 
        current_star_speed = old_star_speed

        dist_to_sun_sq = (current_x - sun_center_x)**2 + (current_y - sun_center_y)**2
        
        if current_y > visual_horizon_y:
            current_x = random.randint(0, int(eyesy.xres)) 
            current_y = random.randint(0, 10) 
            current_star_speed = random.uniform(0.5, 2.5) 
        
        if current_y < visual_horizon_y and dist_to_sun_sq > (radius * 1.05)**2:
            pygame.draw.circle(screen, (int(255), int(255), int(255)), (int(current_x), int(current_y)), 1)
        
        new_stars.append((current_x, current_y, current_star_speed)) 
    stars = new_stars 

    sun_rect_width = 2 * radius
    sun_rect_height = 2 * radius
    sun_rect_topleft = (sun_center_x - radius, sun_center_y - radius)

    magenta_key = (255, 0, 255) 
    gradient_surf = pygame.Surface((sun_rect_width, sun_rect_height))
    gradient_surf.fill(magenta_key) 

    gradient_top_color = sun_color
    gradient_bottom_color = bg_color 

    for y_pixel_on_surf in range(sun_rect_height):
        y_relative_to_center = y_pixel_on_surf - radius
        if abs(y_relative_to_center) <= radius:
            half_chord_squared = radius**2 - y_relative_to_center**2
            if half_chord_squared >= 0: 
                half_chord = math.sqrt(half_chord_squared)
                x_start_on_surf = int(radius - half_chord)
                x_end_on_surf = int(radius + half_chord)
                lerp_factor_base = y_pixel_on_surf / float(sun_rect_height - 1)
                adjusted_lerp_factor = lerp_factor_base * (1.0 + normalized_audio * 1.5)
                adjusted_lerp_factor = max(0.0, min(1.0, adjusted_lerp_factor))
                current_line_color = interpolate_color(gradient_top_color, gradient_bottom_color, adjusted_lerp_factor)
                pygame.draw.line(gradient_surf, current_line_color, 
                                 (x_start_on_surf, y_pixel_on_surf), 
                                 (x_end_on_surf, y_pixel_on_surf), 1) 

    gradient_surf.set_colorkey(magenta_key)
    screen.blit(gradient_surf, sun_rect_topleft)

    # Bars on Sun matching Background
    extension_amount = 15

    # MODIFIED: Sun bar properties for less clutter
    bars_start_y_on_screen = sun_center_y - radius + (radius * 0.50)
    bars_vertical_span = (sun_center_y + radius) - bars_start_y_on_screen
    num_visible_bars = 9
    initial_bar_thickness = (radius * 0.45) / num_visible_bars * 2

    for i in range(num_visible_bars):
        y_stripe_center = bars_start_y_on_screen + (bars_vertical_span / num_visible_bars) * i
        y_relative_to_sun_center = y_stripe_center - sun_center_y
 
        half_chord_squared = radius**2 - y_relative_to_sun_center**2
        half_chord = math.sqrt(max(0, half_chord_squared))
 
        x_start_on_screen = int(sun_center_x - half_chord - extension_amount) 
        x_end_on_screen = int(sun_center_x + half_chord + extension_amount)   
        
        taper_progress = i / max(1, num_visible_bars - 1)
        current_stripe_thickness = initial_bar_thickness * (1 - taper_progress * 0.9)
        current_stripe_thickness = max(1, int(current_stripe_thickness))

        if current_stripe_thickness > 0:
            pygame.draw.line(screen, bg_color, 
                             (x_start_on_screen, int(y_stripe_center)), 
                             (x_end_on_screen, int(y_stripe_center)), 
                             current_stripe_thickness)

    # Update and Draw Horizontal Grid Lines
    x_lines_grid.update(speed)
    x_lines_grid.draw(grid_color, screen, visual_horizon_y, eyesy.yres, grid_origin_y) 

    # Permanent Horizon Line
    horizon_line_y = int(visual_horizon_y) 
    pygame.draw.line(screen, grid_color, (0, horizon_line_y), (int(eyesy.xres), horizon_line_y), 2) 

    # 180-DEGREE VERTICAL PERSPECTIVE LINES
    origin_x = eyesy.xres / 2
    origin_y = visual_horizon_y

    depth = eyesy.yres - origin_y
    num_v_lines = 30 
    max_half_angle_degrees = 88.9 
    max_half_angle_radians = math.radians(max_half_angle_degrees)
    half_virtual_width = depth * math.tan(max_half_angle_radians)
    x_start_on_bottom = origin_x - half_virtual_width
    x_end_on_bottom = origin_x + half_virtual_width

    for i in range(num_v_lines + 1):
        end_x = x_start_on_bottom + (i / num_v_lines) * (x_end_on_bottom - x_start_on_bottom)
        pygame.draw.line(screen, grid_color, (int(origin_x), int(origin_y)), (int(end_x), eyesy.yres), 1)