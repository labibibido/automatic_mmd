"""
Replace motion in an existing finished Blender scene.

Use case:
  You already have a .blend with the character, stage, camera, materials,
  and maybe an old dance motion. This script keeps that scene and imports
  a new VMD motion/camera/music from the project folders.

Recommended workflow:
  1. Open your finished .blend in Blender.
  2. Put new motion in MMD_Project/motion/.
  3. Put new camera VMD in MMD_Project/camera/ if you want to replace camera motion.
  4. Put music in MMD_Project/music/ if needed.
  5. Run this script from Blender Text Editor.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import bpy
from mathutils import Vector


PROJECT_ROOT_OVERRIDE = ""
SOURCE_BLEND_NAME = ""
SOURCE_BLEND_PATH = ""
ARMATURE_NAME_OVERRIDE = ""

FPS = 30
RESOLUTION_X = 1920
RESOLUTION_Y = 1080
FRAME_START = 1
FRAME_END_FALLBACK = 0
PRE_ROLL_SECONDS = 1.0

CLEAR_EXISTING_ARMATURE_ACTIONS = True
CLEAR_EXISTING_CAMERA_ANIMATION = False
IMPORT_NEW_MOTION_VMD = True
IMPORT_NEW_CAMERA_VMD = True
NORMALIZE_IMPORTED_MOTION_TO_FRAME_START = True
ALLOW_UNSAFE_VMD_IMPORT = False
REPLACE_MUSIC = True
ADD_EXTRA_ANIME_FILL_LIGHT = True
RENDER_RESOLUTION_PERCENTAGE = 100
DISABLE_RIGID_BODY_PHYSICS_FOR_TEST = False
RESET_RIGID_BODY_CACHE = True
BAKE_RIGID_BODY_PHYSICS = True
MAX_AUTO_BAKE_FRAMES = 1500
RIGID_BODY_SUBSTEPS = 10
RIGID_BODY_SOLVER_ITERATIONS = 20
AMPLIFY_EAR_PHYSICS = False
EAR_PHYSICS_MASS_MULTIPLIER = 0.45
EAR_PHYSICS_DAMPING_MULTIPLIER = 0.65
EAR_PHYSICS_ANGULAR_DAMPING_MULTIPLIER = 0.65
CAMERA_LOOK_AT_HEAD = False
CAMERA_CALIBRATE_HEIGHT_ONCE = True
CAMERA_HEAD_BONE_CANDIDATES = ["首", "上半身2", "上半身", "Neck", "neck", "Chest", "chest", "UpperBody2", "UpperBody"]
CAMERA_HEAD_TARGET_OFFSET = (0.0, 0.0, 0.0)
CAMERA_TRACK_AXIS = "TRACK_NEGATIVE_Z"
CAMERA_UP_AXIS = "UP_Y"

SAVED_BLEND_FILENAME = "existing_blend_new_motion.blend"


def motion_start_frame() -> int:
    return FRAME_START + int(round(PRE_ROLL_SECONDS * FPS))


class PipelineError(RuntimeError):
    pass


def log(message: str) -> None:
    print(f"[MMD_REPLACE_MOTION] {message}")


def has_project_folders(path: Path) -> bool:
    return (
        (path / "motion").exists()
        and (path / "camera").exists()
        and (path / "music").exists()
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
            raise PipelineError(f"PROJECT_ROOT_OVERRIDE is not a valid MMD_Project folder: {root}")
        return root

    starts: list[Path] = []
    text_path = active_text_path()
    if text_path:
        starts.append(text_path.parent)
    file_value = globals().get("__file__", "")
    if file_value:
        file_path = Path(file_value)
        if file_path.is_absolute():
            starts.append(file_path.resolve().parent)
    if bpy.data.filepath:
        starts.append(Path(bpy.data.filepath).resolve().parent)
    starts.append(Path.cwd().resolve())

    for start in starts:
        root = search_project_root(start)
        if root:
            return root

    raise PipelineError(
        "Could not locate MMD_Project. Set PROJECT_ROOT_OVERRIDE, for example:\n"
        r"PROJECT_ROOT_OVERRIDE = r'D:\MMD\BlenderMMD\by_codex\MMD_Project'"
    )


PROJECT_ROOT = resolve_project_root()
MOTION_DIR = PROJECT_ROOT / "motion"
CAMERA_DIR = PROJECT_ROOT / "camera"
MUSIC_DIR = PROJECT_ROOT / "music"
BLEND_DIR = PROJECT_ROOT / "blend_files"
TEXTURE_SEARCH_DIRS = [
    PROJECT_ROOT / "textures",
    PROJECT_ROOT / "stage",
    PROJECT_ROOT / "stage" / "tex",
    PROJECT_ROOT.parent / "贴图",
]


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
        "mmd_tools is not enabled. Open Edit -> Preferences -> Add-ons, search 'mmd', "
        "then enable mmd_tools."
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


def open_source_blend_if_requested() -> None:
    if SOURCE_BLEND_PATH:
        source_path = Path(SOURCE_BLEND_PATH).resolve()
        if not source_path.exists():
            raise PipelineError(f"SOURCE_BLEND_PATH does not exist: {source_path}")
        bpy.ops.wm.open_mainfile(filepath=str(source_path))
        log(f"Opened source blend: {source_path}")
        return

    if not SOURCE_BLEND_NAME:
        if not bpy.data.filepath:
            log("No .blend is currently saved/opened. Continuing with current unsaved scene.")
        return

    source_path = BLEND_DIR / SOURCE_BLEND_NAME
    if not source_path.exists():
        raise PipelineError(f"SOURCE_BLEND_NAME does not exist: {source_path}")
    bpy.ops.wm.open_mainfile(filepath=str(source_path))
    log(f"Opened source blend: {source_path}")


def find_candidate_armatures() -> list[bpy.types.Object]:
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    armatures.sort(key=lambda obj: len(obj.data.bones), reverse=True)
    return armatures


def select_main_armature() -> bpy.types.Object:
    if ARMATURE_NAME_OVERRIDE:
        armature = bpy.data.objects.get(ARMATURE_NAME_OVERRIDE)
        if armature is None:
            raise PipelineError(f"ARMATURE_NAME_OVERRIDE was not found: {ARMATURE_NAME_OVERRIDE}")
        if armature.type != "ARMATURE":
            raise PipelineError(f"ARMATURE_NAME_OVERRIDE is not an Armature: {ARMATURE_NAME_OVERRIDE}")
        log(f"Selected override armature: {armature.name} ({len(armature.data.bones)} bones)")
        return armature

    armatures = find_candidate_armatures()
    if not armatures:
        raise PipelineError(
            "No Armature found in this .blend. The character must have a skeleton before VMD motion can be applied."
        )
    armature = armatures[0]
    log(f"Selected main armature: {armature.name} ({len(armature.data.bones)} bones)")
    if len(armatures) > 1:
        log("More than one armature was found. The script picked the one with the most bones.")
    return armature


def clear_armature_motion(armature: bpy.types.Object) -> None:
    if not CLEAR_EXISTING_ARMATURE_ACTIONS:
        return

    if armature.animation_data:
        armature.animation_data.action = None
        armature.animation_data_clear()

    for obj in bpy.context.scene.objects:
        if obj.parent == armature and obj.animation_data:
            obj.animation_data.action = None
            obj.animation_data_clear()

    log("Cleared existing armature/object animation data for the selected character.")


def clear_camera_motion() -> None:
    if not CLEAR_EXISTING_CAMERA_ANIMATION:
        return
    for obj in bpy.context.scene.objects:
        if obj.type == "CAMERA" and obj.animation_data:
            obj.animation_data.action = None
            obj.animation_data_clear()
    log("Cleared existing camera animation.")


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


def mmd_bone_compatibility_report(armature: bpy.types.Object) -> tuple[bool, list[str]]:
    bone_names = {bone.name for bone in armature.data.bones}
    mmd_japanese_names = set()
    for pose_bone in armature.pose.bones:
        mmd_bone = getattr(pose_bone, "mmd_bone", None)
        name_j = getattr(mmd_bone, "name_j", "") if mmd_bone else ""
        if name_j:
            mmd_japanese_names.add(name_j)
    all_names = bone_names | mmd_japanese_names

    required_any = [
        ("center", ["センター", "Center"]),
        ("lower body", ["下半身", "LowerBody"]),
        ("upper body", ["上半身", "UpperBody"]),
        ("neck", ["首", "Neck"]),
        ("head", ["頭", "Head"]),
        ("left arm", ["左腕", "腕.L", "腕左", "LeftArm"]),
        ("right arm", ["右腕", "腕.R", "腕右", "RightArm"]),
        ("left elbow", ["左ひじ", "ひじ.L", "LeftElbow"]),
        ("right elbow", ["右ひじ", "ひじ.R", "RightElbow"]),
        ("left wrist", ["左手首", "手首.L", "LeftWrist"]),
        ("right wrist", ["右手首", "手首.R", "RightWrist"]),
        ("left leg", ["左足", "足.L", "LeftLeg"]),
        ("right leg", ["右足", "足.R", "RightLeg"]),
        ("left knee", ["左ひざ", "ひざ.L", "LeftKnee"]),
        ("right knee", ["右ひざ", "ひざ.R", "RightKnee"]),
        ("left ankle", ["左足首", "足首.L", "LeftAnkle"]),
        ("right ankle", ["右足首", "足首.R", "RightAnkle"]),
    ]

    missing = [
        label
        for label, candidates in required_any
        if not any(candidate in all_names for candidate in candidates)
    ]

    strict_vmd_names = ["左腕", "右腕", "左足", "右足", "左ひざ", "右ひざ", "左手首", "右手首"]
    missing_strict = [name for name in strict_vmd_names if name not in all_names]
    warnings = []
    if missing:
        warnings.append(f"Missing required humanoid bone groups: {', '.join(missing)}")
    if missing_strict:
        warnings.append(
            "Standard VMD Japanese side bones are missing: "
            + ", ".join(missing_strict)
            + ". This armature may need retargeting or bone-name conversion before direct VMD import."
        )

    compatible = not missing and not missing_strict
    return compatible, warnings


def import_vmd_motion(path: Path, armature: bpy.types.Object) -> None:
    require_mmd_tools()
    compatible, warnings = mmd_bone_compatibility_report(armature)
    for warning in warnings:
        log(warning)
    if not compatible and not ALLOW_UNSAFE_VMD_IMPORT:
        raise PipelineError(
            "Direct VMD import is blocked because this armature does not expose standard VMD bone names.\n"
            "This matches the severe twisting/stretching you saw. Use the original .blend action, use an FBX/BVH "
            "motion retarget workflow, or create a proper MMD bone map first.\n"
            "If you still want to test direct VMD import, set ALLOW_UNSAFE_VMD_IMPORT = True."
        )

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
            "If this is the same MMD/PMX character, check whether the armature selected by the script is the real "
            "character armature. If it is not MMD-style, retargeting is required."
        ) from exc
    normalize_armature_action_start(armature)
    insert_t_pose_preroll(armature)
    log("Imported new VMD motion onto the existing character.")


def normalize_armature_action_start(armature: bpy.types.Object) -> None:
    if not NORMALIZE_IMPORTED_MOTION_TO_FRAME_START:
        return
    if not armature.animation_data or not armature.animation_data.action:
        return

    action = armature.animation_data.action
    start, end = action.frame_range
    target_start = motion_start_frame()
    delta = target_start - int(start)
    if delta == 0:
        log(f"Imported action already starts at frame {target_start}.")
        return

    for fcurve in action.fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.co.x += delta
            keyframe.handle_left.x += delta
            keyframe.handle_right.x += delta
        fcurve.update()

    new_start, new_end = action.frame_range
    log(
        f"Shifted imported action '{action.name}' by {delta} frames: "
        f"{int(start)}-{int(end)} -> {int(new_start)}-{int(new_end)}"
    )


def shift_action_to_frame(action: bpy.types.Action, target_start: int, label: str) -> None:
    start, end = action.frame_range
    delta = target_start - int(start)
    if delta == 0:
        log(f"{label} action already starts at frame {target_start}.")
        return

    for fcurve in action.fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.co.x += delta
            keyframe.handle_left.x += delta
            keyframe.handle_right.x += delta
        fcurve.update()

    new_start, new_end = action.frame_range
    log(
        f"Shifted {label} action '{action.name}' by {delta} frames: "
        f"{int(start)}-{int(end)} -> {int(new_start)}-{int(new_end)}"
    )


def camera_actions() -> set[bpy.types.Action]:
    actions: set[bpy.types.Action] = set()
    for obj in bpy.context.scene.objects:
        if obj.type != "CAMERA":
            continue
        if obj.animation_data and obj.animation_data.action:
            actions.add(obj.animation_data.action)
        if obj.data and obj.data.animation_data and obj.data.animation_data.action:
            actions.add(obj.data.animation_data.action)
    return actions


def shift_new_or_early_camera_actions(before_actions: set[bpy.types.Action]) -> None:
    target_start = motion_start_frame()
    for action in camera_actions():
        start, _end = action.frame_range
        if action not in before_actions or int(start) < target_start:
            shift_action_to_frame(action, target_start, "camera")


def insert_t_pose_preroll(armature: bpy.types.Object) -> None:
    if PRE_ROLL_SECONDS <= 0 or not armature.animation_data or not armature.animation_data.action:
        return

    action = armature.animation_data.action
    scene = bpy.context.scene
    hold_end = max(FRAME_START, motion_start_frame() - 1)

    scene.frame_set(FRAME_START)
    for pose_bone in armature.pose.bones:
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)
        if pose_bone.rotation_mode == "QUATERNION":
            pose_bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        elif pose_bone.rotation_mode == "AXIS_ANGLE":
            pose_bone.rotation_axis_angle = (0.0, 0.0, 1.0, 0.0)
            rotation_path = "rotation_axis_angle"
        else:
            pose_bone.rotation_euler = (0.0, 0.0, 0.0)
            rotation_path = "rotation_euler"
        if pose_bone.rotation_mode == "QUATERNION":
            rotation_path = "rotation_quaternion"

        pose_bone.keyframe_insert(data_path="location", frame=FRAME_START)
        pose_bone.keyframe_insert(data_path="scale", frame=FRAME_START)
        pose_bone.keyframe_insert(data_path=rotation_path, frame=FRAME_START)

        pose_bone.keyframe_insert(data_path="location", frame=hold_end)
        pose_bone.keyframe_insert(data_path="scale", frame=hold_end)
        pose_bone.keyframe_insert(data_path=rotation_path, frame=hold_end)

    armature.animation_data.action = action
    scene.frame_set(FRAME_START)
    log(f"Inserted T-pose preroll hold from frame {FRAME_START} to {hold_end}.")


def import_vmd_camera(path: Path | None) -> None:
    if path is None or not IMPORT_NEW_CAMERA_VMD:
        log("No new camera VMD imported. Existing camera is preserved.")
        return
    require_mmd_tools()
    clear_camera_motion()
    before_actions = camera_actions()
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
        shift_new_or_early_camera_actions(before_actions)
    except Exception as exc:
        raise PipelineError(f"VMD camera import failed: {path}") from exc
    log("Imported new VMD camera motion.")


def replace_music(path: Path | None) -> None:
    if path is None:
        log("No music file found. Existing audio is preserved.")
        return
    if not REPLACE_MUSIC:
        log("REPLACE_MUSIC is False. Existing audio is preserved.")
        return

    scene = bpy.context.scene
    scene.sequence_editor_create()
    for sequence in list(scene.sequence_editor.sequences_all):
        if sequence.type == "SOUND":
            scene.sequence_editor.sequences.remove(sequence)

    try:
        scene.sequence_editor.sequences.new_sound(
            name=path.stem,
            filepath=str(path),
            channel=1,
            frame_start=motion_start_frame(),
        )
    except Exception as exc:
        raise PipelineError(f"Music import failed: {path}") from exc
    log("Replaced music in the Video Sequencer.")


def ensure_camera() -> None:
    if bpy.context.scene.camera:
        log(f"Using existing scene camera: {bpy.context.scene.camera.name}")
        return
    cameras = [obj for obj in bpy.context.scene.objects if obj.type == "CAMERA"]
    if cameras:
        bpy.context.scene.camera = cameras[0]
        log(f"Assigned existing camera as scene camera: {cameras[0].name}")
        return
    bpy.ops.object.camera_add(location=(0, -8, 3.2), rotation=(1.2217, 0, 0))
    bpy.context.scene.camera = bpy.context.object
    log("No camera found. Added default camera.")


def find_pose_bone(armature: bpy.types.Object, candidates: list[str]) -> bpy.types.PoseBone | None:
    for name in candidates:
        pose_bone = armature.pose.bones.get(name)
        if pose_bone:
            return pose_bone

    for pose_bone in armature.pose.bones:
        mmd_bone = getattr(pose_bone, "mmd_bone", None)
        name_j = getattr(mmd_bone, "name_j", "") if mmd_bone else ""
        name_e = getattr(mmd_bone, "name_e", "") if mmd_bone else ""
        if name_j in candidates or name_e in candidates:
            return pose_bone
    return None


def setup_camera_head_target(armature: bpy.types.Object) -> None:
    if not CAMERA_LOOK_AT_HEAD:
        return

    camera = bpy.context.scene.camera
    if camera is None:
        log("No scene camera found. Skipping head-centered camera target.")
        return

    head_bone = find_pose_bone(armature, CAMERA_HEAD_BONE_CANDIDATES)
    if head_bone is None:
        log("No head bone found. Skipping head-centered camera target.")
        return

    target_name = "Pipeline_Camera_Head_Target"
    target = bpy.data.objects.get(target_name)
    if target is None:
        bpy.ops.object.empty_add(type="PLAIN_AXES")
        target = bpy.context.object
        target.name = target_name
    target.empty_display_size = 0.25

    target.parent = armature
    target.parent_type = "BONE"
    target.parent_bone = head_bone.name
    target.location = CAMERA_HEAD_TARGET_OFFSET
    target.rotation_euler = (0.0, 0.0, 0.0)
    target.scale = (1.0, 1.0, 1.0)

    for constraint in list(camera.constraints):
        if constraint.name == "Pipeline_Look_At_Head":
            camera.constraints.remove(constraint)

    track = camera.constraints.new(type="TRACK_TO")
    track.name = "Pipeline_Look_At_Head"
    track.target = target
    track.track_axis = CAMERA_TRACK_AXIS
    track.up_axis = CAMERA_UP_AXIS
    log(f"Camera now tracks head target on bone: {head_bone.name}")


def pose_bone_world_location(armature: bpy.types.Object, pose_bone: bpy.types.PoseBone) -> Vector:
    return armature.matrix_world @ pose_bone.matrix.translation


def shift_camera_location_z(camera: bpy.types.Object, delta_z: float) -> None:
    if abs(delta_z) < 0.0001:
        log("Camera height calibration delta is near zero. No camera shift needed.")
        return

    shifted_curves = 0
    if camera.animation_data and camera.animation_data.action:
        action = camera.animation_data.action
        for fcurve in action.fcurves:
            if fcurve.data_path == "location" and fcurve.array_index == 2:
                for keyframe in fcurve.keyframe_points:
                    keyframe.co.y += delta_z
                    keyframe.handle_left.y += delta_z
                    keyframe.handle_right.y += delta_z
                fcurve.update()
                shifted_curves += 1

    camera.location.z += delta_z
    log(f"Camera height calibration applied: delta_z={delta_z:.4f}, shifted_z_curves={shifted_curves}")


def calibrate_camera_height_once(armature: bpy.types.Object) -> None:
    if not CAMERA_CALIBRATE_HEIGHT_ONCE:
        return

    camera = bpy.context.scene.camera
    if camera is None:
        log("No scene camera found. Skipping one-time camera height calibration.")
        return

    head_bone = find_pose_bone(armature, CAMERA_HEAD_BONE_CANDIDATES)
    if head_bone is None:
        log("No head bone found. Skipping one-time camera height calibration.")
        return

    scene = bpy.context.scene
    sample_frame = motion_start_frame()
    scene.frame_set(sample_frame)
    bpy.context.view_layer.update()

    head_location = pose_bone_world_location(armature, head_bone)
    desired_center_z = head_location.z + CAMERA_HEAD_TARGET_OFFSET[2]

    camera_location = camera.matrix_world.translation
    camera_forward = camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    head_distance = max((head_location - camera_location).length, 0.001)
    current_center_z = camera_location.z + camera_forward.z * head_distance
    delta_z = desired_center_z - current_center_z

    shift_camera_location_z(camera, delta_z)
    scene.frame_set(FRAME_START)
    log(
        "One-time camera height calibration: "
        f"frame={sample_frame}, head_z={head_location.z:.4f}, "
        f"center_z={current_center_z:.4f}, desired_z={desired_center_z:.4f}"
    )


def add_anime_fill_light() -> None:
    if not ADD_EXTRA_ANIME_FILL_LIGHT:
        return
    if bpy.data.objects.get("Pipeline_Soft_Anime_Fill"):
        return
    bpy.ops.object.light_add(type="AREA", location=(0, -4, 4))
    fill = bpy.context.object
    fill.name = "Pipeline_Soft_Anime_Fill"
    fill.data.energy = 120
    fill.data.size = 5
    log("Added optional soft anime fill light.")


def configure_rigid_body_physics() -> None:
    rigid_body_objects = [obj for obj in bpy.context.scene.objects if obj.rigid_body]
    log(f"Rigid body objects detected: {len(rigid_body_objects)}")

    if DISABLE_RIGID_BODY_PHYSICS_FOR_TEST:
        disabled = 0
        for obj in rigid_body_objects:
            if hasattr(obj.rigid_body, "enabled"):
                obj.rigid_body.enabled = False
                disabled += 1
        log(f"Disabled rigid body physics for test: {disabled} objects.")
        return

    enabled = 0
    for obj in rigid_body_objects:
        if hasattr(obj.rigid_body, "enabled"):
            obj.rigid_body.enabled = True
            enabled += 1
    if enabled:
        log(f"Enabled rigid body physics: {enabled} objects.")

    if AMPLIFY_EAR_PHYSICS:
        amplify_ear_physics(rigid_body_objects)

    world = bpy.context.scene.rigidbody_world
    if world is None:
        log("No rigid body world found. Skipping physics cache reset.")
        return

    world.substeps_per_frame = RIGID_BODY_SUBSTEPS
    world.solver_iterations = RIGID_BODY_SOLVER_ITERATIONS
    if world.point_cache:
        world.point_cache.frame_start = bpy.context.scene.frame_start
        world.point_cache.frame_end = bpy.context.scene.frame_end

    if RESET_RIGID_BODY_CACHE:
        try:
            bpy.ops.ptcache.free_bake_all()
            log("Freed existing physics cache.")
        except Exception as exc:
            log(f"Could not free physics cache automatically: {exc}")

    bpy.context.scene.frame_set(bpy.context.scene.frame_start)
    log(
        "Rigid body physics configured: "
        f"substeps={world.substeps_per_frame}, solver_iterations={world.solver_iterations}"
    )

    frame_count = bpy.context.scene.frame_end - bpy.context.scene.frame_start + 1
    if BAKE_RIGID_BODY_PHYSICS:
        if frame_count > MAX_AUTO_BAKE_FRAMES:
            log(
                f"Skipping automatic rigid body bake because frame_count={frame_count} "
                f"> MAX_AUTO_BAKE_FRAMES={MAX_AUTO_BAKE_FRAMES}. "
                "Raise MAX_AUTO_BAKE_FRAMES if you want the script to bake this full range."
            )
            return
        try:
            bpy.ops.ptcache.bake_all(bake=True)
            log("Baked rigid body physics cache.")
        except Exception as exc:
            log(f"Could not bake physics automatically: {exc}")


def amplify_ear_physics(rigid_body_objects: list[bpy.types.Object]) -> None:
    changed = 0
    for obj in rigid_body_objects:
        name = obj.name.lower()
        if "ear" not in name or obj.rigid_body.kinematic:
            continue
        rb = obj.rigid_body
        rb.mass = max(0.01, rb.mass * EAR_PHYSICS_MASS_MULTIPLIER)
        rb.linear_damping *= EAR_PHYSICS_DAMPING_MULTIPLIER
        rb.angular_damping *= EAR_PHYSICS_ANGULAR_DAMPING_MULTIPLIER
        changed += 1
    if changed:
        log(f"Amplified ear physics response on {changed} rigid bodies.")


def set_frame_range_from_actions() -> None:
    scene = bpy.context.scene
    end = max(scene.frame_end, FRAME_END_FALLBACK)
    for action in bpy.data.actions:
        if action.frame_range:
            end = max(end, int(action.frame_range[1]))
    scene.frame_start = FRAME_START
    scene.frame_end = end
    log(f"Frame range set to {scene.frame_start}-{scene.frame_end}.")


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
    scene.render.resolution_percentage = RENDER_RESOLUTION_PERCENTAGE
    set_eevee_engine(scene)
    scene.eevee.taa_render_samples = 64
    scene.eevee.taa_samples = 32
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    log("Scene preview/render settings prepared. Actual frame rendering is handled by render_png_frames_safe.py.")


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


def save_blend_copy() -> None:
    ensure_dir(BLEND_DIR)
    path = BLEND_DIR / SAVED_BLEND_FILENAME
    disable_auto_pack()
    relink_missing_images()
    call_operator_compat(
        bpy.ops.wm.save_as_mainfile,
        filepath=str(path),
        compress=False,
        relative_remap=False,
    )
    log(f"Saved editable blend copy: {path}")


def run_pipeline() -> None:
    ensure_dir(BLEND_DIR)

    open_source_blend_if_requested()

    motion_file = first_existing_file(MOTION_DIR, [".vmd"], required=True)
    camera_file = first_existing_file(CAMERA_DIR, [".vmd"], required=False)
    music_file = first_existing_file(MUSIC_DIR, [".mp3", ".wav", ".flac", ".m4a"], required=False)

    armature = select_main_armature()
    if IMPORT_NEW_MOTION_VMD:
        clear_armature_motion(armature)
        import_vmd_motion(motion_file, armature)
    else:
        log("IMPORT_NEW_MOTION_VMD is False. Existing character motion is preserved.")
    import_vmd_camera(camera_file)
    replace_music(music_file)
    ensure_camera()
    calibrate_camera_height_once(armature)
    setup_camera_head_target(armature)
    add_anime_fill_light()
    set_frame_range_from_actions()
    configure_rigid_body_physics()
    setup_render_settings()
    save_blend_copy()

    log("Existing blend motion replacement complete. Use render_png_frames_safe.py for frame rendering.")


if __name__ == "__main__":
    try:
        run_pipeline()
    except PipelineError as exc:
        print("\n[MMD_REPLACE_MOTION_ERROR]")
        print(exc)
        raise
