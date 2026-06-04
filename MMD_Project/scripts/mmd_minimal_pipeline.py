"""
Minimal MMD / VTuber dance pipeline for Blender.

Run inside Blender:
  Text Editor -> Open this file -> Run Script

Recommended first pass:
  model/character/*.pmx
  stage/*.blend or stage/*.fbx
  motion/*.vmd
  camera/*.vmd optional
  music/*.mp3 or *.wav optional
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import bpy


PROJECT_ROOT_OVERRIDE = ""


def has_project_folders(path: Path) -> bool:
    return (
        (path / "model" / "character").exists()
        and (path / "stage").exists()
        and (path / "motion").exists()
        and (path / "scripts").exists()
    )


def search_project_root(start: Path) -> Path | None:
    candidates = [start]
    candidates.extend(start.parents)
    for candidate in candidates:
        if candidate.name == "MMD_Project" and has_project_folders(candidate):
            return candidate
        nested = candidate / "MMD_Project"
        if nested.exists() and has_project_folders(nested):
            return nested
    return None


def active_text_path() -> Path | None:
    text = getattr(getattr(bpy.context, "space_data", None), "text", None)
    filepath = getattr(text, "filepath", "") if text else ""
    if filepath:
        return Path(filepath).resolve()
    return None


def resolve_project_root() -> Path:
    if PROJECT_ROOT_OVERRIDE:
        root = Path(PROJECT_ROOT_OVERRIDE).resolve()
        if not has_project_folders(root):
            raise RuntimeError(f"PROJECT_ROOT_OVERRIDE is not a valid MMD_Project folder: {root}")
        return root

    possible_starts: list[Path] = []

    text_path = active_text_path()
    if text_path:
        possible_starts.append(text_path.parent)

    file_value = globals().get("__file__", "")
    if file_value:
        file_path = Path(file_value)
        if file_path.is_absolute():
            possible_starts.append(file_path.resolve().parent)

    blend_path = bpy.data.filepath
    if blend_path:
        possible_starts.append(Path(blend_path).resolve().parent)

    possible_starts.append(Path.cwd().resolve())

    for start in possible_starts:
        root = search_project_root(start)
        if root:
            return root

    raise RuntimeError(
        "Could not locate MMD_Project. Set PROJECT_ROOT_OVERRIDE near the top of this script, "
        "for example: PROJECT_ROOT_OVERRIDE = r'D:\\MMD\\BlenderMMD\\by_codex\\MMD_Project'"
    )


PROJECT_ROOT = resolve_project_root()

CHARACTER_DIR = PROJECT_ROOT / "model" / "character"
STAGE_DIR = PROJECT_ROOT / "stage"
MOTION_DIR = PROJECT_ROOT / "motion"
CAMERA_DIR = PROJECT_ROOT / "camera"
MUSIC_DIR = PROJECT_ROOT / "music"
VIDEO_DIR = PROJECT_ROOT / "output" / "video"
FRAMES_DIR = PROJECT_ROOT / "output" / "frames"
BLEND_DIR = PROJECT_ROOT / "blend_files"
TEXTURE_SEARCH_DIRS = [
    PROJECT_ROOT / "textures",
    PROJECT_ROOT / "stage",
    PROJECT_ROOT / "stage" / "tex",
    PROJECT_ROOT.parent / "贴图",
]

FPS = 30
RESOLUTION_X = 1920
RESOLUTION_Y = 1080
FRAME_START = 1
FRAME_END_FALLBACK = 1800
OUTPUT_CONTAINER = "MPEG4"
OUTPUT_CODEC = "H264"
OUTPUT_FILENAME = "mmd_test_render.mp4"
BLEND_FILENAME = "mmd_test_scene.blend"
RENDER_ANIMATION = False


class PipelineError(RuntimeError):
    pass


def log(message: str) -> None:
    print(f"[MMD_PIPELINE] {message}")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def first_existing_file(folder: Path, extensions: Iterable[str], required: bool) -> Path | None:
    if not folder.exists():
        if required:
            raise PipelineError(f"Folder not found: {folder}")
        return None

    normalized = tuple(ext.lower() for ext in extensions)
    matches = sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in normalized
    )
    if matches:
        log(f"Using file: {matches[0]}")
        return matches[0]

    if required:
        raise PipelineError(
            f"No file with extensions {', '.join(normalized)} found in: {folder}"
        )
    return None


def addon_enabled(module_name: str) -> bool:
    return module_name in bpy.context.preferences.addons


def require_mmd_tools() -> None:
    possible_modules = ("mmd_tools", "bl_ext.blender_org.mmd_tools")
    if any(addon_enabled(module) for module in possible_modules):
        return

    raise PipelineError(
        "mmd_tools does not appear to be enabled. In Blender, open "
        "Edit -> Preferences -> Add-ons, search 'mmd', then enable mmd_tools."
    )


def supported_operator_keywords(operator) -> set[str]:
    try:
        return {prop.identifier for prop in operator.get_rna_type().properties}
    except Exception:
        return set()


def call_operator_compat(operator, **kwargs):
    supported = supported_operator_keywords(operator)
    if supported:
        filtered = {key: value for key, value in kwargs.items() if key in supported}
        skipped = sorted(set(kwargs) - set(filtered))
        if skipped:
            log(f"Skipping unsupported operator options: {', '.join(skipped)}")
        return operator(**filtered)
    return operator(**kwargs)


def patch_cycles_light_cast_shadow_for_fbx() -> None:
    """Work around Blender 5.1 FBX importer assigning a removed Cycles light property."""
    settings_type = getattr(bpy.types, "CyclesLightSettings", None)
    if settings_type is None or hasattr(settings_type, "cast_shadow"):
        return

    try:
        settings_type.cast_shadow = bpy.props.BoolProperty(
            name="FBX Cast Shadow Compatibility",
            default=True,
        )
        log("Applied Blender 5.1 FBX light compatibility patch.")
    except Exception as exc:
        log(f"Could not apply FBX light compatibility patch: {exc}")


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    log("Cleared default scene.")


def import_pmx(path: Path) -> list[bpy.types.Object]:
    require_mmd_tools()
    before = set(bpy.data.objects)
    try:
        bpy.ops.mmd_tools.import_model(
            filepath=str(path),
            scale=0.08,
            types={"MESH", "ARMATURE", "MORPHS", "DISPLAY", "PHYSICS"}
        )
    except Exception as exc:
        raise PipelineError(
            f"PMX import failed: {path}\n"
            "Check that mmd_tools is enabled and that the PMX path has no broken texture references."
        ) from exc
    imported = [obj for obj in bpy.data.objects if obj not in before]
    log(f"Imported PMX character objects: {len(imported)}")
    return imported


def import_fbx(path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    patch_cycles_light_cast_shadow_for_fbx()
    try:
        bpy.ops.import_scene.fbx(filepath=str(path))
    except Exception as exc:
        message = str(exc)
        if "CyclesLightSettings" in message and "cast_shadow" in message:
            raise PipelineError(
                f"FBX import failed while reading lights: {path}\n"
                "This is a Blender 5.1 FBX importer compatibility issue with lights in the FBX. "
                "Quick fixes: export the room FBX again without lights/cameras, delete lights from the source scene, "
                "or import the FBX once in Blender 4.x and save it as a .blend stage."
            ) from exc
        raise PipelineError(f"FBX import failed: {path}") from exc
    imported = [obj for obj in bpy.data.objects if obj not in before]
    log(f"Imported FBX objects: {len(imported)}")
    return imported


def append_blend_scene(path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    try:
        with bpy.data.libraries.load(str(path), link=False) as (data_from, data_to):
            data_to.objects = list(data_from.objects)
        for obj in data_to.objects:
            if obj is not None:
                bpy.context.collection.objects.link(obj)
    except Exception as exc:
        raise PipelineError(f"Blend scene append failed: {path}") from exc
    imported = [obj for obj in bpy.data.objects if obj not in before]
    log(f"Appended blend scene objects: {len(imported)}")
    return imported


def import_obj(path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    try:
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=str(path))
        else:
            bpy.ops.import_scene.obj(filepath=str(path))
    except Exception as exc:
        raise PipelineError(f"OBJ import failed: {path}") from exc
    imported = [obj for obj in bpy.data.objects if obj not in before]
    log(f"Imported OBJ objects: {len(imported)}")
    return imported


def import_character(path: Path) -> list[bpy.types.Object]:
    suffix = path.suffix.lower()
    if suffix == ".pmx":
        return import_pmx(path)
    if suffix == ".fbx":
        return import_fbx(path)
    if suffix == ".blend":
        return append_blend_scene(path)
    raise PipelineError(f"Unsupported character format for first version: {path.suffix}")


def import_stage(path: Path) -> list[bpy.types.Object]:
    suffix = path.suffix.lower()
    if suffix == ".blend":
        return append_blend_scene(path)
    if suffix == ".fbx":
        return import_fbx(path)
    if suffix == ".pmx":
        return import_pmx(path)
    if suffix == ".obj":
        return import_obj(path)
    raise PipelineError(f"Unsupported stage format: {path.suffix}")


def find_armature(objects: list[bpy.types.Object]) -> bpy.types.Object | None:
    for obj in objects:
        if obj.type == "ARMATURE":
            return obj
    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def safe_select_only(obj: bpy.types.Object) -> None:
    for scene_obj in bpy.context.scene.objects:
        scene_obj.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def operator_context_for_object(obj: bpy.types.Object) -> dict:
    return {
        "active_object": obj,
        "object": obj,
        "selected_objects": [obj],
        "selected_editable_objects": [obj],
    }


def import_vmd_motion(path: Path, armature: bpy.types.Object) -> None:
    require_mmd_tools()
    safe_select_only(armature)
    try:
        with bpy.context.temp_override(**operator_context_for_object(armature)):
            call_operator_compat(
                bpy.ops.mmd_tools.import_vmd,
                filepath=str(path),
                files=[{"name": path.name}],
                directory=str(path.parent),
                scale=0.08,
                margin=0,
                bone_mapper="PMX",
                rename_bones=True,
                use_pose_mode=False,
                update_scene_settings=True,
                create_new_action=True,
                use_nla=False,
            )
    except Exception as exc:
        raise PipelineError(
            f"VMD motion import failed: {path}\n"
            "If unsupported keyword options are shown above, the script should now skip them automatically. "
            "If this still fails, the model may need PMX/MMD bones or retargeting."
        ) from exc
    log("Imported VMD motion onto character armature.")


def import_vmd_camera(path: Path) -> None:
    require_mmd_tools()
    try:
        camera = bpy.context.scene.camera
        if camera:
            safe_select_only(camera)
            with bpy.context.temp_override(**operator_context_for_object(camera)):
                call_operator_compat(
                    bpy.ops.mmd_tools.import_vmd,
                    filepath=str(path),
                    files=[{"name": path.name}],
                    directory=str(path.parent),
                )
        else:
            call_operator_compat(
                bpy.ops.mmd_tools.import_vmd,
                filepath=str(path),
                files=[{"name": path.name}],
                directory=str(path.parent),
            )
    except Exception as exc:
        raise PipelineError(
            f"VMD camera import failed: {path}\n"
            "You can continue without a camera VMD by removing this file from camera/."
        ) from exc
    log("Imported VMD camera.")


def add_default_camera() -> None:
    if bpy.context.scene.camera:
        return
    bpy.ops.object.camera_add(location=(0, -8, 3.2), rotation=(1.2217, 0, 0))
    bpy.context.scene.camera = bpy.context.object
    log("Added default camera.")


def add_music(path: Path | None) -> None:
    if path is None:
        log("No music file found. Skipping audio.")
        return
    scene = bpy.context.scene
    scene.sequence_editor_create()
    try:
        scene.sequence_editor.sequences.new_sound(
            name=path.stem,
            filepath=str(path),
            channel=1,
            frame_start=FRAME_START,
        )
    except Exception as exc:
        raise PipelineError(f"Music import failed: {path}") from exc
    log("Added music to Video Sequencer.")


def set_frame_range_from_actions() -> None:
    scene = bpy.context.scene
    end = FRAME_END_FALLBACK
    for action in bpy.data.actions:
        if action.frame_range:
            end = max(end, int(action.frame_range[1]))
    scene.frame_start = FRAME_START
    scene.frame_end = end
    log(f"Frame range set to {scene.frame_start}-{scene.frame_end}.")


def setup_toon_world_and_lighting() -> None:
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.color = (0.78, 0.84, 0.95)

    bpy.ops.object.light_add(type="SUN", location=(0, -3, 6), rotation=(0.7, 0.0, 0.45))
    sun = bpy.context.object
    sun.name = "Anime_Key_Sun"
    sun.data.energy = 2.2
    sun.data.angle = 0.04

    bpy.ops.object.light_add(type="AREA", location=(0, -4, 4))
    fill = bpy.context.object
    fill.name = "Soft_Front_Fill"
    fill.data.energy = 180
    fill.data.size = 5
    log("Added simple anime-style lighting.")


def create_basic_toon_material(original: bpy.types.Material) -> None:
    original.use_nodes = True
    nodes = original.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        return

    name = original.name.lower()
    if "skin" in name or "face" in name or "body" in name:
        bsdf.inputs["Roughness"].default_value = 0.72
        bsdf.inputs["Base Color"].default_value = (1.0, 0.72, 0.62, 1.0)
    elif "hair" in name:
        bsdf.inputs["Roughness"].default_value = 0.38
    elif "eye" in name:
        bsdf.inputs["Roughness"].default_value = 0.18
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (0.12, 0.18, 0.35, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 0.25
    else:
        bsdf.inputs["Roughness"].default_value = 0.55


def setup_basic_toon_materials() -> None:
    for material in bpy.data.materials:
        create_basic_toon_material(material)
    log("Applied basic toon-friendly material tweaks.")


def set_eevee_engine(scene: bpy.types.Scene) -> None:
    enum_items = scene.render.bl_rna.properties["engine"].enum_items
    supported = {item.identifier for item in enum_items}
    if "BLENDER_EEVEE_NEXT" in supported:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in supported:
        scene.render.engine = "BLENDER_EEVEE"
    else:
        raise PipelineError(f"Eevee render engine is not available. Supported engines: {sorted(supported)}")
    log(f"Render engine set to: {scene.render.engine}")


def setup_render_settings() -> None:
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x = RESOLUTION_X
    scene.render.resolution_y = RESOLUTION_Y
    scene.render.resolution_percentage = 100

    set_eevee_engine(scene)
    scene.eevee.taa_render_samples = 64
    scene.eevee.taa_samples = 32

    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = OUTPUT_CONTAINER
    scene.render.ffmpeg.codec = OUTPUT_CODEC
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.audio_codec = "AAC"
    scene.render.filepath = str(VIDEO_DIR / OUTPUT_FILENAME)
    log(f"Render output set to: {scene.render.filepath}")


def existing_image_path(image: bpy.types.Image) -> Path | None:
    if not image.filepath:
        return None
    try:
        path = Path(bpy.path.abspath(image.filepath)).resolve()
    except Exception:
        return None
    return path if path.exists() else None


def build_texture_index() -> dict[str, Path]:
    index: dict[str, Path] = {}
    for folder in TEXTURE_SEARCH_DIRS:
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if path.is_file():
                index.setdefault(path.name.lower(), path)
    return index


def relink_missing_images() -> None:
    texture_index = build_texture_index()
    relinked = 0
    missing: list[str] = []

    for image in bpy.data.images:
        if image.source != "FILE" or existing_image_path(image):
            continue

        original_name = Path(image.filepath).name if image.filepath else image.name
        candidate = texture_index.get(original_name.lower())
        if candidate:
            image.filepath = str(candidate)
            relinked += 1
        else:
            missing.append(image.filepath or image.name)

    if relinked:
        log(f"Relinked missing textures by filename: {relinked}")
    if missing:
        log("Some textures are still missing. Save will continue with Auto Pack disabled.")
        for item in missing[:12]:
            log(f"Missing texture: {item}")
        if len(missing) > 12:
            log(f"... {len(missing) - 12} more missing textures")


def disable_auto_pack() -> None:
    if getattr(bpy.data, "use_autopack", False):
        bpy.data.use_autopack = False
        log("Disabled Auto Pack to avoid save failures from missing external textures.")


def save_blend() -> None:
    path = BLEND_DIR / BLEND_FILENAME
    disable_auto_pack()
    relink_missing_images()
    call_operator_compat(
        bpy.ops.wm.save_as_mainfile,
        filepath=str(path),
        compress=False,
        relative_remap=False,
    )
    log(f"Saved blend file: {path}")


def render_if_enabled() -> None:
    if not RENDER_ANIMATION:
        log("RENDER_ANIMATION is False. Scene is prepared but render was not started.")
        return
    bpy.ops.render.render(animation=True)


def run_pipeline() -> None:
    for folder in (VIDEO_DIR, FRAMES_DIR, BLEND_DIR):
        ensure_dir(folder)

    character_file = first_existing_file(CHARACTER_DIR, [".pmx", ".fbx", ".blend"], required=True)
    stage_file = first_existing_file(STAGE_DIR, [".blend", ".fbx", ".pmx", ".obj"], required=True)
    motion_file = first_existing_file(MOTION_DIR, [".vmd"], required=False)
    camera_file = first_existing_file(CAMERA_DIR, [".vmd"], required=False)
    music_file = first_existing_file(MUSIC_DIR, [".mp3", ".wav", ".flac", ".m4a"], required=False)

    clear_scene()
    stage_objects = import_stage(stage_file)
    character_objects = import_character(character_file)
    armature = find_armature(character_objects)

    if motion_file:
        if armature is None:
            raise PipelineError(
                "Motion file found, but no character armature was detected. "
                "Use a PMX model for the first version, or import/retarget an armature manually."
            )
        import_vmd_motion(motion_file, armature)
    else:
        log("No VMD motion found. Skipping motion import.")

    if camera_file:
        import_vmd_camera(camera_file)
    add_default_camera()
    add_music(music_file)

    set_frame_range_from_actions()
    setup_toon_world_and_lighting()
    setup_basic_toon_materials()
    setup_render_settings()
    save_blend()
    render_if_enabled()

    log("Minimal pipeline complete.")


if __name__ == "__main__":
    try:
        run_pipeline()
    except PipelineError as exc:
        print("\n[MMD_PIPELINE_ERROR]")
        print(exc)
        raise
