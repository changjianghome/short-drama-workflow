# LTX 视频 JSON 生成 — 硬性规定清单

> 此文件仅列出必须遵守的硬性规定，无详细说明。详细解释见 `JSON生成规则.md`。

---

## 1. 执行规则

- [ ] **必须**基于真实四宫格图片写 JSON，禁止仅凭文字盲写
- [ ] **单图单写模式**：读取 `*-*.png` → 立即写 `*-*.json`，禁止批量读多张再写
- [ ] JSON 中的 prompt 必须严格匹配图片实际画面，图片有偏离则 prompt 跟着偏离

## 2. 工作流参数（不可变更）

| 参数 | 值 |
|---|---|
| FPS | 30（固定） |
| num_guides | ≤ 4 |
| total_frames 上限 | < 900（< 30 秒） |
| total_frames 下限 | ≥ 540（≥ 18 秒，N=1 时以上限 240 帧为准） |
| 每段帧数范围 | 30–240 帧 |
| 收尾段帧数范围 | 30–240 帧 |
| 中间 frame_indices | 必须能被 8 整除（末段起始索引除外，N=1 时无需满足） |

### W3 数据自洽性三大铁律
- `sum(segment_lengths) == 总帧数`
- `frame_indices[i] == sum(segment_lengths[0:i])`
- `frame_indices[-1] + segment_lengths[-1] == 总帧数`
- segment_lengths 与 frame_indices 必须来自同一配对单元，禁止跨单元混搭
- 禁止先定 frame_indices 再反推 segment_lengths

## 3. 时长分配

- **宁长勿短**：所有"可长可短"一律取上界
- 速算公式：`时长(秒) ≈ (台词字数 ÷ 2.5) + (动作节点数 × 2.0)`
- 公式结果是**下限**，只能加不能减
- 情感重音/收尾/含台词镜头：额外加至少 1s
- 禁止为凑上限压缩非关键分镜

## 4. LTX 2.3 硬约束

- **H0**: num_guides ≤ 4
- **H1**: 单段 ≤ 240 帧
- **H2**: 单段连续动作阶段 ≤ 3
- **H3**: 单段禁止两种主光源/主色调
- **H5**: 帧索引与段长对齐
- **H6**: 收尾段 30–240 帧
- **H9**: 必须做视觉连续性评估，按档位调 strength + 写 local_prompts + 追加 negative_prompt

## 5. 提示词要求

### 详细度
- 每段 ≥ 120 英文单词（含台词段 ≥ 140）
- 整段 local_prompts ≥ 480 英文单词（段数较少时按比例折算：N=3 ≥ 360, N=2 ≥ 240, N=1 ≥ 120）
- 覆盖至少 4 个细节层次（面部/手部/身体姿态/服装道具/环境光线/声音）
- 写"过程"而非"状态"

### 结构
- 每段：`Shot N + 景别 + 主动 camera + 角色名(男/女) + 物理动作 + 台词(中文) + 光源 + audio:...`
- 非首段以 `Continuing seamlessly from the previous moment...` 开头
- 非末段末尾：`audio:` + 镜头转换描写 + 下一画面内容
- 用时间连接词（then/as/while）串联动作，禁止罗列
- 物理动作替代情绪标签（show don't tell）
- 禁止剪辑暗示词：cut to / meanwhile / next scene / transitioning to 等

## 6. 角色规则

- 所有角色用 `中文名(男/女)` 格式，全文统一
- global_prompt 首次出现写全称 `中文名(男/女) (完整英文外貌)`
- 禁止使用 she/he/那女孩/那男孩
- 多角色同镜头必须描述位置关系

## 7. 台词规则
- 分镜提示词必须包含原剧本的台词,使用"人物名字(性别)说:..."这样的格式
- **台词必须保留剧本原始语言**，禁止翻译成英文
- 英文单引号 `''` 包裹中文原文
- TTS 清洗：仅允许 `。 ， ？ ！`
- 无台词段标注 no dialogue / silent moment / ambient only
- lipsync=true 时柔化嘴部：lips parted softly

## 8. 输出格式

- 合法 JSON，6 字段：global_prompt / local_prompts / segment_lengths / ltxv_add_guide_multi / negative_prompt / 分段
- 用 ```json 包裹
- JSON 之外不要任何解释、前言、后记
- 全部字符串单行无换行
- negative_prompt 必须追加 H9.4 的 16 个反硬切关键词
