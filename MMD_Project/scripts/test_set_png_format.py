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
    print(f"[PNG_TEST] current={scene.render.image_settings.file_format}")
    try:
        scene.render.image_settings.file_format = "PNG"
        print(f"[PNG_TEST] set PNG ok, current={scene.render.image_settings.file_format}")
    except Exception as exc:
        print(f"[PNG_TEST] set PNG failed: {type(exc).__name__}: {exc}")

    try:
        scene.render.filepath = r"D:\MMD\BlenderMMD\by_codex\MMD_Project\output\frames\png_test\frame_"
        scene.render.image_settings.file_format = "PNG"
        print(f"[PNG_TEST] set filepath then PNG ok, current={scene.render.image_settings.file_format}")
    except Exception as exc:
        print(f"[PNG_TEST] set filepath then PNG failed: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
