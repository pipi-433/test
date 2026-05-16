# Avatar Preset Clip LiteAvatar Result

## 结论

Task 07.6F 已完成一个 ignored sidecar spike，用于验证：

```text
clip_id -> preset wav -> /lingjing/avatar/play-clip -> AVATAR_AUDIO -> LiteAvatar -> WebRTC audio/video
```

程序化 WebRTC 验收通过：主后端 `POST /api/avatar/play-clip` 返回 `mode=sidecar, accepted=true`，OpenAvatarChat sidecar 返回 `adapter=liteavatar_trusted_clip_audio` 且 `llm_bypassed=true`，接收端拿到非静音 audio 和非空 LiteAvatar video frame。

2026-05-16 人工 WebUI 验收已补充完成：用户在 WebUI 中建立 RTC session 后，分别验证了短句实时播报和预存 clip 播放，两种播放都能正常发声，预存 clip 效果良好。因此当前能力可表述为“本机演示环境中，可信后端短文本和预存 wav 均可驱动 LiteAvatar 发声与口型表现”。

边界仍需保留：这仍是 ignored sidecar spike，不是生产级数字人能力；OpenAvatarChat + LiteAvatar 只作为表现层，不接管 RAG、路线、识景、运营分析或任何业务大脑决策。

## Sidecar Patch 点

以下改动都在 ignored 区域，不进入 git：

- `external/OpenAvatarChat/src/handlers/client/rtc_client/client_handler_rtc.py`
  - 新增 `POST /lingjing/avatar/play-clip`。
  - 请求只接受白名单 `clip_id` 和 `audio_path`。
  - `audio_path` 必须解析到 `D:\py\dota\external\avatar-clips\` 下，且必须是 `.wav`。
  - endpoint 选择指定 `session_id` 或当前 active session。
  - 使用 `librosa.load(..., sr=24000, mono=True)` 读取 wav。
  - 构造 `ChatDataType.AVATAR_AUDIO`，source 为 `lingjing_trusted_clip`，提交到现有 session。
- `external/avatar-clips/lingshan_buddha_intro_45s.wav`
  - 本地 ignored 测试 wav，用于 smoke，不提交。
- `external/run_logs/liteavatar_clip_received_audio.wav`
  - 程序化接收端捕获的 WebRTC 音频，不提交。
- `external/run_logs/liteavatar_clip_received_frame.png`
  - 程序化接收端捕获的 LiteAvatar 视频帧，不提交。

主仓库只补充演示配置和文档，不提交第三方源码、模型、音频或日志。

## wav 到 AVATAR_AUDIO 链路

LiteAvatar handler 消费 `ChatDataType.AVATAR_AUDIO`。其音频定义为：

```text
DataBundleEntry.create_audio_entry("avatar_audio", 1, 24000)
```

因此 preset clip endpoint 将 wav 转成 24 kHz mono float32 audio，然后提交：

```text
ChatData(
  source="lingjing_trusted_clip",
  type=ChatDataType.AVATAR_AUDIO,
  data=DataBundle(avatar_audio),
  finish_stream=True
)
```

后续仍走 OpenAvatarChat 已有 LiteAvatar handler，由 LiteAvatar 输出 `AVATAR_AUDIO` 和 `AVATAR_VIDEO` 到 WebRTC。该路径不经过 `AVATAR_TEXT`、TTS、`HUMAN_TEXT`、`SendHumanText` 或 LLM。

## 后端 play-clip 行为

主后端 `POST /api/avatar/play-clip` 仍只接受 `clip_id`，不接受外部任意音频路径。白名单和音频路径由 `backend/app/services/avatar_clip_player.py` 生成。

sidecar 模式配置：

```powershell
$env:AVATAR_SPEAKER_MODE='sidecar'
$env:AVATAR_SIDECAR_ADAPTER='http_json'
$env:AVATAR_SIDECAR_BASE_URL='http://127.0.0.1:8282'
$env:AVATAR_SIDECAR_CLIP_PATH='/lingjing/avatar/play-clip'
```

当 sidecar 在线、WebRTC session active 且 wav 存在时，主后端调用 sidecar clip endpoint。sidecar 不在线、clip 缺失或 endpoint 失败时，主后端降级 mock，不返回 500。

## 验证摘要

程序化 WebRTC smoke 使用 active session `lingjing-f-clip-capture` 调用主后端：

```json
{
  "backend_mode": "sidecar",
  "backend_accepted": true,
  "sidecar_adapter": "liteavatar_trusted_clip_audio",
  "sidecar_llm_bypassed": true,
  "frames_delta": {
    "audio": 359,
    "video": 179
  },
  "audio_samples_captured": 689280,
  "audio_peak": 21934,
  "audio_rms": 1362.21
}
```

捕获文件：

- `D:\py\dota\external\run_logs\liteavatar_clip_received_audio.wav`
- `D:\py\dota\external\run_logs\liteavatar_clip_received_frame.png`

日志证据显示本次 clip 播放路径出现 `RtcClient` 生产的 `AVATAR_AUDIO`，随后 LiteAvatar 输出 `AVATAR_AUDIO` 和 `AVATAR_VIDEO` stream；没有把 clip 作为 `HUMAN_TEXT` 进入 LLM 对话链路。

人工 WebUI 验收补充：

- 验收时间：2026-05-16
- 验收方式：打开 `http://127.0.0.1:8282`，建立 RTC session 后调用主后端 API。
- 短句实时播报：`POST /api/avatar/speak` 正常发声，整句播报已缓解早期“两字一顿”问题。
- 预存 clip 播放：`POST /api/avatar/play-clip` 正常播放，用户反馈“效果很好”。
- 验收结论：两种播放都没问题，可进入演示 SOP。

## 启动与调用

启动演示链路：

```powershell
cd D:\py\dota
& .\scripts\start_avatar_demo.ps1 -ForceLowMemory -OpenWebUI
```

WebUI 建立 RTC session 后检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8282/lingjing/avatar/sessions
```

调用主后端：

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8015/api/avatar/play-clip `
  -ContentType 'application/json' `
  -Body '{"clip_id":"lingshan_buddha_intro_45s","source":"attraction","interrupt":true}'
```

停止演示链路：

```powershell
& .\scripts\stop_avatar_demo.ps1
```

## 能力边界

- 已实现：本机 ignored sidecar spike 的 preset wav 到 LiteAvatar WebRTC audio/video 程序化验证。
- 已完成：短句实时播报和预存 clip 播放的人工 WebUI 发声/口型观感验收。
- 已验证：主后端只接收 `clip_id`，sidecar endpoint 校验 wav 必须在 `external/avatar-clips` 下。
- 已验证：不走 `SendHumanText`、`HUMAN_TEXT` 或 LLM。
- 未完成：真实讲解录音资产、批量音频资源管理、生产化稳定性、前端按钮接入。
- 未完成：把 ignored OpenAvatarChat patch 整理为可审查的上游补丁或独立 sidecar 包。
