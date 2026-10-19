import pygame
import math
import random

# Global variables for animation and optimization
rotation_x = 0.0
rotation_y = 0.0
highlighted_cubes = []
frame_count = 0
audio_history = []  # For smoother audio processing
color_cache = {}  # Cache computed colors to reduce calculations

class HighlightedCube:
    def __init__(self, x, y, z, color, lifetime=90):  # Increased lifetime
        self.x = x
        self.y = y 
        self.z = z
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.pulse_phase = random.random() * math.pi * 2  # For pulsing effect

def setup(screen, eyesy):
    """Initialize the mode - called once when mode loads"""
    global rotation_x, rotation_y, highlighted_cubes, audio_history, color_cache
    rotation_x = 0.0
    rotation_y = 0.0
    highlighted_cubes = []
    audio_history = []
    color_cache = {}

def smooth_audio_level(eyesy, window_size=5):
    """Calculate smoothed audio level to reduce jitter"""
    global audio_history
    
    current_audio = abs(eyesy.audio_in[-1]) if eyesy.audio_in else 0
    audio_normalized = current_audio / 32768.0
    
    # Maintain rolling average
    audio_history.append(audio_normalized)
    if len(audio_history) > window_size:
        audio_history.pop(0)
    
    return sum(audio_history) / len(audio_history)

def enhanced_color_harmony(base_color, cube_position, time_factor):
    """Generate more sophisticated color variations"""
    r, g, b = base_color
    x, y, z = cube_position
    
    # Create color variation based on position and time
    position_hash = (x * 7 + y * 13 + z * 17) % 360
    hue_shift = (position_hash + time_factor * 50) % 360
    
    # Convert to HSV-like manipulation for better color harmony
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    
    if max_val == min_val:  # Grayscale
        return base_color
    
    # Apply hue shift with position-based variation
    shift_factor = math.sin(math.radians(hue_shift)) * 0.3
    
    if r >= g and r >= b:  # Red dominant
        new_color = (
            max(50, min(255, int(r + shift_factor * 100))),
            max(50, min(255, int(g + shift_factor * 150))),
            max(50, min(255, int(b + shift_factor * 80)))
        )
    elif g >= r and g >= b:  # Green dominant
        new_color = (
            max(50, min(255, int(r + shift_factor * 80))),
            max(50, min(255, int(g + shift_factor * 100))),
            max(50, min(255, int(b + shift_factor * 150)))
        )
    else:  # Blue dominant
        new_color = (
            max(50, min(255, int(r + shift_factor * 150))),
            max(50, min(255, int(g + shift_factor * 80))),
            max(50, min(255, int(b + shift_factor * 100)))
        )
    
    return new_color

def calculate_cube_brightness(center_distance, audio_level, layer_fade, depth_scale):
    """Optimized brightness calculation with better audio response"""
    # Improved audio brightness spread with exponential falloff
    audio_brightness_range = audio_level * 5.0 + 1.0  # Always some range
    audio_brightness_factor = math.exp(-max(0, center_distance - audio_brightness_range) / 2.0)
    audio_brightness_factor = max(0.15, min(1.0, audio_brightness_factor))
    
    # Combine all factors with better weighting
    min_brightness = 0.1
    brightness = min_brightness + (depth_scale * layer_fade * audio_brightness_factor * (1.0 - min_brightness))
    
    return brightness

