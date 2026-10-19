# Swarm Terrain Back to Front

Four Terrain surfaces form the top, right, bottom, and left walls of a box.
Their flat bases sit on the outside; every audio peak projects inward toward
the central space. Each wall uses 64 history rows and 16 frequency columns.
The box extends 17 world units along its depth, preserving its front opening.
Spectrum history scrolls from the far end toward the viewer over about 3.2 seconds. Height and color respond to the
same audio spectrum as stock Terrain.

This formation shares a native renderer and 4096 particles with the other 3D
Swarms, so it uses their native particle morph on mode changes. Stock layouts
and controls retain their original logic. Its audio history is independent.
The included swarm_handoff.py provides 0.65-second blended handoffs for Text,
Flower of Life, and the flat Kaleidoscope, which use other simulations.

Knob 1: camera distance. Knob 2: viewing angle, bounded to keep the camera facing into the box. Knob 3: glow and trails. Knob 4: hue.
Knob 5: background. Trigger is inactive, like Terrain.
