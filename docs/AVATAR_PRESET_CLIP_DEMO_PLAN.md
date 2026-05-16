# Avatar Preset Clip Demo Plan

## 背景

Task 07.6C 到 07.6D4 已验证“后端可信短文本 -> OpenAvatarChat/LiteAvatar sidecar -> TTS/口型”的实时链路。该链路适合路线摘要、识景提示、短句欢迎语，但不适合把 30 到 60 秒景点讲解全部放在现场 TTS 中合成：长文本实时 TTS 会带来首包延迟、分段停顿、首字吞音、口型同步漂移和断线后重试成本。

因此比赛演示里的固定景点讲解推荐走预存 clip：提前准备讲解音频，演示时只按白名单 `clip_id` 触发播放。这样可以把实时生成风险从主流程中移走，同时保持灵境后端仍然是唯一业务入口。

## API 契约

接口：

```http
POST /api/avatar/play-clip
```

请求：

```json
{
  "clip_id": "lingshan_buddha_intro_45s",
  "source": "attraction",
  "interrupt": true
}
```

字段：

| 字段 | 说明 |
| --- | --- |
| `clip_id` | 必填，只能是后端白名单中的预存讲解 ID。请求不能传任意音频路径。 |
| `source` | 可选，取值为 `route`、`attraction`、`vision`、`kiosk`、`admin`、`demo`。 |
| `interrupt` | 可选，演示层是否希望打断当前播报。 |

mock 响应示例：

```json
{
  "mode": "mock",
  "accepted": true,
  "message": "已进入数字人预存讲解播放队列",
  "fallback_reason": null,
  "metadata": {
    "clip_id": "lingshan_buddha_intro_45s",
    "title": "灵山大佛介绍",
    "attraction_name": "灵山大佛",
    "duration_seconds": 45,
    "policy": "preset_clip_whitelist_only",
    "llm_bypassed": true
  }
}
```

未知 `clip_id` 不抛 500，返回 `accepted=false`，并在 metadata 中给出可用白名单。

## Clip 白名单

当前后端白名单在 `backend/app/services/avatar_clip_player.py` 中，至少包含：

| clip_id | 标题 | 景点 | 时长 | 音频文件 |
| --- | --- | --- | --- | --- |
| `lingshan_buddha_intro_45s` | 灵山大佛介绍 | 灵山大佛 | 45 秒 | `external/avatar-clips/lingshan_buddha_intro_45s.wav` |
| `fan_gong_intro_45s` | 灵山梵宫介绍 | 灵山梵宫 | 45 秒 | `external/avatar-clips/fan_gong_intro_45s.wav` |
| `jiulong_guanyu_intro_30s` | 九龙灌浴介绍 | 九龙灌浴 | 30 秒 | `external/avatar-clips/jiulong_guanyu_intro_30s.wav` |

音频路径由后端根据白名单生成，并限制在 `D:\py\dota\external\avatar-clips\` 下。前端和外部请求只能传 `clip_id`，不能传文件路径。

## mock 与 sidecar 行为

`AVATAR_SPEAKER_MODE=mock` 或默认模式：

- 无 API Key 可运行。
- 即使 `external/avatar-clips` 中尚无真实 wav 文件，也返回 `mode=mock, accepted=true`。
- 响应 metadata 会标注 `audio_exists=false`，便于演示前检查资源是否齐全。

`AVATAR_SPEAKER_MODE=sidecar`：

- 如果音频文件不存在，返回 mock fallback，`accepted=true`，不让主后端崩溃。
- 如果 `AVATAR_SIDECAR_CLIP_PATH` 为空，返回 mock fallback，并标注 `clip_sidecar_adapter_pending=true`。
- 如果配置了 `AVATAR_SIDECAR_CLIP_PATH`，后端会先检查 sidecar `/readiness`，再用 HTTP JSON 调用 clip endpoint；调用失败时降级 mock，不返回 500。
- clip 播放不调用 LLM，不调用 RAG/Route/Vision/Analytics，不使用 OpenAvatarChat WebUI 的 `SendHumanText`。

Task 07.6F 已在 ignored sidecar spike 中补齐 `POST /lingjing/avatar/play-clip`，并完成程序化 WebRTC 验证：后端白名单 `clip_id` 指向 `external/avatar-clips` 下的 wav，OpenAvatarChat sidecar 将 wav 载入为 24 kHz mono `AVATAR_AUDIO`，LiteAvatar 继续输出 `AVATAR_AUDIO` / `AVATAR_VIDEO` 到 RTC。该验证没有使用 `SendHumanText`、`HUMAN_TEXT` 或 LLM。

2026-05-16 已补充人工 WebUI 验收：用户打开 `http://127.0.0.1:8282` 建立 RTC session 后，分别验证了短句实时播报和预存 clip 播放，两种播放都能正常发声，预存 clip 效果良好。仍需注意：这只能表述为本机演示环境中的 sidecar 表现层能力，不能表述为生产级数字人口型播报能力。

## 演示 SOP

1. 准备音频资源：

```powershell
cd D:\py\dota
New-Item -ItemType Directory -Force .\external\avatar-clips
```

将白名单 wav 文件放入 `external/avatar-clips`，不要提交音频文件、模型、缓存或日志。

2. 启动 mock 后端：

```powershell
cd D:\py\dota
$env:AVATAR_SPEAKER_MODE='mock'
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8025
```

3. 调用已知 clip：

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8025/api/avatar/play-clip `
  -ContentType 'application/json' `
  -Body '{"clip_id":"lingshan_buddha_intro_45s","source":"attraction","interrupt":true}'
```

4. 调用未知 clip，确认稳定错误：

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8025/api/avatar/play-clip `
  -ContentType 'application/json' `
  -Body '{"clip_id":"unknown_clip","source":"demo","interrupt":true}'
```

5. 如果使用 Task 07.6F 的 ignored sidecar clip endpoint，配置：

```powershell
$env:AVATAR_SPEAKER_MODE='sidecar'
$env:AVATAR_SIDECAR_BASE_URL='http://127.0.0.1:8282'
$env:AVATAR_SIDECAR_CLIP_PATH='/lingjing/avatar/play-clip'
```

然后打开 WebUI 建立 RTC session，或使用 aiortc smoke client 建立 `/webrtc/offer` session，再调用：

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8015/api/avatar/play-clip `
  -ContentType 'application/json' `
  -Body '{"clip_id":"lingshan_buddha_intro_45s","source":"attraction","interrupt":true}'
```

## 能力边界

- 这是 Avatar Preset Clip Demo 的后端契约和 mock-first 最小闭环，不是生产级数字人音频资产管理系统。
- 当前不接前端，不改变游客端/Kiosk/Admin 页面。
- 当前不读取原始资料包，不新增真实地图/GPS/客流/硬件能力。
- OpenAvatarChat + LiteAvatar 仍只作为数字人表现层 sidecar；灵境后端继续负责 RAG、路线、识景和运营逻辑。
- 真实预存音频驱动 LiteAvatar 的程序化 RTC 验证已完成，但 OpenAvatarChat patch 仍位于 ignored `external/OpenAvatarChat`，未进入主仓库。
- 人工 WebUI 视觉/听觉验收已完成：短句实时播报和预存 clip 播放都可用于本机演示。
- 真实讲解录音资产、批量 clip 管理、断线重连稳定性和生产化部署尚未完成。
