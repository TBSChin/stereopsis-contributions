import pygame
import math

# Global variables
camera_z = 0.0
segments = []
tunnel_path = []  # Track tunnel center positions for path variation
spin_rotation = 0.0  # Track current spin rotation
flash_fade = 0.0  # Track flash fade amount

def setup(screen, eyesy):
    """Initialize the mode - called once when mode loads"""
    global camera_z, segments, tunnel_path, spin_rotation, flash_fade
    camera_z = 0.0
    segments = []
    tunnel_path = []
    spin_rotation = 0.0
    flash_fade = 0.0
    
    # Create initial segments with path variation
    for i in range(15):  # More segments since they're shorter
        z_pos = i * 100  # Reduced from 200 to 100 (shorter segments)
        # Create gentle curves in the tunnel path
        center_x = math.sin(i * 0.3) * 100
        center_y = math.cos(i * 0.2) * 80
        segments.append(z_pos)
        tunnel_path.append((center_x, center_y))

def project_3d_to_2d(x, y, z, camera_z, screen_center_x, screen_center_y):
    """Simple 3D to 2D projection"""
    rel_z = z - camera_z
    
    if rel_z <= 10:  # Too close or behind camera
        return None
    
    # Simple perspective projection
    distance = 300
    screen_x = int((x * distance) / rel_z + screen_center_x)
    screen_y = int((y * distance) / rel_z + screen_center_y)
    
    return (screen_x, screen_y)

def draw_ring(screen, z_pos, sides, camera_z, screen_center_x, screen_center_y, color, center_offset_x=0, center_offset_y=0, flash_boost=0, spin_rotation=0):
    """Draw a single ring at z position with center offset, flash boost, and spin rotation"""
    radius = 150
    points = []
    
    # Apply flash boost to color
    if flash_boost > 0:
        boosted_color = (
            min(255, color[0] + flash_boost),
            min(255, color[1] + flash_boost),
            min(255, color[2] + flash_boost)
        )
    else:
        boosted_color = color
    
    # Calculate ring vertices with center offset and spin rotation
    for i in range(sides):
        angle = (i * 2 * math.pi) / sides + spin_rotation
        x = math.cos(angle) * radius + center_offset_x
        y = math.sin(angle) * radius + center_offset_y
        
        # Project to 2D
        projected = project_3d_to_2d(x, y, z_pos, camera_z, screen_center_x, screen_center_y)
        if projected:
            points.append(projected)
    
    # Draw the ring
    if len(points) >= 3:
        for i in range(len(points)):
            next_i = (i + 1) % len(points)
            pygame.draw.line(screen, boosted_color, points[i], points[next_i], 2 if flash_boost > 0 else 1)
    
    return points  # Return points for connecting lines

def draw_connecting_lines(screen, points1, points2, color, flash_boost=0):
    """Draw lines connecting two rings with optional flash boost"""
    if points1 and points2 and len(points1) == len(points2):
        # Apply flash boost to color
        if flash_boost > 0:
            boosted_color = (
                min(255, color[0] + flash_boost),
                min(255, color[1] + flash_boost),
                min(255, color[2] + flash_boost)
            )
            line_width = 2
        else:
            boosted_color = color
            line_width = 1
            
        for i in range(len(points1)):
            pygame.draw.line(screen, boosted_color, points1[i], points2[i], line_width)

def draw(screen, eyesy):
    """Main drawing function - called every frame"""
    global camera_z, segments, tunnel_path, spin_rotation, flash_fade
    
    # Set background
    eyesy.color_picker_bg(eyesy.knob5)
    
    # Get wireframe color
    wire_color = eyesy.color_picker(eyesy.knob4)
    
    # Get screen center
    screen_center_x = eyesy.xres / 2
    screen_center_y = eyesy.yres / 2
    
    # Get number of sides from knob 1
    sides = max(3, min(12, int(eyesy.knob1 * 10) + 3))
    
    # Calculate spin from knob 3 (bipolar: 0=left spin, 0.5=no spin, 1=right spin)
    spin_amount = (eyesy.knob3 - 0.5) * 0.15  # -0.075 to +0.075 radians per frame
    spin_rotation += spin_amount
    
    # Move camera forward based on knob 2 (speed control)
    speed = 1.0 + (eyesy.knob2 * 8.0)  # 1.0 to 9.0 units per frame
    camera_z += speed
    
    # Handle flash fade with smooth decay
    if eyesy.trig:
        flash_fade = 1.0  # Set to full flash
    else:
        flash_fade *= 0.85  # Fade out smoothly (85% each frame)
        if flash_fade < 0.05:  # Stop very small values
            flash_fade = 0.0
    
    # Add new segments with path variation as camera moves
    while len(segments) < 15 or segments[-1] < camera_z + 1000:  # More segments to maintain
        if segments:
            new_z = segments[-1] + 100  # Reduced from 200 to 100 (shorter segments)
            # Create path variation using segment index
            segment_index = len(segments)
            center_x = math.sin(segment_index * 0.3) * 100
            center_y = math.cos(segment_index * 0.2) * 80
        else:
            new_z = camera_z + 100  # Reduced from 200 to 100
            center_x = 0
            center_y = 0
        
        segments.append(new_z)
        tunnel_path.append((center_x, center_y))
    
    # Remove old segments and corresponding path points (keep them longer)
    while segments and segments[0] < camera_z - 500:  # Increased from -200 to -500
        segments.pop(0)
        if tunnel_path:
            tunnel_path.pop(0)
    
    # Calculate smooth flash boost based on fade amount
    flash_boost = int(flash_fade * 100)  # 0 to 100 based on fade
    
    # Draw rings and connecting lines
    previous_points = None
    for i, z_pos in enumerate(segments):
        if z_pos > camera_z and i < len(tunnel_path):  # Only draw segments ahead
            # Distance-based color fading
            distance = z_pos - camera_z
            fade = max(0.2, 1.0 - (distance / 800))
            
            faded_color = (
                int(wire_color[0] * fade),
                int(wire_color[1] * fade),
                int(wire_color[2] * fade)
            )
            
            # Get path offset for this segment
            center_x, center_y = tunnel_path[i]
            
            # Draw the ring and get its points (with flash boost and spin rotation)
            current_points = draw_ring(screen, z_pos, sides, camera_z, 
                                     screen_center_x, screen_center_y, faded_color, 
                                     center_x, center_y, flash_boost, spin_rotation)
            
            # Draw connecting lines to previous ring (with flash boost if triggered)
            if previous_points and current_points:
                draw_connecting_lines(screen, previous_points, current_points, faded_color, flash_boost)
            
            previous_points = current_points