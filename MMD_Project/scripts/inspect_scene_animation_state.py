from __future__ import annotations

import sys
from pathlib import Path

import bpy


def action_name(obj: bpy.types.Object) -> str:
    if obj.animation_data and obj.animation_data.action:
        return obj.animation_data.action.name
    return "<none>"


def main() -> None:
    if "--" not in sys.argv:
        raise SystemExit("Usage: blender --background --python inspect_scene_animation_state.py -- path/to/file.blend")
    blend_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    scene = bpy.context.scene
    print(f"[ANIM_STATE] Blend: {blend_path}")
    print(f"[ANIM_STATE] Scene frame range: {scene.frame_start}-{scene.frame_end}")
    print(f"[ANIM_STATE] Current frame: {scene.frame_current}")

    for obj in sorted([o for o in scene.objects if o.type == "ARMATURE"], key=lambda o: len(o.data.bones), reverse=True):
        print(f"[ARMATURE_STATE] name={obj.name} bones={len(obj.data.bones)} action={action_name(obj)}")
        if obj.animation_data and obj.animation_data.action:
            start, end = obj.animation_data.action.frame_range
            print(f"[ARMATURE_ACTION] frames={int(start)}-{int(end)} fcurves={len(obj.animation_data.action.fcurves)}")
        print(f"[ARMATURE_STATE] nla_tracks={len(obj.animation_data.nla_tracks) if obj.animation_data else 0}")

    for obj in [o for o in scene.objects if o.type == "CAMERA"]:
        print(f"[CAMERA_STATE] name={obj.name} action={action_name(obj)}")

    print(f"[ANIM_STATE] Actions: {len(bpy.data.actions)}")
    for action in sorted(bpy.data.actions, key=lambda a: a.name):
        start, end = action.frame_range
        print(f"[ACTION_STATE] name={action.name} frames={int(start)}-{int(end)} fcurves={len(action.fcurves)}")


if __name__ == "__main__":
    main()
