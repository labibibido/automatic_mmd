from __future__ import annotations

import sys
from pathlib import Path

import bpy


WATCH_OBJECTS = [
    "00C_Ear_L.001",
    "00D_Ear_L.002",
    "00G_Ear_R.001",
    "00H_Ear_R.002",
]


def main() -> None:
    if "--" not in sys.argv:
        raise SystemExit("Usage: blender --background --python measure_ear_motion.py -- path/to/file.blend")
    blend_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    scene = bpy.context.scene
    frames = [scene.frame_start, min(scene.frame_start + 30, scene.frame_end), min(scene.frame_start + 120, scene.frame_end), scene.frame_end]
    frames = sorted(set(frames))

    samples: dict[str, list[tuple[int, tuple[float, float, float]]]] = {name: [] for name in WATCH_OBJECTS}
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for name in WATCH_OBJECTS:
            obj = bpy.data.objects.get(name)
            if obj:
                loc = obj.matrix_world.translation
                samples[name].append((frame, (loc.x, loc.y, loc.z)))

    for name, values in samples.items():
        print(f"[EAR_MOTION] {name}")
        previous = None
        for frame, loc in values:
            if previous is None:
                delta = 0.0
            else:
                delta = sum((loc[i] - previous[i]) ** 2 for i in range(3)) ** 0.5
            print(f"[EAR_MOTION_SAMPLE] frame={frame} loc=({loc[0]:.4f},{loc[1]:.4f},{loc[2]:.4f}) delta_from_prev={delta:.6f}")
            previous = loc


if __name__ == "__main__":
    main()
