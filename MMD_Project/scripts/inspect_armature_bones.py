from __future__ import annotations

import sys
from pathlib import Path

import bpy


def main() -> None:
    if "--" not in sys.argv:
        raise SystemExit("Usage: blender --background --python inspect_armature_bones.py -- path/to/file.blend")
    blend_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    armatures.sort(key=lambda obj: len(obj.data.bones), reverse=True)
    if not armatures:
        print("[BONES] No armature found.")
        return

    armature = armatures[0]
    print(f"[BONES] Armature: {armature.name}")
    print(f"[BONES] Bone count: {len(armature.data.bones)}")
    for bone in list(armature.data.bones)[:120]:
        print(f"[BONE] {bone.name}")


if __name__ == "__main__":
    main()
