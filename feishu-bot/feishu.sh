#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${HOME}/.feishu/config.json"

# ===== 从项目 .env 加载凭证 =====
load_env() {
  local env_file=""
  [[ -f ".env" ]] && env_file=".env"
  [[ -z "$env_file" && -f "$(dirname "$0")/../.env" ]] && env_file="$(dirname "$0")/../.env"
  [[ -z "$env_file" ]] && return 0
  local tmp; tmp=$(grep -E '^FEISHU_' "$env_file" 2>/dev/null | sed 's/^/export /')
  [[ -n "$tmp" ]] && eval "$tmp" 2>/dev/null || true
}

# ===== 获取 chat_id =====
get_chat_id() {
  if [[ -n "${1:-}" ]]; then
    echo "$1"
  elif [[ -n "${FEISHU_CHAT_ID:-}" ]]; then
    echo "$FEISHU_CHAT_ID"
  else
    echo "❌ 未指定 chat_id。命令行传入或在 .env 中设置 FEISHU_CHAT_ID" >&2
    exit 1
  fi
}

# ===== 配置命令 =====
cmd_config() {
  mkdir -p "$(dirname "$CONFIG_FILE")"
  cat > "$CONFIG_FILE" <<EOF
{
  "app_id": "${1}",
  "app_secret": "${2}"
}
EOF
  echo "✅ 配置已保存到 $CONFIG_FILE"
}

# ===== 获取 token =====
get_token() {
  load_env
  local app_id="${FEISHU_APP_ID:-}"
  local app_secret="${FEISHU_APP_SECRET:-}"
  if [[ -z "$app_id" && -f "$CONFIG_FILE" ]]; then
    app_id=$(python3 -c "import json;print(json.load(open('${CONFIG_FILE}'))['app_id'])")
    app_secret=$(python3 -c "import json;print(json.load(open('${CONFIG_FILE}'))['app_secret'])")
  fi
  if [[ -z "$app_id" ]]; then
    echo "❌ 未找到凭证。请在项目 .env 中添加:" >&2
    echo "  FEISHU_APP_ID=cli_xxx" >&2
    echo "  FEISHU_APP_SECRET=xxx" >&2
    echo "或运行: feishu config --app-id xxx --app-secret xxx" >&2
    exit 1
  fi
  curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
    -H "Content-Type: application/json" \
    -d "{\"app_id\":\"${app_id}\",\"app_secret\":\"${app_secret}\"}" \
  | python3 -c "import sys,json;r=json.load(sys.stdin);print(r['tenant_access_token'])"
}

# ===== 上传文件（最大支持 30MB，设 180s 超时） =====
upload_file() {
  local token="$1" file="$2" file_type="$3"
  local filename="${4:-$(basename "$file")}"
  curl -s --max-time 180 -X POST "https://open.feishu.cn/open-apis/im/v1/files" \
    -H "Authorization: Bearer $token" \
    -F "file_type=$file_type" \
    -F "file_name=$filename" \
    -F "file=@$file" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['file_key'])"
}

# ===== 上传图片（最大支持 10MB） =====
upload_image() {
  local token="$1" file="$2"
  curl -s --max-time 60 -X POST "https://open.feishu.cn/open-apis/im/v1/images" \
    -H "Authorization: Bearer $token" \
    -F "image_type=message" \
    -F "image=@$file" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['image_key'])"
}

# ===== 发送消息 =====
send_msg() {
  local token="$1" chat_id="$2" msg_type="$3" content="$4"
  curl -s --max-time 60 -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "{\"receive_id\":\"${chat_id}\",\"msg_type\":\"${msg_type}\",\"content\":${content}}" \
  | python3 -c "import sys,json;r=json.load(sys.stdin);print('✅' if r['code']==0 else '❌ '+r['msg']);r['code']==0 or exit(1)"
}

# ===== 解析参数：首参数若为 chat_id 则提取，否则用默认 =====
is_chat_id() {
  [[ "${1:-}" =~ ^(oc_|ou_|om_|chat_) ]]
}

# ===== 文本 =====
cmd_text() {
  local chat_id text
  if is_chat_id "${1:-}"; then chat_id="$1"; shift; else chat_id=$(get_chat_id); fi
  text="${1:-}"
  local token; token=$(get_token)
  local content; content=$(python3 -c "import json,sys;print(json.dumps(json.dumps({'text':sys.argv[1]})))" "$text")
  send_msg "$token" "$chat_id" "text" "$content"
}

