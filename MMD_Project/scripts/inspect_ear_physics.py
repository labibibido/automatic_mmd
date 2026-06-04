from __future__ import annotations

import sys
from pathlib import Path

import bpy


KEYWORDS = ("ear", "Ear", "EAR", "耳", "Kemono_Ear", "Kemono")


def matches(name: str) -> bool:
    return any(keyword in name for keyword in KEYWORDS)


def main() -> None:
    if "--" not in sys.argv:
        raise SystemExit("Usage: blender --background --python inspect_ear_physics.py -- path/to/file.blend")
    blend_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    scene = bpy.context.scene
    print(f"[EAR_PHYSICS] Blend: {blend_path}")
    print(f"[EAR_PHYSICS] Scene frame range: {scene.frame_start}-{scene.frame_end}")
    print(f"[EAR_PHYSICS] Rigid body world: {scene.rigidbody_world is not None}")
    if scene.rigidbody_world:
        world = scene.rigidbody_world
        cache = world.point_cache
        print(f"[EAR_PHYSICS] World enabled objects collection: {world.collection.name if world.collection else '<none>'}")
        print(f"[EAR_PHYSICS] Cache baked: {cache.is_baked if cache else '<no cache>'}")
        print(f"[EAR_PHYSICS] Cache range: {cache.frame_start}-{cache.frame_end if cache else '<no cache>'}")

    armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
    armatures.sort(key=lambda obj: len(obj.data.bones), reverse=True)
    arm = armatures[0] if armatures else None
    if arm:
        print(f"[EAR_PHYSICS] Armature: {arm.name}")
        for bone in arm.pose.bones:
            if matches(bone.name):
                constraints = ", ".join(f"{c.name}:{c.type}" for c in bone.constraints) or "<none>"
                print(f"[EAR_BONE] name={bone.name} parent={bone.parent.name if bone.parent else '<none>'} constraints={constraints}")

    for obj in scene.objects:
        if not matches(obj.name):
            continue
        parent = obj.parent.name if obj.parent else "<none>"
        rb = obj.rigid_body
        rb_info = "<none>"
        if rb:
            rb_info = (
                f"type={rb.type} enabled={getattr(rb, 'enabled', '<no enabled>')} "
                f"kinematic={getattr(rb, 'kinematic', '<no kinematic>')} "
                f"mass={getattr(rb, 'mass', '<no mass>')}"
            )
        constraints = ", ".join(f"{c.name}:{c.type}" for c in obj.constraints) or "<none>"
        vertex_groups = []
        if obj.type == "MESH":
            vertex_groups = [group.name for group in obj.vertex_groups if matches(group.name)]
        print(
            f"[EAR_OBJECT] name={obj.name} type={obj.type} parent={parent} "
            f"rigid_body={rb_info} constraints={constraints} vertex_groups={vertex_groups}"
        )

    for obj in scene.objects:
        if obj.rigid_body_constraint and matches(obj.name):
            con = obj.rigid_body_constraint
            print(
                f"[EAR_JOINT] name={obj.name} type={con.type} "
                f"obj1={con.object1.name if con.object1 else '<none>'} "
                f"obj2={con.object2.name if con.object2 else '<none>'} "
                f"enabled={con.enabled}"
            )


if __name__ == "__main__":
    main()
