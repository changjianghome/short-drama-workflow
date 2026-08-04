#!/usr/bin/env bash
# 阶段门禁检查：未完成前置阶段，禁止进入/查看当前及下一阶段内容
# 用法: bash 流程门禁检查.sh <阶段号1-6> [项目目录]
# 例:   bash 流程门禁检查.sh 3 wk/项目名
set -u

STAGE=$1
PROJ=${2:-$(dirname "$(realpath "$0")")}
STATE_FILE="$PROJ/流程进度.md"

if [ ! -f "$STATE_FILE" ]; then
  echo "❌ 找不到 $STATE_FILE，请先完成阶段1（含建目录与流程进度文件）。"
  echo "⛔ 禁止继续。"
  exit 1
fi

STAGE_NAMES=( "阶段1_准备" "阶段2_母图" "阶段3_四宫格提示词" "阶段4_四宫格制作" "阶段5_LTX_JSON" "阶段6_视频生成" )

# 阶段1 特殊：只需进度文件存在即可
if [ "$STAGE" -eq 1 ]; then
  echo "✅ 阶段1 无前置，可开始。"
  exit 0
fi

# 检查 阶段1 .. 阶段N-1 是否全部 ✅
for ((i=1; i<STAGE; i++)); do
  key="${STAGE_NAMES[$((i-1))]}"
  line=$(grep "^${key}=" "$STATE_FILE" | tail -1)
  if echo "$line" | grep -q "✅"; then
    echo "✅ $key 已完成"
  else
    echo "❌ $key 未完成（当前状态：${line:-未登记}）"
    echo "⛔ 必须先完成阶段$i，禁止进入阶段$STAGE，禁止查看阶段$STAGE及后续内容。"
    exit 1
  fi
done

echo "✅ 前置阶段全部完成，可进入阶段$STAGE。"
