from __future__ import annotations

import sys
from pathlib import Path

import bpy


def main() -> None:
    if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1:
        blend_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
        if blend_path.exists():
            bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    scene = bpy.context.scene
    items = scene.render.image_settings.bl_rna.properties["file_format"].enum_items
    print("[RENDER_FORMATS] file_format items:")
    for item in items:
        print(f"[FORMAT] {item.identifier}")
    print(f"[RENDER_FORMATS] current={scene.render.image_settings.file_format}")


if __name__ == "__main__":
    main()
