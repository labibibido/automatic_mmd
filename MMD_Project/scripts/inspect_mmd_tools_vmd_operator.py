from __future__ import annotations

import sys
from pathlib import Path

import bpy


def main() -> None:
    blend_path = None
    if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1:
        blend_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    if blend_path and blend_path.exists():
        bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    print("[VMD_OPERATOR] import_vmd properties:")
    for prop in bpy.ops.mmd_tools.import_vmd.get_rna_type().properties:
        enum_values = ""
        if getattr(prop, "enum_items", None):
            enum_values = " enum=" + ",".join(item.identifier for item in prop.enum_items)
        default = getattr(prop, "default", "<no default>")
        print(f"[VMD_OPERATOR_PROP] {prop.identifier} default={default}{enum_values}")

    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    armatures.sort(key=lambda obj: len(obj.data.bones), reverse=True)
    if not armatures:
        print("[MMD_BONE_META] No armature.")
        return

    arm = armatures[0]
    print(f"[MMD_BONE_META] Armature: {arm.name}")
    interesting = ["腕.R", "腕.L", "足.R", "足.L", "ひじ.R", "ひじ.L", "手首.R", "手首.L", "センター"]
    for name in interesting:
        bone = arm.pose.bones.get(name)
        if not bone:
            print(f"[MMD_BONE_META] {name}: missing")
            continue
        mmd_bone = getattr(bone, "mmd_bone", None)
        attrs = {}
        if mmd_bone:
            for attr in ("name_j", "name_e", "bone_id", "transform_order", "additional_transform_bone"):
                if hasattr(mmd_bone, attr):
                    attrs[attr] = getattr(mmd_bone, attr)
        print(f"[MMD_BONE_META] {name}: {attrs}")


if __name__ == "__main__":
    main()
