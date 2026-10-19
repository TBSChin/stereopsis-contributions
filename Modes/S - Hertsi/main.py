import pygame
import pygame.gfxdraw
import math
import random

# Global variables to track state
trigger_active = False
trigger_timer = 0
TRIGGER_DURATION = 5  # frames
ripple_time = 0
ripple_active = False
ripple_strength = 0

# Store random parameters for each line
line_params = []
POINT_STEP = 3  # Sample every 3rd pixel for wave points

def _hue_to_rgb(h):
    """Convert hue (0.0-1.0) to RGB tuple at full saturation/value."""
    h6 = (h % 1.0) * 6.0
    x = int(255 * (1.0 - abs(h6 % 2.0 - 1.0)))
    i = int(h6) % 6
    if   i == 0: return (255, x, 0)
    elif i == 1: return (x, 255, 0)
    elif i == 2: return (0, 255, x)
    elif i == 3: return (0, x, 255)
    elif i == 4: return (x, 0, 255)
    else:        return (255, 0, x)


def setup(screen, eyesy):
    global trigger_active, trigger_timer, ripple_time, ripple_active, ripple_strength, line_params
    trigger_active = False
    trigger_timer = 0
    ripple_time = 0
    ripple_active = False
    ripple_strength = 0
    
    # Initialize random parameters for each line
    line_params = []
    for i in range(12):
        line_params.append({
            'frequency_offset': random.uniform(0.8, 1.2),
            'phase_offset': random.uniform(0, 2 * math.pi),
            'thickness_variation': random.uniform(0.9, 1.1)
        })

