"""Native 3D morphs plus compositor-only blends for other Swarm simulations."""
import json
import ctypes
import os
import sys
import time
import pygame

SHARED_3D = frozenset(('Swarm - Tunnel', 'Swarm - Ribbon', 'Swarm - Terrain',
    'Swarm - Terrain Convergence', 'Swarm - Terrain Back to Front',
    'Swarm - Orb', 'Swarm - Nebula', 'Swarm - Cymatics',
    '07A - Swarm - Kaleidoscope 3D', 'Swarm - Kaleidoscope 3D', 'Swarm - Tesseract',
    'Swarm - Icosa Cages', 'Swarm - Torus Knot', 'Swarm - Double Helix',
    'Swarm - Hopf Rings', 'Swarm - 24 Cell', '04I - Swarm - Magnetic Field',
    'Swarm - Dodeca Nest', 'Swarm - Morph Bloom', 'Swarm - Spiral Galaxy'))


class Handoff:
    def __init__(self, display, eyesy, main, root, clock=time.monotonic, getter=None):
        self.display, self.eyesy, self.main, self.root = display, eyesy, main, root
        self.original = display.present
        self.clock = clock
        self.previous = None
        self.previous_size = None
        self.old = None
        self.output = None
        self.started = 0.0
        self.duration = 0.65
        self.events = []
        self.getter = getter
        self.pending_native = None

    def native_state(self):
        lib = self.getter() if self.getter else None
        if lib is None:
            return {}
        values = (ctypes.c_float * 8)()
        lib.sw_debug(values, 8)
        return dict(style=int(values[0]), morph=float(values[1]), morphing=bool(values[2]),
                    transition=int(values[3]), particles=lib.sw_ready())

    def event(self, **values):
        self.events.append(dict(time=time.time(), **values))
        self.events = self.events[-80:]
        try:
            with open(os.path.join(self.root, 'transition-events.json'), 'w') as f:
                json.dump(self.events, f, indent=2)
        except OSError:
            pass
        print('[swarm-handoff] %s' % values, flush=True)

    def present(self, frame, clear=None, osd=None, interval=1):
        name = self.eyesy.mode
        if not getattr(self.main, 'good_frames', 0) or self.eyesy.menu_mode:
            self.previous, self.old = None, None
            return self.original(frame, clear=clear, osd=osd, interval=interval)
        now = self.clock()
        if name != self.previous:
            previous = self.previous
            self.old = None
            self.pending_native = None
            both = previous and 'swarm' in previous.lower() and 'swarm' in name.lower()
            native = both and previous in SHARED_3D and name in SHARED_3D
            if both and not native:
                snapshot = pygame.Surface(self.previous_size or frame.get_size(), 0, 32)
                if self.display.snapshot(snapshot) == 0:
                    if snapshot.get_size() != frame.get_size():
                        snapshot = pygame.transform.smoothscale(snapshot, frame.get_size())
                    self.old = snapshot
                    self.output = pygame.Surface(frame.get_size(), 0, 32)
                    self.started = now
                    self.event(kind='blend-start', source=previous, target=name)
            elif native:
                self.event(kind='native-morph', source=previous, target=name, **self.native_state())
                self.pending_native = name
            self.previous = name
        self.previous_size = frame.get_size()
        if self.pending_native:
            state = self.native_state()
            if state and not state['morphing']:
                self.event(kind='native-complete', target=self.pending_native, **state)
                self.pending_native = None
        if self.old is None:
            return self.original(frame, clear=clear, osd=osd, interval=interval)
        progress = min(1.0, max(0.0, (now - self.started) / self.duration))
        if progress >= 1.0 or frame.get_size() != self.old.get_size():
            self.old = None
            self.event(kind='blend-complete', target=name)
            return self.original(frame, clear=clear, osd=osd, interval=interval)
        # Blend a separate output surface. Persist and the native accumulator
        # keep the unblended scene; normal steady-state frames incur no copy.
        self.display.sync()
        self.output.blit(frame, (0, 0))
        ease = progress * progress * (3.0 - 2.0 * progress)
        self.old.set_alpha(round(255 * (1.0 - ease)))
        self.output.blit(self.old, (0, 0))
        rc = self.original(self.output, clear=clear, osd=osd, interval=interval)
        if clear is not None:
            frame.fill(tuple(clear)[:3])
        return rc


def install(eyesy, root, getter=None):
    main = sys.modules.get('__main__')
    display = getattr(main, 'disp', None)
    if not display or not getattr(display, 'comp', False):
        return
    existing = getattr(display, '_swarm_handoff', None)
    if existing is not None:
        existing.__class__ = Handoff
        if not hasattr(existing, 'previous_size'):
            existing.previous_size = getattr(main, 'last_frame', eyesy.screen).get_size()
        existing.getter = getter
        return
    handoff = Handoff(display, eyesy, main, root, getter=getter)
    display._swarm_handoff = handoff
    display.present = handoff.present
    print('[swarm-handoff] installed: native 3D morphs, 0.65 s blends for other Swarms', flush=True)