# ===== 文件 =====
cmd_file() {
  local chat_id file
  if is_chat_id "${1:-}"; then chat_id="$1"; shift; else chat_id=$(get_chat_id); fi
  file="${1:-}"
  [[ -f "$file" ]] || { echo "❌ 文件不存在: $file"; exit 1; }
  local token; token=$(get_token)
  local file_key; file_key=$(upload_file "$token" "$file" "stream")
  local content; content=$(python3 -c "import json;print(json.dumps(json.dumps({'file_key':'${file_key}'})))")
  send_msg "$token" "$chat_id" "file" "$content"
}

# ===== 图片 =====
cmd_image() {
  local chat_id file
  if is_chat_id "${1:-}"; then chat_id="$1"; shift; else chat_id=$(get_chat_id); fi
  file="${1:-}"
  [[ -f "$file" ]] || { echo "❌ 文件不存在: $file"; exit 1; }
  local token; token=$(get_token)
  local image_key; image_key=$(upload_image "$token" "$file")
  local content; content=$(python3 -c "import json;print(json.dumps(json.dumps({'image_key':'${image_key}'})))")
  send_msg "$token" "$chat_id" "image" "$content"
}

# ===== 视频 =====
cmd_media() {
  local chat_id video thumb=""
  if is_chat_id "${1:-}"; then chat_id="$1"; shift; else chat_id=$(get_chat_id); fi
  video="${1:-}"; thumb="${2:-}"
  [[ -f "$video" ]] || { echo "❌ 视频不存在: $video"; exit 1; }
  local token; token=$(get_token)

  local file_key; file_key=$(upload_file "$token" "$video" "mp4")

  local image_key=""
  if [[ -n "$thumb" ]]; then
    [[ -f "$thumb" ]] || { echo "❌ 封面不存在: $thumb"; exit 1; }
    image_key=$(upload_image "$token" "$thumb")
  elif command -v ffmpeg &>/dev/null; then
    local tmp_thumb; tmp_thumb=$(mktemp /tmp/feishu_thumb_XXXXX.png)
    ffmpeg -y -i "$video" -vframes 1 "$tmp_thumb" 2>/dev/null
    image_key=$(upload_image "$token" "$tmp_thumb")
    rm -f "$tmp_thumb"
  fi

  local content; content=$(python3 -c "
import json
d = {'file_key': '${file_key}'}
if '${image_key}': d['image_key'] = '${image_key}'
print(json.dumps(json.dumps(d)))
")
  send_msg "$token" "$chat_id" "media" "$content"
}

# ===== 语音 =====
cmd_audio() {
  local chat_id file
  if is_chat_id "${1:-}"; then chat_id="$1"; shift; else chat_id=$(get_chat_id); fi
  file="${1:-}"
  [[ -f "$file" ]] || { echo "❌ 文件不存在: $file"; exit 1; }
  local token; token=$(get_token)
  local file_key; file_key=$(upload_file "$token" "$file" "stream")
  local content; content=$(python3 -c "import json;print(json.dumps(json.dumps({'file_key':'${file_key}'})))")
  send_msg "$token" "$chat_id" "audio" "$content"
}

# ===== 固定格式发送 post（分隔线 + 标题 + 内容 + 可选文件） =====
cmd_post() {
  local chat_id=""
  if is_chat_id "${1:-}"; then chat_id="$1"; shift; fi
  [[ -z "$chat_id" ]] && chat_id=$(get_chat_id)

  local title="" content="" file="" thumb=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --title)   [[ -n "${2:-}" ]] && title="$2";   shift 2 ;;
      --content) [[ -n "${2:-}" ]] && content="$2"; shift 2 ;;
      --file)    [[ -n "${2:-}" ]] && file="$2";    shift 2 ;;
      --thumb)   [[ -n "${2:-}" ]] && thumb="$2";   shift 2 ;;
      *) echo "❌ 未知参数: $1（仅支持 --title --content --file --thumb）"; exit 1 ;;
    esac
  done

  [[ -z "$title" && -z "$content" && -z "$file" ]] && { echo "❌ 标题/内容/文件至少提供一个"; exit 1; }
  [[ -n "$file" && ! -f "$file" ]] && { echo "❌ 文件不存在: $file"; exit 1; }
  [[ -n "$thumb" && ! -f "$thumb" ]] && { echo "❌ 封面不存在: $thumb"; exit 1; }

  local token; token=$(get_token)

  local body="-----------"
  [[ -n "$title" ]]   && body+="\n标题：${title}"
  [[ -n "$content" ]] && body+="\n${content}"

  if [[ -n "$file" ]]; then
    local content_json
    content_json=$(python3 -c "import json,sys;print(json.dumps(json.dumps({'text':sys.argv[1]})))" "$body")
    send_msg "$token" "$chat_id" "text" "$content_json"

    case "${file,,}" in
      *.mp4|*.mov|*.avi|*.mkv|*.webm|*.m4v)
        local file_key image_key=""
        file_key=$(upload_file "$token" "$file" "mp4")
        if [[ -n "$thumb" ]]; then
          image_key=$(upload_image "$token" "$thumb")
        elif command -v ffmpeg &>/dev/null; then
          local tmp_thumb; tmp_thumb=$(mktemp /tmp/feishu_thumb_XXXXX.png)
          ffmpeg -y -i "$file" -vframes 1 "$tmp_thumb" 2>/dev/null
          image_key=$(upload_image "$token" "$tmp_thumb")
          rm -f "$tmp_thumb"
        fi
        local mcontent
        mcontent=$(python3 -c "
import json
d = {'file_key': '${file_key}'}
if '${image_key}': d['image_key'] = '${image_key}'
print(json.dumps(json.dumps(d)))
")
        send_msg "$token" "$chat_id" "media" "$mcontent"
        ;;
      *.png|*.jpg|*.jpeg|*.gif|*.webp|*.bmp)
        local image_key
        image_key=$(upload_image "$token" "$file")
        local icontent
        icontent=$(python3 -c "import json;print(json.dumps(json.dumps({'image_key':'${image_key}'})))")
        send_msg "$token" "$chat_id" "image" "$icontent"
        ;;
      *)
        local fkey
        fkey=$(upload_file "$token" "$file" "stream")
        local fcontent
        fcontent=$(python3 -c "import json;print(json.dumps(json.dumps({'file_key':'${fkey}'})))")
        send_msg "$token" "$chat_id" "file" "$fcontent"
        ;;
    esac
  else
    local content_json
    content_json=$(python3 -c "import json,sys;print(json.dumps(json.dumps({'text':sys.argv[1]})))" "$body")
    send_msg "$token" "$chat_id" "text" "$content_json"
  fi
}

