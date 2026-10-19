# Knob	    Function
# Knob 1	Pattern complexity (√x), blended with audio
# Knob 2	Modulo divisor (tiling), blended with audio
# Knob 3	Resolution (32–256), blended with audio
# Knob 4	Color mode:
#        		0.0–0.33 = expressive dual-brightness mono	
#        		0.33–0.66 = 4-color hue palette	
#        		0.66–1.0 = animated color cycling	
# Knob 5	Background color + audio/knob blend amount
import pygame
import math
import colorsys

def setup(screen, eyesy):
    global buffer
    buffer = pygame.Surface((128, 128))

def draw(screen, eyesy):
    # --- Audio Level ---
    raw_audio = [abs(x) for x in eyesy.audio_in]
    audio_level = sum(raw_audio) / len(raw_audio) / 32768.0
    audio_level = min(max(audio_level, 0.0), 1.0)

    # --- Blend knob5: knob/audio interpolation ---
    blend = eyesy.knob5
    k1 = (1 - blend) * eyesy.knob1 + blend * audio_level
    k2 = (1 - blend) * eyesy.knob2 + blend * audio_level
    k3 = (1 - blend) * eyesy.knob3 + blend * audio_level

    # --- Pattern Parameters ---
    xval = 1 + k1 * 9
    sqrtx = math.sqrt(xval)
    modval = int(2 + pow(k2, 0.7) * 10)
    modval = max(2, modval)
    buf_size = int(32 + k3 * 224)
    buffer = pygame.Surface((buf_size, buf_size))

    # --- Background Color ---
    eyesy.color_picker_bg(eyesy.knob5)

    # --- Color Mode Selection via knob4 ---
    color_mode = eyesy.knob4
    palette = []

    if color_mode < 0.33:
        # 🎨 Original monochrome brightness logic
        base_color = eyesy.color_picker(color_mode * 3.0)  # remap 0–0.33 → 0–1
        for total in range(4):
            if total in (0, 1):
                color = tuple(min(255, c + total * 30) for c in base_color)
            else:
                color = (0, 0, 0)
            palette.append(color)

    elif color_mode < 0.66:
        # 🌈 4-Color Hue Palette
        base_hue = ((color_mode - 0.33) / 0.33) % 1.0
        for i in range(4):
            h = (base_hue + i * 0.25) % 1.0
            rgb = colorsys.hsv_to_rgb(h, 1.0, 1.0)
            palette.append(tuple(int(255 * c) for c in rgb))

    else:
        # 🔁 Animated Cycling Palette
        time = pygame.time.get_ticks() * 0.0001
        base_hue = (time + (color_mode - 0.66) * 3) % 1.0
        for i in range(4):
            h = (base_hue + i * 0.2) % 1.0
            rgb = colorsys.hsv_to_rgb(h, 1.0, 1.0)
            palette.append(tuple(int(255 * c) for c in rgb))

    # --- Sequence generation ---
    a = [0] * buf_size
    for i in range(1, buf_size):
        q = int(i * sqrtx) % modval
        a[i] = a[i - 1] + (1 if q == 1 else -1)

    # --- Draw pattern ---
    buffer.fill((0, 0, 0, 0))
    for x in range(buf_size):
        ax = a[x]
        for y in range(buf_size):
            total = (ax + a[y]) % 4
            color = palette[total]
            buffer.set_at((x, y), color)

    # --- Scale & Blit ---
    scaled = pygame.transform.smoothscale(buffer, (int(eyesy.xres), int(eyesy.yres)))
    screen.blit(scaled, (0, 0))
