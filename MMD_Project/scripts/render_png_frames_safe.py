"""
Safely render the current Blender scene to PNG frames, one frame at a time.

Use after running replace_motion_in_existing_blend.py and opening the saved .blend.
This avoids Blender's FFMPEG/mp4 path and also avoids projects where
render.image_settings.file_format is stuck on FFMPEG.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import bpy


PROJECT_ROOT_OVERRIDE = r"D:\MMD\BlenderMMD\by_codex\MMD_Project"
OUTPUT_RUN_NAME = ""
FRAME_STEP = 1
FRAME_START_OVERRIDE = 0
FRAME_END_OVERRIDE = 0
SAVE_FORMAT = "PNG"


def log(message: str) -> None:
    print(f"[SAFE_FRAME_RENDER] {message}")


def project_root() -> Path:
    if PROJECT_ROOT_OVERRIDE:
        return Path(PROJECT_ROOT_OVERRIDE).resolve()
    if bpy.data.filepath:
        current = Path(bpy.data.filepath).resolve()
        for parent in [current.parent, *current.parents]:
            candidate = parent / "MMD_Project"
            if candidate.exists():
                return candidate
            if parent.name == "MMD_Project":
                return parent
    return Path.cwd().resolve()


def output_dir() -> Path:
    run_name = OUTPUT_RUN_NAME or "manual_frames_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    path = project_root() / "output" / "frames" / run_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def frame_range() -> tuple[int, int]:
    scene = bpy.context.scene
    start = FRAME_START_OVERRIDE or scene.frame_start
    end = FRAME_END_OVERRIDE or scene.frame_end
    return int(start), int(end)


def save_render_result(path: Path) -> None:
    image = bpy.data.images.get("Render Result")
    if image is None:
        raise RuntimeError("Render Result image was not found after rendering.")
    image.save_render(filepath=str(path), scene=bpy.context.scene)


def main() -> None:
    scene = bpy.context.scene
    start, end = frame_range()
    out_dir = output_dir()

    log(f"Output folder: {out_dir}")
    log(f"Frame range: {start}-{end}, step={FRAME_STEP}")
    log("Rendering one frame at a time. Already-rendered frames will be skipped.")

    for frame in range(start, end + 1, FRAME_STEP):
        suffix = SAVE_FORMAT.lower()
        frame_path = out_dir / f"frame_{frame:04d}.{suffix}"
        if frame_path.exists():
            log(f"Skip existing frame {frame}: {frame_path.name}")
            continue

        scene.frame_set(frame)
        bpy.context.view_layer.update()
        log(f"Rendering frame {frame} -> {frame_path.name}")
        bpy.ops.render.render(write_still=False, animation=False)
        save_render_result(frame_path)

    log("Safe PNG frame render complete.")


if __name__ == "__main__":
    main()
