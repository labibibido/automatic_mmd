from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import bpy


WATCH_WORDS = (
    "ear", "Ear", "耳", "Kemono_Ear",
    "hair", "Hair", "髪", "Ahoge",
    "tail", "Tail", "Kemono_Tail",
    "skirt", "Skirt",
    "breast", "Breast",
    "secondary",
    "rigid",
)


def main() -> None:
    if "--" not in sys.argv:
        raise SystemExit("Usage: blender --background --python inspect_action_fcurves.py -- path/to/file.blend")
    blend_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    armatures.sort(key=lambda obj: len(obj.data.bones), reverse=True)
    arm = armatures[0] if armatures else None
    action = arm.animation_data.action if arm and arm.animation_data else None
    if action is None:
        print("[FCURVES] No armature action found.")
        return

    print(f"[FCURVES] Armature: {arm.name}")
    print(f"[FCURVES] Action: {action.name}")
    bone_counter: Counter[str] = Counter()
    watched: list[str] = []

    for fcurve in action.fcurves:
        path = fcurve.data_path
        if 'pose.bones["' not in path:
            continue
        bone_name = path.split('pose.bones["', 1)[1].split('"]', 1)[0]
        bone_counter[bone_name] += 1
        if any(word in bone_name for word in WATCH_WORDS):
            watched.append(bone_name)

    print(f"[FCURVES] Animated bones: {len(bone_counter)}")
    print("[FCURVES] Top animated bones:")
    for name, count in bone_counter.most_common(80):
        print(f"[ANIM_BONE] {name} curves={count}")

    unique_watched = sorted(set(watched))
    print(f"[FCURVES] Watched accessory/physics-like animated bones: {len(unique_watched)}")
    for name in unique_watched[:120]:
        print(f"[WATCHED_BONE] {name}")


if __name__ == "__main__":
    main()
