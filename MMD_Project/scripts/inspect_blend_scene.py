from __future__ import annotations

import sys
from pathlib import Path

import bpy


def main() -> None:
    if "--" not in sys.argv:
        raise SystemExit("Usage: blender --background --python inspect_blend_scene.py -- path/to/file.blend")
    blend_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    if not blend_path.exists():
        raise SystemExit(f"Blend file not found: {blend_path}")

    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    print(f"[INSPECT] Blend: {blend_path}")
    print(f"[INSPECT] Scene: {bpy.context.scene.name}")
    print(f"[INSPECT] Frame range: {bpy.context.scene.frame_start}-{bpy.context.scene.frame_end}")

    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    cameras = [obj for obj in bpy.context.scene.objects if obj.type == "CAMERA"]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    lights = [obj for obj in bpy.context.scene.objects if obj.type == "LIGHT"]

    print(f"[INSPECT] Armatures: {len(armatures)}")
    for obj in sorted(armatures, key=lambda item: len(item.data.bones), reverse=True):
        action = obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else "<none>"
        print(f"[ARMATURE] name={obj.name} bones={len(obj.data.bones)} action={action}")

    print(f"[INSPECT] Cameras: {len(cameras)}")
    scene_camera_name = bpy.context.scene.camera.name if bpy.context.scene.camera else "<none>"
    print(f"[INSPECT] Scene camera: {scene_camera_name}")
    for obj in cameras:
        action = obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else "<none>"
        print(f"[CAMERA] name={obj.name} action={action}")

    print(f"[INSPECT] Meshes: {len(meshes)}")
    for obj in sorted(meshes, key=lambda item: item.name)[:30]:
        print(f"[MESH] name={obj.name} parent={obj.parent.name if obj.parent else '<none>'}")
    if len(meshes) > 30:
        print(f"[MESH] ... {len(meshes) - 30} more")

    print(f"[INSPECT] Lights: {len(lights)}")
    for obj in lights:
        print(f"[LIGHT] name={obj.name} type={obj.data.type}")

    print(f"[INSPECT] Actions: {len(bpy.data.actions)}")
    for action in sorted(bpy.data.actions, key=lambda item: item.name)[:40]:
        start, end = action.frame_range
        print(f"[ACTION] name={action.name} frames={int(start)}-{int(end)}")
    if len(bpy.data.actions) > 40:
        print(f"[ACTION] ... {len(bpy.data.actions) - 40} more")


if __name__ == "__main__":
    main()
