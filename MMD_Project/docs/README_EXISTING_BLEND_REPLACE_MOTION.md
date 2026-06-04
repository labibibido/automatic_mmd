# 已有成品 `.blend` 换动作流程

适合这种情况：

- `.blend` 里已经有角色
- 角色就是你最终想用的角色
- 角色已经有骨架、材质、物理、场景
- 摄像头也已经调好
- 你只是想以后换新的舞蹈动作、镜头和音乐

请使用：

```text
MMD_Project/scripts/replace_motion_in_existing_blend.py
```

不要用 `mmd_minimal_pipeline.py` 处理成品工程，因为那个脚本会清空并重新导入场景，更适合从零组装。

## 推荐用法

1. 先复制一份你的成品 `.blend`，避免误覆盖原工程。
2. 用 Blender 打开这个成品 `.blend`。
3. 把新的动作放进：

```text
MMD_Project/motion/
```

4. 如果有新镜头 VMD，放进：

```text
MMD_Project/camera/
```

5. 如果有新音乐，放进：

```text
MMD_Project/music/
```

6. 在 Blender 的 Text Editor 打开并运行：

```text
MMD_Project/scripts/replace_motion_in_existing_blend.py
```

脚本会保存一个新副本：

```text
MMD_Project/blend_files/existing_blend_new_motion.blend
```

默认不会直接渲染。确认动作和镜头没问题后，把脚本里的：

```python
RENDER_ANIMATION = False
```

改成：

```python
RENDER_ANIMATION = True
```

视频输出到：

```text
MMD_Project/output/video/existing_blend_new_motion.mp4
```

默认推荐不要直接输出 mp4，而是先输出 PNG 序列。脚本会自动设置：

```python
OUTPUT_MODE = "PNG_SEQUENCE"
RENDER_ANIMATION = False
```

运行脚本后，它只会配置渲染，不会立刻开渲。确认工程正常后，在 Blender 菜单里手动点：

```text
Render -> Render Animation
```

每次运行会创建一个新的帧输出文件夹：

```text
MMD_Project/output/frames/render_YYYYMMDD_HHMMSS/frame_0001.png
MMD_Project/output/frames/render_YYYYMMDD_HHMMSS/frame_0002.png
MMD_Project/output/frames/render_YYYYMMDD_HHMMSS/frame_0003.png
```

这种方式比直接 mp4 稳得多：中断后已经渲好的帧还在，不需要全部重来。

如果 Blender 报错说 PNG 格式不可用，或者工程输出格式被锁在 `FFMPEG`，使用安全逐帧渲染脚本：

```text
MMD_Project/scripts/render_png_frames_safe.py
```

用法：

1. 先运行 `replace_motion_in_existing_blend.py`，让它保存好新工程。
2. 打开保存后的工程：

```text
MMD_Project/blend_files/existing_blend_new_motion.blend
```

3. 在 Text Editor 里打开：

```text
MMD_Project/scripts/render_png_frames_safe.py
```

4. 点击 `Run Script`。

它会逐帧渲染并保存：

```text
MMD_Project/output/frames/manual_frames_YYYYMMDD_HHMMSS/frame_0001.png
```

已经存在的帧会自动跳过，所以中断后可以继续跑。

如果你一定要直接渲 mp4，可以改成：

```python
OUTPUT_MODE = "MP4"
```

但不建议在当前电脑上直接把 `RENDER_ANIMATION` 改成 `True`。

## PNG 序列合成视频

渲染完 PNG 后，可以在 Blender 里合成视频：

1. 打开 `Video Editing` 工作区。
2. `Add -> Image/Sequence`。
3. 进入本次输出目录，例如：

```text
MMD_Project/output/frames/render_YYYYMMDD_HHMMSS/
```

4. 选中所有 `frame_####.png`。
5. 如果有音乐，`Add -> Sound` 加入音乐。
6. 在 Output Properties 里设置：

```text
File Format: FFmpeg Video
Container: MPEG-4
Video Codec: H.264
Audio Codec: AAC
```

7. 输出到：

```text
MMD_Project/output/video/
```

8. 点击 `Render -> Render Animation` 合成最终视频。

## 重要开关

默认会在舞蹈前留 1 秒准备段。30fps 时，角色会在第 1-30 帧保持初始 T pose，动作、镜头和音乐从第 31 帧开始：

```python
PRE_ROLL_SECONDS = 1.0
```

如果不想要准备段：

```python
PRE_ROLL_SECONDS = 0.0
```

默认会在舞蹈开始帧做一次相机高度校准：优先以脖子/胸部骨骼高度为参考，把整段相机位置动画的 Z 轴整体平移。这样会保留镜头配布原本的推拉、旋转和运镜节奏，只修正整体高度：

```python
CAMERA_CALIBRATE_HEIGHT_ONCE = True
CAMERA_HEAD_BONE_CANDIDATES = ["首", "上半身2", "上半身", "Neck", "neck", "Chest", "chest", "UpperBody2", "UpperBody"]
CAMERA_HEAD_TARGET_OFFSET = (0.0, 0.0, 0.0)
```

如果画面还是太高，把 Z 偏移调低：

```python
CAMERA_HEAD_TARGET_OFFSET = (0.0, 0.0, -0.10)
```

如果画面太低，把 Z 偏移调高：

```python
CAMERA_HEAD_TARGET_OFFSET = (0.0, 0.0, 0.30)
```

如果你想完全使用镜头配布原本的高度，不做自动校准：

```python
CAMERA_CALIBRATE_HEIGHT_ONCE = False
```

如果你想让相机每一帧都持续看向头部，可以打开头部跟随。这个会更稳定对准脸，但会更明显改变配布镜头原本的朝向：