def draw(screen, eyesy):
    # knob5 controls fg/bg color:
    #   0.0        = white on black
    #   0.05-0.95  = complementary color pairs from the hue wheel
    #   1.0        = black on white
    k5 = eyesy.knob5
    if k5 < 0.05:
        fg_color = (255, 255, 255)
        bg_color = (0, 0, 0)
    elif k5 > 0.95:
        fg_color = (0, 0, 0)
        bg_color = (255, 255, 255)
    else:
        hue = (k5 - 0.05) / 0.9  # remap 0.05-0.95 -> 0.0-1.0
        fg_color = _hue_to_rgb(hue)
        bg_color = _hue_to_rgb(hue + 0.5)

    screen.fill(bg_color)    
    
    # Calculate margins (20% of width/height)
    margin_x = int(0.2 * int(eyesy.xres))
    margin_y = int(0.2 * int(eyesy.yres))
    
    # Calculate line length based on knob1
    # knob1: 0.0 -> 26% width (original minimum), 1.0 -> 100% width
    line_length = int(int(eyesy.xres) * (0.26 + 0.74 * eyesy.knob1))
    
    # Calculate line spacing based on knob2
    # knob2: 0.0 -> 50 pixels (max), 1.0 -> full vertical range utilization (smooth transition)
    min_spacing = 25
    max_spacing = 50
    
    # Calculate original spacing behavior
    inverted_knob2 = 0.9 - eyesy.knob2
    original_spacing = min_spacing + (max_spacing - min_spacing) * inverted_knob2
    
    # Calculate full range spacing behavior
    total_thickness = sum(2 + 2 * i for i in range(12))
    full_range_spacing = (int(eyesy.yres) - total_thickness) // 11
    full_range_spacing = max(1, full_range_spacing)  # Ensure minimum spacing
    
    # Smooth interpolation between both behaviors
    spacing = int(original_spacing * (1 - eyesy.knob2) + full_range_spacing * eyesy.knob2)
    
    # Calculate audio-driven wave parameters
    # Get average audio level from recent samples
    audio_level = abs(sum(eyesy.audio_in) / len(eyesy.audio_in)) / 32768.0
    
    # Handle trigger state and ripple effects
    global trigger_active, trigger_timer, ripple_time, ripple_active, ripple_strength, ripple_random_params
    
    # Initialize ripple random params if not exists
    if 'ripple_random_params' not in globals():
        ripple_random_params = {
            'frequency': 0.02,
            'phase_shift': 0,
            'amplitude_scale': 1.0,
            'propagation_speed': 0.1,
            'waveform_type': 'sine'
        }
    
    # Trigger handling
    if eyesy.trig:
        trigger_active = True
        trigger_timer = TRIGGER_DURATION
        # Create a ripple effect when triggered with random parameters
        ripple_active = True
        ripple_strength = 1.0
        ripple_time = 0
        
        # Store random parameters for this ripple
        ripple_random_params = {
            'frequency': random.uniform(0.01, 0.03),  # Random wave frequency
            'phase_shift': random.uniform(0, 2 * math.pi),  # Random phase shift
            'amplitude_scale': random.uniform(0.8, 1.2),  # Random amplitude variation
            'propagation_speed': random.uniform(0.08, 0.12),  # Random propagation speed
            'waveform_type': random.choice(['sine', 'cosine', 'mixed'])  # Different waveform types
        }
    
    if trigger_active:
        trigger_timer -= 1
        if trigger_timer <= 0:
            trigger_active = False
    
    # Ripple effect handling
    if ripple_active:
        ripple_time += 1
        # Ripple decays over time
        ripple_strength = max(0, 1.0 - (ripple_time / 30.0))  # 30 frame decay
        if ripple_strength <= 0:
            ripple_active = False
    
    # Calculate wave amplitude based on knob3 and audio level
    # Ensure wave doesn't cause line overlap (max amplitude < spacing/2)
    max_wave_height = min(spacing // 2, 15)  # Limit to 15px max or half of spacing
    
    # Base wave amplitude
    if trigger_active:
        base_amplitude = max_wave_height * eyesy.knob3  # Maximum effect when triggered
    else:
        base_amplitude = max_wave_height * eyesy.knob3 * audio_level
    
    wave_amplitude = base_amplitude
    
    # Wave frequency (adjustable)
    wave_frequency = 0.02  # cycles per pixel
    
    # Draw lines with wave effect
    # Smooth transition for starting position
    y_pos = int(margin_y * (1 - eyesy.knob2))  # From margin_y to 0
    
    for i in range(12):  # 12 lines to fit within margins
        thickness = 2 + 2 * i  # 2, 4, 6, ..., 24 pixels
        
        # Calculate start x position
        start_x = (int(eyesy.xres) - line_length) // 2
        
        # Get random parameters for this line
        params = line_params[i] if i < len(line_params) else {'frequency_offset': 1.0, 'phase_offset': 0, 'thickness_variation': 1.0}
        
        # Create wave pattern for this line with natural variations
        # Each line has different frequency, phase, and ripple timing
        base_phase_offset = i * 0.2 + params['phase_offset']
        adjusted_frequency = wave_frequency * params['frequency_offset']
        
        # Add audio-driven frequency variation
        audio_freq_variation = 1.0 + (audio_level * 0.2)  # Up to 20% variation based on audio
        
        # Calculate wave complexity based on knob4
        # 0.0 = simple single wave, 1.0 = complex interference patterns
        complexity = eyesy.knob4
        
        # Generate additional waves for complexity
        wave2_amplitude = 0
        wave3_amplitude = 0
        wave2_phase = 0
        wave3_phase = 0
        
        if complexity > 0.1:  # Start adding second wave
            wave2_amplitude = complexity * 0.5  # 0.0 to 0.5
            wave2_phase = base_phase_offset + math.pi * 0.5  # 90 degree phase shift
            wave2_frequency = adjusted_frequency * 1.5  # Higher frequency harmonic
        
        if complexity > 0.5:  # Add third wave for more complexity
            wave3_amplitude = (complexity - 0.5) * 1.5  # 0.0 to 1.0
            wave3_phase = base_phase_offset + math.pi * 0.3  # Different phase shift
            wave3_frequency = adjusted_frequency * 0.7  # Lower frequency subharmonic
        
        # Ripple parameters (calculated once per line)
        ripple_phase = 0
        ripple_component = 0  # Always initialize
        if ripple_active:
            # Use random parameters for this ripple
            freq = ripple_random_params['frequency']
            phase = ripple_random_params['phase_shift']
            amp_scale = ripple_random_params['amplitude_scale']
            speed = ripple_random_params['propagation_speed']
            waveform = ripple_random_params['waveform_type']
            
            # Ripple propagates outward from center with random speed
            ripple_phase = (ripple_time * speed) + phase - (i * 0.5)
            
            # Add ripple component to wave amplitude for this line
            # Ripple amplitude decreases with line index and has random scaling
            ripple_component = ripple_strength * max_wave_height * 0.5 * amp_scale * (1.0 - (i / 12.0))
        
        # Balanced wave constraint system - preserve knob4 functionality while preventing overlap
        # Let waves be generated at natural amplitudes (don't scale pre-generation)
        line_wave_amplitude = wave_amplitude + ripple_component
        
        # Apply thickness variation based on audio and random factor
        adjusted_thickness = max(1, int(thickness * params['thickness_variation'] * (1.0 + (audio_level * 0.1))))
        
        # Draw the wavy line as a polygon ribbon with anti-aliased edges
        half_t = adjusted_thickness / 2.0
        upper_edge = []
        lower_edge = []
        last_x = start_x + line_length - 1
        for x in range(start_x, start_x + line_length, POINT_STEP):
            rx = x - start_x
            # Calculate base wave offset
            base_wave = math.sin(rx * adjusted_frequency * audio_freq_variation + base_phase_offset)

            # Calculate additional waves for complexity
            wave2 = 0
            wave3 = 0
            if complexity > 0.1:
                wave2 = math.sin(rx * wave2_frequency * audio_freq_variation + wave2_phase) * wave2_amplitude
            if complexity > 0.5:
                wave3 = math.sin(rx * wave3_frequency * audio_freq_variation + wave3_phase) * wave3_amplitude

            # Calculate ripple wave (if active)
            ripple_wave = 0
            if ripple_active:
                waveform = ripple_random_params['waveform_type']
                if waveform == 'sine':
                    ripple_wave = math.sin(rx * freq + ripple_phase)
                elif waveform == 'cosine':
                    ripple_wave = math.cos(rx * freq + ripple_phase)
                else:  # mixed
                    ripple_wave = (math.sin(rx * freq + ripple_phase) +
                                  math.cos(rx * freq * 1.3 + ripple_phase * 1.5)) * 0.5

            # Combine all waves
            total_wave = base_wave + wave2 + wave3 + ripple_wave
            wave_offset = total_wave * line_wave_amplitude

            # Compute center y and ribbon edges
            center_y = y_pos + half_t + wave_offset
            upper_edge.append((x, round(center_y - half_t)))
            lower_edge.append((x, round(center_y + half_t)))

        # Ensure the rightmost pixel is included
        if upper_edge and upper_edge[-1][0] < last_x:
            rx = last_x - start_x
            base_wave = math.sin(rx * adjusted_frequency * audio_freq_variation + base_phase_offset)
            wave2 = 0
            wave3 = 0
            if complexity > 0.1:
                wave2 = math.sin(rx * wave2_frequency * audio_freq_variation + wave2_phase) * wave2_amplitude
            if complexity > 0.5:
                wave3 = math.sin(rx * wave3_frequency * audio_freq_variation + wave3_phase) * wave3_amplitude
            ripple_wave = 0
            if ripple_active:
                waveform = ripple_random_params['waveform_type']
                if waveform == 'sine':
                    ripple_wave = math.sin(rx * freq + ripple_phase)
                elif waveform == 'cosine':
                    ripple_wave = math.cos(rx * freq + ripple_phase)
                else:
                    ripple_wave = (math.sin(rx * freq + ripple_phase) +
                                  math.cos(rx * freq * 1.3 + ripple_phase * 1.5)) * 0.5
            
            total_wave = base_wave + wave2 + wave3 + ripple_wave
            wave_offset = total_wave * line_wave_amplitude

            center_y = y_pos + half_t + wave_offset
            upper_edge.append((last_x, round(center_y - half_t)))
            lower_edge.append((last_x, round(center_y + half_t)))

        # Build closed polygon: upper edge left-to-right, lower edge right-to-left
        if len(upper_edge) >= 2:
            lower_edge.reverse()
            ribbon = upper_edge + lower_edge
            pygame.gfxdraw.filled_polygon(screen, ribbon, fg_color)
            pygame.gfxdraw.aapolygon(screen, ribbon, fg_color)
        
        # Move to next line position
        y_pos += thickness + spacing
        
        # Check if we're exceeding the bottom margin (smooth transition)
        termination_height = int(eyesy.yres) - int(margin_y * (1 - eyesy.knob2))
        if y_pos + thickness > termination_height:
            break