# ===== 帮助 =====
cmd_help() {
  cat <<EOF
用法:
  feishu config --app-id <id> --app-secret <secret>   保存凭证
  feishu text    [chat_id] <文本>                      发送文本
  feishu file    [chat_id] <文件路径>                   发送文件
  feishu image   [chat_id] <图片路径>                   发送图片
  feishu media   [chat_id] <视频路径> [封面路径]         发送视频
  feishu audio   [chat_id] <音频路径>                   发送语音
  feishu post    [chat_id] [--title "标题"] [--content "内容"] [--file 路径] [--thumb 封面]   固定格式发送

  feishu post 每次发送固定格式:
    -----------          （分隔线，区分不同消息）
    标题：xxx            （可选）
    内容正文             （可选）
    文件/视频            （可选，自动识别类型：视频/图片/普通文件）

  chat_id 以 oc_/ou_ 开头时为指定群/用户，省略则从 .env 加载 FEISHU_CHAT_ID

配置来源（优先级从高到低）:
  1. 环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_CHAT_ID
  2. 项目 .env 文件
  3. feishu config 保存的配置文件 (~/.feishu/config.json)
EOF
}

# ===== 主入口 =====
main() {
  load_env
  [[ $# -lt 1 ]] && { cmd_help; exit 1; }
  case "$1" in
    config) shift; [[ "$1" == "--app-id" ]] && shift; local id="$1"; shift; [[ "$1" == "--app-secret" ]] && shift; local secret="$1"; cmd_config "$id" "$secret" ;;
    text)   shift; cmd_text   "$@" ;;
    file)   shift; cmd_file   "$@" ;;
    image)  shift; cmd_image  "$@" ;;
    media)  shift; cmd_media  "$@" ;;
    audio)  shift; cmd_audio  "$@" ;;
    post)   shift; cmd_post   "$@" ;;
    help|-h|--help) cmd_help ;;
    *) echo "❌ 未知命令: $1"; cmd_help; exit 1 ;;
  esac
}

main "$@"