```python
CAMERA_LOOK_AT_HEAD = True
```

如果不想持续头部跟随：

```python
CAMERA_LOOK_AT_HEAD = False
```

保留原相机，不清掉原相机动画：

```python
CLEAR_EXISTING_CAMERA_ANIMATION = False
IMPORT_NEW_CAMERA_VMD = True
```

如果你想完全使用成品 `.blend` 里的原相机运动，不导入新镜头：

```python
IMPORT_NEW_CAMERA_VMD = False
```

如果你只想保留成品 `.blend` 原来的角色动作，不导入新 VMD：

```python
IMPORT_NEW_MOTION_VMD = False
```

如果导入后角色从第 1 帧不动，可能是 VMD 动作被导入到了很后面的帧。脚本默认会把新导入的角色动作平移到第 1 帧：

```python
NORMALIZE_IMPORTED_MOTION_TO_FRAME_START = True
```

如果设置了 `PRE_ROLL_SECONDS = 1.0`，它会自动把动作和新导入的镜头平移到准备段之后，而不是第 1 帧。

如果脚本提示标准 VMD 骨骼名缺失，说明这个 `.blend` 的骨架不适合直接导入任意 VMD。当前检查到的风险是左右肢体骨骼可能是 `腕.R / 腕.L`、`足.R / 足.L` 这类 Blender 风格名字，而很多 VMD 使用 `右腕 / 左腕 / 右足 / 左足`。这种情况需要 retarget 或骨骼名转换。

不建议直接打开这个开关，除非只是做测试：

```python
ALLOW_UNSAFE_VMD_IMPORT = True
```

如果你想替换音乐：

```python
REPLACE_MUSIC = True
```

如果想保留原音乐：

```python
REPLACE_MUSIC = False
```

如果耳朵、发饰、头发、尾巴被拉长或飞出去，先做诊断测试：

```python
DISABLE_RIGID_BODY_PHYSICS_FOR_TEST = True
```

如果这样之后身体动作正常、耳朵发饰不再飞，说明问题来自刚体/Joint/物理缓存，而不是 VMD 主动作。测试完再改回：

```python
DISABLE_RIGID_BODY_PHYSICS_FOR_TEST = False
```

脚本默认会重新启用刚体、重置刚体缓存，并提高刚体求解精度。为了避免长片段烘焙卡死，自动烘焙有最大帧数保护：

```python
RESET_RIGID_BODY_CACHE = True
BAKE_RIGID_BODY_PHYSICS = True
MAX_AUTO_BAKE_FRAMES = 1500
RIGID_BODY_SUBSTEPS = 10
RIGID_BODY_SOLVER_ITERATIONS = 20
```

如果动作长度超过 `MAX_AUTO_BAKE_FRAMES`，脚本会跳过自动烘焙并打印提示。你可以提高这个值，或者在 Blender 里手动烘焙刚体缓存。

如果耳朵看起来还是不明显晃，可以先确认它不是完全没动。运行：

```text
MMD_Project/scripts/inspect_ear_physics.py
MMD_Project/scripts/measure_ear_motion.py
```

当前模型检查结果显示耳朵刚体、Joint、骨骼 Copy Transforms 约束和烘焙缓存都存在；耳朵刚体在动画中确实有位移。如果你想让耳朵更明显地晃，可以打开：

```python
AMPLIFY_EAR_PHYSICS = True
```

它会降低耳朵动态刚体的质量和阻尼，让耳朵更容易摆动。太飘的话，把它改回：

```python
AMPLIFY_EAR_PHYSICS = False
```

如果脚本找不到 `MMD_Project`，手动填写：

```python
PROJECT_ROOT_OVERRIDE = r"D:\MMD\BlenderMMD\by_codex\MMD_Project"
```

如果你想让脚本直接打开这次的成品工程，可以填写：

```python
SOURCE_BLEND_PATH = r"D:\MMD\BlenderMMD\by_codex\MMD_Project\stage\臭猫猫的卧室 G1.blend"
```

这次检查到的角色骨架名是：

```python
ARMATURE_NAME_OVERRIDE = "MaoMao 3 PE_arm"
```

## 如果保存时报缺失贴图

有些成品 `.blend` 会保留作者电脑上的绝对贴图路径，例如：

```text
C:\Users\Administrator\Desktop\贴图\xxx.jpg
```

新版脚本保存前会：

- 关闭 Blender 的 Auto Pack
- 在 `MMD_Project/textures/`
- 在 `MMD_Project/stage/`
- 在 `MMD_Project/stage/tex/`
- 在 `D:\MMD\BlenderMMD\by_codex\贴图\`

按文件名查找同名贴图并自动重链接。

如果控制台仍显示缺失贴图，请把对应图片放进：

```text
MMD_Project/textures/
```

或：

```text
MMD_Project/stage/tex/
```

## 如果动作没有套上

先检查：

- 场景里是否有多个 Armature
- 脚本控制台显示的 `Selected main armature` 是不是角色骨架
- 新 VMD 是否适合这个角色的骨骼
- 原角色是否是 MMD/PMX 风格骨骼

如果场景里有多个骨架，脚本默认选骨骼数量最多的那个。选错时，下一版可以加 `ARMATURE_NAME_OVERRIDE`，手动指定角色骨架名字。

## 如果你想保留旧动作

把：

```python
CLEAR_EXISTING_ARMATURE_ACTIONS = True
```

改成：

```python
CLEAR_EXISTING_ARMATURE_ACTIONS = False
```

不过多数“换舞蹈动作”的场景建议清掉旧动作，否则新旧 Action 可能混在一起。