def draw(screen, eyesy):
    """Main drawing function - called every frame"""
    global rotation_x, rotation_y, highlighted_cubes, frame_count, color_cache
    
    frame_count += 1
    time_factor = frame_count * 0.1  # For time-based effects
    
    # Improved audio processing
    audio_level = smooth_audio_level(eyesy)
    
    # Enhanced trigger-based cube highlighting with multiple cubes
    if eyesy.trig:
        # Highlight multiple cubes for more dramatic effect
        num_highlights = random.randint(2, 4)
        max_coord = int(min(7, max(3, eyesy.knob3 * 14))) if eyesy.knob3 <= 0.5 else 3
        
        for _ in range(num_highlights):
            highlight_x = random.randint(-max_coord, max_coord)
            highlight_y = random.randint(-max_coord, max_coord) 
            highlight_z = random.randint(-max_coord, max_coord)
            
            # Enhanced color harmony
            base_color = eyesy.color_picker(eyesy.knob4)
            highlight_color = enhanced_color_harmony(base_color, (highlight_x, highlight_y, highlight_z), time_factor)
            
            # Add new highlighted cube with varied lifetimes
            lifetime = random.randint(60, 120)
            highlighted_cubes.append(HighlightedCube(highlight_x, highlight_y, highlight_z, highlight_color, lifetime))
    
    # Update highlighted cubes with pulsing effect
    highlighted_cubes = [cube for cube in highlighted_cubes if cube.lifetime > 0]
    for cube in highlighted_cubes:
        cube.lifetime -= 1
        cube.pulse_phase += 0.2  # Pulse speed
    
    # Get screen center
    center_x = eyesy.xres / 2
    center_y = eyesy.yres / 2
    
    # Stable background color - no audio reactivity to prevent flashing
    bg_color = eyesy.color_picker_bg(eyesy.knob5)
    screen.fill(bg_color)
    
    # Get wireframe color
    wire_color = eyesy.color_picker(eyesy.knob4)
    
    # Enhanced rotation controls with momentum
    base_speed = 0.08
    x_speed = (eyesy.knob1 - 0.5) * base_speed
    y_speed = (eyesy.knob2 - 0.5) * base_speed
    
    # Add slight audio-reactive rotation variation
    audio_rotation_mod = audio_level * 0.02
    x_speed += math.sin(time_factor * 0.1) * audio_rotation_mod
    y_speed += math.cos(time_factor * 0.1) * audio_rotation_mod
    
    # Improved knob 3 control with better transitions
    if eyesy.knob3 <= 0.5:
        density_factor = eyesy.knob3 * 2.0
        matrix_size = 7
        # Smoother density threshold with exponential curve
        density_threshold = 2.5 + (density_factor ** 1.5) * 4.5
        perspective_distance = 700
    else:
        matrix_size = 7
        density_threshold = 7.0
        zoom_factor = (eyesy.knob3 - 0.5) * 2.0
        # Smoother zoom curve
        perspective_distance = 300 + (zoom_factor ** 0.7) * 900
    
    # Update rotation angles
    rotation_x += x_speed
    rotation_y += y_speed
    
    # Cube geometry (unchanged - works well)
    vertices = [
        [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
        [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]
    ]
    
    edges = [
        [0, 1], [1, 2], [2, 3], [3, 0],  # Back face
        [4, 5], [5, 6], [6, 7], [7, 4],  # Front face
        [0, 4], [1, 5], [2, 6], [3, 7]   # Connecting edges
    ]
    
    # Dynamic base size with audio reactivity
    base_size = 45 + (audio_level * 15)  # Size responds to audio
    spacing = base_size * 3.2
    
    # Pre-calculate trigonometric values for performance
    cos_x, sin_x = math.cos(rotation_x), math.sin(rotation_x)
    cos_y, sin_y = math.cos(rotation_y), math.sin(rotation_y)
    
    # Draw matrix with optimizations
    cubes_drawn = 0
    max_cubes = 200  # Performance limit
    
    for ix in range(matrix_size):
        for iy in range(matrix_size):
            for iz in range(matrix_size):
                if cubes_drawn >= max_cubes:
                    break
                    
                # Distance-based culling for performance
                cube_index_x = abs(ix - matrix_size//2)
                cube_index_y = abs(iy - matrix_size//2)
                cube_index_z = abs(iz - matrix_size//2)
                max_cube_distance = max(cube_index_x, cube_index_y, cube_index_z)
                
                # Enhanced smooth density control
                cube_layer = max_cube_distance
                fade_start = density_threshold - 2.0  # Longer fade distance
                
                if cube_layer < fade_start:
                    layer_fade = 1.0
                elif cube_layer > density_threshold:
                    layer_fade = 0.0
                else:
                    # Smoother fade curve
                    fade_progress = (cube_layer - fade_start) / 2.0
                    layer_fade = 1.0 - (fade_progress ** 0.7)  # Curved fade
                
                if layer_fade <= 0.02:
                    continue
                
                cubes_drawn += 1
                
                # Position calculations
                offset_x = (ix - matrix_size//2) * spacing
                offset_y = (iy - matrix_size//2) * spacing
                offset_z = (iz - matrix_size//2) * spacing
                
                # Enhanced distance calculations
                center_distance = math.sqrt(
                    cube_index_x**2 + cube_index_y**2 + cube_index_z**2
                )
                distance_from_origin = math.sqrt(offset_x**2 + offset_y**2 + offset_z**2)
                
                # Better depth scaling
                depth_scale = max(0.2, 1.0 - (distance_from_origin / (spacing * 5)))
                cube_size = base_size * depth_scale
                
                # Check for highlighting with pulsing effect
                highlight_color = None
                highlight_intensity = 0.0
                cube_pos = (ix - matrix_size//2, iy - matrix_size//2, iz - matrix_size//2)
                
                for highlighted_cube in highlighted_cubes:
                    if (highlighted_cube.x == cube_pos[0] and 
                        highlighted_cube.y == cube_pos[1] and 
                        highlighted_cube.z == cube_pos[2]):
                        highlight_color = highlighted_cube.color
                        base_fade = highlighted_cube.lifetime / highlighted_cube.max_lifetime
                        # Add pulsing effect
                        pulse = (math.sin(highlighted_cube.pulse_phase) + 1.0) * 0.5
                        highlight_intensity = base_fade * (0.6 + 0.4 * pulse)  # Pulse between 60% and 100%
                        break
                
                # Enhanced color calculation
                brightness = calculate_cube_brightness(center_distance, audio_level, layer_fade, depth_scale)
                
                if highlight_color and highlight_intensity > 0:
                    # Enhanced highlight blending
                    blend_factor = highlight_intensity * 0.9
                    final_color = tuple(
                        int(wire_color[i] * (1.0 - blend_factor) + highlight_color[i] * blend_factor)
                        for i in range(3)
                    )
                    fade_color = tuple(
                        max(15, min(255, int(final_color[i] * brightness)))
                        for i in range(3)
                    )
                else:
                    # Add subtle color variation based on position
                    color_key = (ix, iy, iz, int(time_factor / 10))  # Cache key
                    if color_key not in color_cache:
                        position_variation = math.sin(ix * 0.5) * math.cos(iy * 0.3) * math.sin(iz * 0.4)
                        color_mod = 1.0 + (position_variation * 0.1)  # Subtle variation
                        color_cache[color_key] = tuple(
                            max(15, min(255, int(wire_color[i] * color_mod * brightness)))
                            for i in range(3)
                        )
                    fade_color = color_cache[color_key]
                
                # Transform vertices (optimized)
                projected_vertices = []
                for vertex in vertices:
                    x, y, z = vertex
                    
                    # Scale and translate
                    x = x * cube_size + offset_x
                    y = y * cube_size + offset_y
                    z = z * cube_size + offset_z
                    
                    # Apply rotations (using pre-calculated trig values)
                    y_rot = y * cos_x - z * sin_x
                    z_rot = y * sin_x + z * cos_x
                    y, z = y_rot, z_rot
                    
                    x_rot = x * cos_y + z * sin_y
                    z_rot = -x * sin_y + z * cos_y
                    x, z = x_rot, z_rot
                    
                    # Perspective projection with bounds checking
                    if z + perspective_distance > 1:  # Avoid division issues
                        screen_x = (x * perspective_distance) / (z + perspective_distance) + center_x
                        screen_y = (y * perspective_distance) / (z + perspective_distance) + center_y
                    else:
                        screen_x, screen_y = center_x, center_y
                        
                    projected_vertices.append((int(screen_x), int(screen_y)))
                
                # Enhanced line drawing with adaptive thickness
                base_line_width = max(1, int(3 * depth_scale * layer_fade))
                if highlight_intensity > 0:
                    line_width = max(base_line_width, int(base_line_width * (1.5 + highlight_intensity)))
                else:
                    line_width = base_line_width
                
                # Draw edges with better culling
                margin = 200
                for edge in edges:
                    start_vertex = projected_vertices[edge[0]]
                    end_vertex = projected_vertices[edge[1]]
                    
                    # Enhanced bounds checking
                    if ((-margin <= start_vertex[0] <= eyesy.xres + margin and 
                         -margin <= start_vertex[1] <= eyesy.yres + margin) or
                        (-margin <= end_vertex[0] <= eyesy.xres + margin and 
                         -margin <= end_vertex[1] <= eyesy.yres + margin)):
                        
                        pygame.draw.line(screen, fade_color, start_vertex, end_vertex, line_width)
    
    # Note: Removed trigger flash effect to keep background stable
    # The highlighted cubes and their pulsing provides enough visual feedback
    
    # Clean up color cache periodically to prevent memory growth
    if frame_count % 300 == 0:  # Every 5 seconds at 60fps
        color_cache.clear()