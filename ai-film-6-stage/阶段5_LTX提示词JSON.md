# 阶段5：制作 LTX 对应的 JSON

> **本阶段目标**：为每张切分好的分镜图写一个 LTX 视频 JSON（一张图 → 一个 JSON）。
> **输入**：阶段4 切分图（`06_分镜图片/片*.png`）+ 阶段1 台词（`01_剧本/Clip_设计.md`）
> **输出**：`07_LTX提示词/LTX_片01_描述.json`（每 Clip 一个）

---

## 阶段门禁（必须先执行）

- ⛔ **硬性规则**：完成本阶段任务之前，**禁止查看阶段6及以后的文件内容**。
- 进入本阶段先跑门禁检查：
  ```bash
  bash 流程门禁检查.sh 5 wk/项目名
  ```
- 输出「✅ 前置阶段全部完成」→ 继续本阶段。
- 输出「⛔ 禁止继续」→ **立即停止**，先完成前置阶段，不要继续读本文件。

## 0. 可独立运行说明

- 本文件是**独立阶段**，可单独执行。
- 前置条件：`06_分镜图片/` 切分图齐全（阶段4），`01_剧本/Clip_设计.md` 台词齐全（阶段1）。

## 1. 输入检查（缺一不可）

- [ ] `06_分镜图片/` 中单图数量 = Clip 总数，片号完整
- [ ] `01_剧本/Clip_设计.md` 每片台词完整（含标点）
- [ ] **已完整读取** JSON 生成规则：
      `../runninghub-api/scripts/ltx2.3-JSON生成规则.md`
      （以及同目录 `ltx2.3-JSON生成规则-硬性规定.md`）

## 2. 生成规则速记（必须遵守）

1. **单图单写模式**：一张图 → 一个 JSON，逐个处理，禁止批量；读一张图立即写对应 JSON。
2. **必须基于真实图片**：写 JSON 前先查看 `06_分镜图片/片XX.png` 真实画面，严格描述画面（构图/人物姿态/镜头），禁止凭文字脚本盲写。
3. **JSON 只保留 4 个核心字段**：`global_prompt`、`local_prompts`（字符串，非数组）、`segment_lengths`、`ltxv_add_guide_multi`（含 `frame_indices`、`strengths`）。
4. **台词格式**：`角色名字 says: '台词完整含标点'`，禁止裸台词。
5. **时长**：短台词 `segment_lengths: 176`（约5s），长台词 `200`（约6s）。
6. 避免 `[Frame X]` 特殊符号。

## 3. JSON 模板 `07_LTX提示词/LTX_片01_MissLi送别.json`

```json
{
  "global_prompt": "A warm and friendly school scene with young students (aged 10-12) in a modern Chinese elementary school. The students are wearing school uniforms: white shirts with blue stripes, blue shorts/skirts, and red scarves. The environment includes a bright classroom doorway with a corridor and blue lockers in background. The art style is cute 3D animation with soft lighting and pastel colors, suitable for children's educational content.",
  "local_prompts": "Miss Li (female teacher, 30s, warm smile, ponytail, glasses, green dress) stands at classroom doorway, smiling warmly and waving her right hand. Miss Li says: 'Class is over. See you tomorrow, boys and girls!' Warm afternoon lighting, school corridor background. audio: female teacher speaking clearly, warm tone, school ambience",
  "segment_lengths": "176",
  "ltxv_add_guide_multi": {
    "frame_indices": [0],
    "strengths": [1.0]
  }
}
```

## 4. local_prompts 编写结构

```
[角色描述] + [动作描述] + [角色名字 says: '台词内容'] + [场景描述] + [audio: 音频描述]
```

例：
```
Liu Tao (boy, 10-12, short black hair, school uniform with red scarf)
stands with Wang Bing, speaking enthusiastically and gesturing.
Liu Tao says: 'We are talking about our favourite subjects. What subject do you like best, Wang Bing?'
Sunny playground background, bright outdoor lighting.
audio: boy speaking enthusiastically, friendly tone, outdoor ambience
```

## 5. 产出核对

- [ ] `07_LTX提示词/` 中 JSON 数量 = Clip 总数
- [ ] 每个 JSON 可被 `json.load` 正常解析，仅含 4 个核心字段
- [ ] `local_prompts` 为字符串；`ltxv_add_guide_multi` 含 `frame_indices` 和 `strengths`
- [ ] 每个 JSON 对应的分镜图真实存在（`06_分镜图片/片XX.png`）
- [ ] 台词格式全部为「角色名 says: '…'」
- [ ] 已把 LTX JSON 登记到 `资产文件.md`
- [ ] 把 `流程进度.md` 中 `阶段5_LTX_JSON` 改为 ✅（之后才能进入阶段6）
- [ ] mac-say 播报：`LTX提示词已就绪`（≤30字）
