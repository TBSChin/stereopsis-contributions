import pygame
import math
import random
import os

NUM_PLANETS = 9
STAR_COUNT = 300
stars = []
planets = []
ufo = {}
ufo_trail = []
ufo_image = None
rockets = []
rocket_img = None

ufo2 = {}
ufo2_image = None
ufo1_alive = True
ufo2_alive = True
ufo1_respawn_timer = 0
ufo2_respawn_timer = 0
explosions = []

def draw_explosion(screen, x, y, frame):
    radius = 5 + frame * 2
    r = 200 + random.randint(0, 55)
    g = 50 + random.randint(0, 205 - frame*5 if frame < 20 else 0)
    b = random.randint(0, 50)
    color = (r, g, b)
    pygame.draw.circle(screen, color, (int(x), int(y)), radius)

def setup(screen, eyesy):
    global stars, planets, ufo, ufo_trail, ufo_image, rocket_img, rockets
    global ufo2, ufo2_image, ufo1_alive, ufo2_alive, ufo1_respawn_timer, ufo2_respawn_timer, explosions

    # Load UFO1 image
    try:
        ufo_path = os.path.join(eyesy.mode_root, "images", "ufo.png")
        ufo_img = pygame.image.load(ufo_path).convert_alpha()
        ufo_image = pygame.transform.smoothscale(ufo_img, (33, 24))
    except Exception as e:
        print("UFO image failed to launch:", e)
        ufo_image = None

    # Load rocket image
    try:
        rocket_path = os.path.join(eyesy.mode_root, "images", "rocket.png")
        rocket_raw = pygame.image.load(rocket_path).convert_alpha()
        rocket_img = pygame.transform.rotate(pygame.transform.smoothscale(rocket_raw, (17, 9)), 0)
    except Exception as e:
        print("Rocket image failed to launch:", e)

    # Load UFO2 image
    try:
        ufo2_path = os.path.join(eyesy.mode_root, "images", "ufo2.png")
        ufo2_raw = pygame.image.load(ufo2_path).convert_alpha()
        ufo2_image = pygame.transform.smoothscale(ufo2_raw, (33, 24))
    except Exception as e:
        print("UFO2 image failed to launch:", e)
        ufo2_image = None

    # Starfield
    stars.clear()
    stars.extend([
        {
            "x": random.uniform(-eyesy.xres, eyesy.xres),
            "y": random.uniform(-eyesy.yres, eyesy.yres),
            "z": random.uniform(1, eyesy.xres)
        }
        for _ in range(STAR_COUNT)
    ])

    # Planets
    planets.clear()
    for i in range(NUM_PLANETS):
        base_size = random.randint(2, 19)
        base_radius = 44 + i * 70 + base_size * 2 + random.uniform(-25, 5)
        moon_count = random.randint(0, max(1, base_size // 5))
        has_moon = moon_count > 0
        moons = []
        for m in range(moon_count):
            moons.append({
                "orbit_offset": random.uniform(-3, 3),
                "size": random.randint(2, max(4, base_size // 5)),
                "color": [random.randint(180, 255) for _ in range(3)]
            })
        planets.append({
            "angle": random.uniform(0, 2 * math.pi),
            "base_radius": base_radius,
            "speed": 0.008 + random.uniform(0.005, 0.02),
            "base_size": base_size,
            "color_offset": random.random(),
            "has_moon": has_moon,
            "moon_count": moon_count,
            "moons": moons,
            "moon_offset": random.uniform(0, 2 * math.pi),
            "radioactive": random.random() < 0.5,
            "glow_scale": random.uniform(1.05, 1.25),
            "glow_color": [random.randint(100, 255) for _ in range(3)],
            "glow_timer": random.randint(100, 300),
            "glow_last_time": 0,
            "has_ring": False,
            "ring_angle": None,
            "ring_color": (200, 200, 200)
        })

    sorted_planets = sorted(enumerate(planets), key=lambda p: p[1]["base_radius"], reverse=True)
    ring_candidates = sorted_planets[:5]
    ringed_indices = random.sample(ring_candidates, k=random.randint(1, 3))

    for index, _ in ringed_indices:
        planet = planets[index]
        planet["has_ring"] = True
        planet["ring_angle"] = random.choice(["side", "perspective"])
        hue = (planet["color_offset"] + 0.05) % 1.0
        planet["ring_color"] = eyesy.color_picker(hue)

    ufo.clear()
    ufo.update({
        "from_idx": 0,
        "to_idx": 1,
        "progress": 0.0,
        "speed": 0.005,
        "color_phase": 0
    })
    ufo_trail.clear()

    ufo2 = {
        "pos": [random.randint(100, 1180), random.randint(100, 620)],
        "cooldown": 0
    }

    ufo1_alive = True
    ufo2_alive = True
    ufo1_respawn_timer = 0
    ufo2_respawn_timer = 0
    explosions.clear()


def draw(screen, eyesy):
    global ufo1_alive, ufo2_alive, ufo1_respawn_timer, ufo2_respawn_timer

    cx, cy = eyesy.xres // 2, eyesy.yres // 2
    eyesy.color_picker_bg(eyesy.knob5)

    star_speed = int(eyesy.knob5 * 10) + 1
    for star in stars:
        star["z"] -= star_speed
        if star["z"] < 1:
            star["x"] = random.uniform(-eyesy.xres, eyesy.xres)
            star["y"] = random.uniform(-eyesy.yres, eyesy.yres)
            star["z"] = eyesy.xres
        star_x = int(cx + (star["x"] / star["z"]) * eyesy.xres)
        star_y = int(cy + (star["y"] / star["z"]) * eyesy.yres)
        brightness = max(0, 255 - int(star["z"] / eyesy.xres * 255))
        pygame.draw.circle(screen, (brightness, brightness, brightness), (star_x, star_y), 2)

    left = sum(a for i, a in enumerate(eyesy.audio_in) if i % 2 == 0) / 50
    right = sum(a for i, a in enumerate(eyesy.audio_in) if i % 2 == 1) / 50
    left_boost = max(0, min(abs(left) / 32768.0, 1)) * 50
    right_boost = max(0, min(abs(right) / 32768.0, 1)) * 50

    t = pygame.time.get_ticks() / 1000.0
    lfo = (math.sin(t * 1.5) + 1) / 2
    audio_amp = sum(abs(a) for a in eyesy.audio_in) / len(eyesy.audio_in)
    audio_norm = min(audio_amp / 32768.0, 1.0)
    sun_hue = (lfo * 0.4 + audio_norm * 0.6) % 1.0
    sun_color = eyesy.color_picker(sun_hue)
    sun_base = 12 + int(eyesy.knob1 * 16)

    for i in range(5, 0, -1):
        flicker = 1.0 + random.uniform(-0.05, 0.05)  # subtle brightness flicker
        radius = int(sun_base + i * 12 + audio_norm * 50)
        glow_color = tuple(min(255, int(c * (1.0 - i * 0.1) * flicker)) for c in sun_color)
        pygame.draw.circle(screen, glow_color, (cx, cy), radius)

    # Bright center
    core_flicker = 1.0 + random.uniform(0, 0.1)
    core_color = tuple(min(255, int(c * core_flicker)) for c in sun_color)
    pygame.draw.circle(screen, core_color, (cx, cy), sun_base)

    planet_positions = []
    for i, p in enumerate(planets):
        orbit = p["base_radius"] + eyesy.knob1 * 100
        p["angle"] += p["speed"] + eyesy.knob2 * 0.02
        x = int(cx + orbit * math.cos(p["angle"]))
        y = int(cy + orbit * math.sin(p["angle"]))

        audio_boost = left_boost if i % 2 == 0 else right_boost
        wobble = (math.sin(p["angle"] * 3 + i) + 1) * 10
        size = int(p["base_size"] + audio_boost + wobble + eyesy.knob3 * 20)
        color = eyesy.color_picker((eyesy.knob4 + p["color_offset"]) % 1.0)

        if p.get("has_ring"):
            ring_color = p.get("ring_color", (200, 200, 200))
            if p["ring_angle"] == "side":
                pygame.draw.line(screen, ring_color, (x - size * 2, y), (x + size * 2, y), 3)
            else:
                pygame.draw.ellipse(screen, ring_color,
                    pygame.Rect(x - size * 2, y - int(size * 0.6), size * 4, int(size * 1.2)), 3)

        if p["radioactive"]:
            now = pygame.time.get_ticks()
            if now - p["glow_last_time"] > p["glow_timer"]:
                p["glow_color"] = [random.randint(100, 255) for _ in range(3)]
                p["glow_timer"] = random.randint(100, 300)
                p["glow_last_time"] = now
            pygame.draw.circle(screen, p["glow_color"], (x, y), int(size * p["glow_scale"]))
        pygame.draw.circle(screen, color, (x, y), size)

        if p["has_moon"]:
            for idx, moon in enumerate(p["moons"]):
                moon_orbit = size + 10 + idx * 6 + moon["orbit_offset"]
                moon_angle = p["angle"] + p["moon_offset"] + idx
                mx = int(x + moon_orbit * math.cos(moon_angle * 2))
                my = int(y + moon_orbit * math.sin(moon_angle * 2))
                pygame.draw.circle(screen, moon["color"], (mx, my), moon["size"])

        planet_positions.append((x, y))

    # === UFO1 movement and status ===
    if not ufo1_alive:
        ufo1_respawn_timer -= 1
        if ufo1_respawn_timer <= 0:
            ufo1_alive = True

    if not ufo2_alive:
        ufo2_respawn_timer -= 1
        if ufo2_respawn_timer <= 0:
            ufo2_alive = True

    # Update UFO1 (planet to planet)
    if ufo1_alive:
        if ufo["progress"] >= 1.0:
            ufo["from_idx"] = ufo["to_idx"]
            ufo["to_idx"] = (ufo["to_idx"] + 1) % len(planets)
            ufo["progress"] = 0.0

        fx, fy = planet_positions[ufo["from_idx"]]
        tx, ty = planet_positions[ufo["to_idx"]]
        ufo["progress"] += ufo["speed"] + 0.001 * (left_boost + right_boost)

        ux = int(fx + (tx - fx) * ufo["progress"])
        uy = int(fy + (ty - fy) * ufo["progress"])
    else:
        ux, uy = -100, -100  # offscreen

    # === UFO2 follows UFO1 ===
    if ufo2_alive:
        u2x, u2y = ufo2["pos"]
        dx = ux - u2x
        dy = uy - u2y
        dist = math.hypot(dx, dy)
        if dist > 1:
            ufo2["pos"][0] += dx / dist * 3.3
            ufo2["pos"][1] += dy / dist * 2.6
        # fire lightning randomly
        if ufo2.get("cooldown", 0) <= 0 and random.random() < 0.01:
            ufo2["cooldown"] = 40
            ufo2["target_pos"] = (ux, uy)
        else:
            ufo2["cooldown"] = max(0, ufo2["cooldown"] - 1)

        if "target_pos" in ufo2:
            x1, y1 = int(ufo2["pos"][0]), int(ufo2["pos"][1])
            x2, y2 = int(ufo2["target_pos"][0]), int(ufo2["target_pos"][1])
            for i in range(5):
                offset = random.randint(-5, 5)
                r = 100 + random.randint(0, 155)
                g = 200 + random.randint(0, 55)
                b = 255
                color = (r, g, b)
                width = 2 if i < 3 else 1  # thinner lines for glow
                pygame.draw.line(screen, color, (x1 + offset, y1), (x2 + offset, y2), width)

            if random.random() < 0.1:
                del ufo2["target_pos"]

            # check if lightning hit UFO1
            if ufo1_alive and math.hypot(ux - x1, uy - y1) < 30:
                ufo1_alive = False
                ufo1_respawn_timer = 120
                explosions.append({"pos": (ux, uy), "timer": 15})

    # === UFO1 trail ===
    if ufo1_alive and eyesy.knob4 > 0.001:
        ufo_trail.append((ux, uy, ufo["color_phase"]))
        if len(ufo_trail) > 100:
            ufo_trail.pop(0)

        for i, (tx, ty, phase) in enumerate(ufo_trail):
            fade = int(255 * (i / len(ufo_trail)))
            if eyesy.knob4 >= 0.95:
                hue = (phase + i * 0.03) % 1.0
                color = eyesy.color_picker(hue)
            else:
                hue = (eyesy.knob4 + i * 0.01) % 1.0
                color = eyesy.color_picker(hue)
            faded = tuple(max(0, c - fade) for c in color)
            pygame.draw.circle(screen, faded, (tx, ty), 2)

        ufo["color_phase"] += 0.03 if eyesy.knob4 >= 0.95 else 0.01
    elif ufo1_alive:
        ufo["color_phase"] += 0.01

    # === Rocket Launching ===
    if ufo1_alive and ufo2_alive and random.random() < 0.002:
        dx = ufo2["pos"][0] - ux
        dy = ufo2["pos"][1] - uy
        dist = math.hypot(dx, dy)
        if dist > 0:
            velocity = (dx / dist * 4, dy / dist * 4)
            angle = math.degrees(math.atan2(-dy, dx))
            rockets.append({
                "pos": [ux, uy],
                "vel": velocity,
                "angle": angle,
                "trail": [],
                "lifetime": 300
            })

    # === Rocket Updates ===
    for rocket in rockets[:]:
        rocket["pos"][0] += rocket["vel"][0]
        rocket["pos"][1] += rocket["vel"][1]
        rocket["lifetime"] -= 1

        # update angle
        vx, vy = rocket["vel"]
        rocket["angle"] = math.degrees(math.atan2(-vy, vx))

        # update trail
        rocket["trail"].append(tuple(rocket["pos"]))
        if len(rocket["trail"]) > 10:
            rocket["trail"].pop(0)

        for i, (tx, ty) in enumerate(rocket["trail"]):
            alpha = int(255 * (i / len(rocket["trail"])))
            color = (255, 100, 100)
            fade_color = tuple(max(0, c - alpha) for c in color)
            pygame.draw.circle(screen, fade_color, (int(tx), int(ty)), 2)

        # draw rocket
        if rocket_img:
            rotated = pygame.transform.rotate(rocket_img, rocket["angle"])
            rect = rotated.get_rect(center=(int(rocket["pos"][0]), int(rocket["pos"][1])))
            screen.blit(rotated, rect.topleft)
        else:
            pygame.draw.circle(screen, (255, 0, 0), (int(rocket["pos"][0]), int(rocket["pos"][1])), 3)

        # check if hit ufo2
        if ufo2_alive and math.hypot(rocket["pos"][0] - ufo2["pos"][0],
                                     rocket["pos"][1] - ufo2["pos"][1]) < 20:
            ufo2_alive = False
            ufo2_respawn_timer = 120
            explosions.append({"pos": (ufo2["pos"][0], ufo2["pos"][1]), "timer": 15})
            rockets.remove(rocket)
            continue

        if rocket["lifetime"] <= 0:
            rockets.remove(rocket)

    # === Draw UFOs if alive ===
    if ufo1_alive:
        if ufo_image:
            screen.blit(ufo_image, (ux - 10, uy - 10))
        else:
            pygame.draw.circle(screen, (255, 255, 255), (ux, uy), 4)

    if ufo2_alive:
        if ufo2_image:
            screen.blit(ufo2_image, (int(ufo2["pos"][0]) - 10, int(ufo2["pos"][1]) - 10))
        else:
            pygame.draw.circle(screen, (0, 255, 255), (int(ufo2["pos"][0]), int(ufo2["pos"][1])), 6)

    # === Draw explosions ===
    for e in explosions[:]:
        draw_explosion(screen, *e["pos"], 15 - e["timer"])
        e["timer"] -= 1
        if e["timer"] <= 0:
            explosions.remove(e)
