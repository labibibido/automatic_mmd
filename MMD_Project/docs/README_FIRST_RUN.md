# MMD / VTuber 三渲二舞蹈视频：第一版使用说明

这是最小可运行版本，目标是先跑通：

- 导入角色
- 导入场景
- 导入 VMD 动作
- 可选导入 VMD 镜头
- 可选导入音乐
- 设置 Eevee、1080p、30fps
- 保存可修改的 `.blend`
- 准备 mp4 输出路径

第一版默认不自动开始渲染。先确认场景没问题，再把脚本里的 `RENDER_ANIMATION = False` 改成 `True`。

## 1. 文件放哪里

推荐第一轮使用：

- 角色：PMX
- 动作：VMD
- 场景：blend，其次 FBX
- 渲染：Eevee
- 输出：1080p / 30fps / mp4

把素材放到这些位置：

```text
MMD_Project/model/character/你的角色.pmx
MMD_Project/stage/你的场景.blend
MMD_Project/motion/你的动作.vmd
MMD_Project/camera/你的镜头.vmd
MMD_Project/music/你的音乐.mp3
```

`camera/` 和 `music/` 可以为空。没有镜头时，脚本会创建一个默认相机。

## 2. Blender 里怎么运行

1. 打开 Blender。
2. 确认 `mmd_tools` 已启用：
   - `Edit -> Preferences -> Add-ons`
   - 搜索 `mmd`
   - 勾选 `mmd_tools`
3. 打开 `Scripting` 工作区。
4. 在 Text Editor 里打开：

```text
MMD_Project/scripts/mmd_minimal_pipeline.py
```

5. 点击 `Run Script`。
6. 如果成功，会保存：

```text
MMD_Project/blend_files/mmd_test_scene.blend
```

如果 Blender 报错说找不到 `MMD_Project`，打开脚本顶部，把：

```python
PROJECT_ROOT_OVERRIDE = ""
```

改成你的项目绝对路径：

```python
PROJECT_ROOT_OVERRIDE = r"D:\MMD\BlenderMMD\by_codex\MMD_Project"
```

## 3. 如何开始真正渲染

第一次先不要渲染，确认模型、动作、镜头正常后，再打开脚本，把这一行：

```python
RENDER_ANIMATION = False
```

改成：

```python
RENDER_ANIMATION = True
```

重新运行脚本，输出视频会在：

```text
MMD_Project/output/video/mmd_test_render.mp4
```

## 4. 需要手动检查什么

第一版跑完后，请检查：

- 角色是否导入成功
- 场景比例是否正常
- 动作是否真的套到角色上
- 镜头是否对准角色
- 音乐是否从第 1 帧开始
- 材质是否太黑、太灰或丢贴图
- 衣服、头发、尾巴是否明显穿模

## 5. 如果动作穿模怎么办

常见原因：

- 模型体型和动作原作者使用的模型差异较大
- 肩、手腕、裙子、腿部权重不同
- 鞋跟高度、裙摆、长袖导致交叉

第一版处理方式：

- 先降低镜头距离，确认是不是局部穿模。
- 在 Dope Sheet / Graph Editor 里手调关键帧。
- 对严重穿模的衣服，后续版本再加 cloth 或 MMD 物理。
- 如果是 VRM/FBX 模型套 VMD，通常需要 retarget，不建议第一轮这样做。

## 6. 如果耳朵/尾巴不动怎么办

第一版只导入，不自动修物理。

PMX 模型：

- 如果原模型有 MMD rigid body / joint，mmd_tools 通常可以导入。
- 需要在 Blender 里检查 rigid bodies 是否存在。
- 后续阶段可以专门调 MMD 物理烘焙。

VRM 模型：

- 通常使用 VRM spring bone。
- 你的 Blender 5.1.2 需要先确认 VRM Add-on 是否兼容。
- VRM + VMD 需要 retarget，第一版不建议。

如果模型本身没有耳朵/尾巴骨骼：

- 需要加骨骼链。
- 给耳朵/尾巴刷权重。
- 再用 spring bone、jiggle bone 或 cloth 类方案做摆动。

## 7. 如果渲染太慢怎么办

先用这些设置：

- 1080p
- 30fps
- Eevee
- 输出测试片段，比如 300 帧
- 关闭高采样抗锯齿
- 不要一开始上 4K / 60fps

RTX 4060 Laptop 8GB 做 1080p Eevee 是合理的。复杂 PMX 物理和高面数场景会明显拖慢。

## 8. 如果模型变黑怎么办

常见原因：

- 贴图路径丢失
- 材质节点不兼容
- 法线方向异常
- 色彩管理过暗
- 场景灯光不足

先检查：

- `File -> External Data -> Find Missing Files`
- 材质贴图是否存在
- 是否有主光源
- 脚本是否成功添加 `Anime_Key_Sun`

## 9. 如果描边太粗或太细怎么办

第一版还没有加自动描边。下一阶段建议做两种描边方案：

- Freestyle：简单、稳定，适合测试。
- 反法线外壳描边：更像 MMD/VTuber，但需要按模型材质和比例细调。

第一版跑通后，我们再加描边控制参数。

## 10. PMX / VRM 怎么选

当前推荐：

- 想直接跳 MMD 动作：PMX
- 想保留 VTuber spring bone：VRM
- 想省 retarget 工作：PMX
- 想做直播/VRM 生态：VRM

你的第一版目标是 MMD 舞蹈 MV，所以建议先用 PMX。
