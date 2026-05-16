# Task 07.6D Trusted Speak Bridge Result

## 结论

本轮已实现一个 ignored sidecar bridge 原型：

```text
灵境 FastAPI 已生成可信短文本
-> POST /api/avatar/speak
-> AVATAR_SIDECAR_ADAPTER=http_json
-> external/lingjing-avatar-bridge/trusted_speak_bridge.py
-> dry-run 或 Windows SAPI 本机发声
```

该 bridge 只接收后端传入的文本，不调用 LLM，不调用 RAG、Route Planner、Vision 或 Analytics。它用于验证“后端可信文本可以经由 sidecar adapter 进入播报层”，不是让 OpenAvatarChat 回答问题。

当前可以验证到：主后端 `http_json` adapter 能稳定调用本地 trusted bridge，并在 bridge 在线时返回 `mode="sidecar"`、`accepted=true`；bridge 离线时主后端稳定降级到 mock，不返回 500。

当前尚未验证到：OpenAvatarChat WebUI 中的 LiteAvatar 真实视频人像已经按该文本口型播报。原因是当前官方 RTC client 对外文本入口只映射为 `HUMAN_TEXT`，会进入对话链路；纯播报需要在 sidecar 进程内新增 `AVATAR_TEXT` 注入入口。

## 协议调查结论

OpenAvatarChat 内部后半段管线存在：

```text
AVATAR_TEXT -> TTS handler -> AVATAR_AUDIO -> LiteAvatar handler -> AVATAR_AUDIO/AVATAR_VIDEO -> RTC/WebUI
```

但当前 WebUI 外部文本发送路径是：

```text
WebUI sendText()
-> RTCDataChannel SendHumanText
-> RtcStream.set_channel()
-> RtcClientSessionDelegate.put_data(EngineChannelType.TEXT)
-> ChatDataType.HUMAN_TEXT
-> LLM/TTS/avatar 对话链路
```

因此 `SendHumanText` 不是可信播报入口，不能作为 `/api/avatar/speak` 的验收路径。

要真正触发 LiteAvatar 按后端文本发声，最小上游改动建议是：

- 在 `external/OpenAvatarChat/src/handlers/client/rtc_client/client_handler_rtc.py` 给 `ClientHandlerRtc` 增加 `AVATAR_TEXT` output definition。
- 给 `RtcClientSessionDelegate` 增加只提交 `ChatDataType.AVATAR_TEXT` 的方法，不经过 `EngineChannelType.TEXT -> HUMAN_TEXT` 映射。
- 在 `ClientHandlerRtc.on_setup_app()` 注册本地 HTTP endpoint，例如 `POST /lingjing/avatar/speak`，找到当前已建立 session 的 delegate 后提交 `AVATAR_TEXT`。
- 如果有多个会话，请求必须带 `session_id` 或由 bridge 明确选择当前活动 session。

上述改动应留在 ignored sidecar 区或作为上游补丁，不进入灵境主业务大脑。

## Bridge 接口

启动：

```powershell
cd D:\py\dota
python .\external\lingjing-avatar-bridge\trusted_speak_bridge.py --host 127.0.0.1 --port 8022 --speaker dry-run
```

Windows 本机发声 smoke：

```powershell
cd D:\py\dota
python .\external\lingjing-avatar-bridge\trusted_speak_bridge.py --host 127.0.0.1 --port 8022 --speaker windows-sapi
```

接口：

```http
POST http://127.0.0.1:8022/lingjing/avatar/speak
Content-Type: application/json
```

请求：

```json
{
  "text": "您好，我是灵境导游，正在为您播报路线摘要。",
  "emotion": "happy",
  "source": "route",
  "interrupt": true
}
```

成功响应：

```json
{
  "accepted": true,
  "mode": "sidecar",
  "message": "trusted text accepted for avatar speech",
  "metadata": {
    "adapter": "trusted_speak_bridge",
    "speaker": "dry-run",
    "llm_bypassed": true,
    "text_chars": 22,
    "latency_ms": 0
  }
}
```

## 主后端联调配置

```powershell
$env:AVATAR_SPEAKER_MODE='sidecar'
$env:AVATAR_SIDECAR_ADAPTER='http_json'
$env:AVATAR_SIDECAR_BASE_URL='http://127.0.0.1:8022'
$env:AVATAR_SIDECAR_SPEAK_PATH='/lingjing/avatar/speak'
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8015
```

主后端请求示例：

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8015/api/avatar/speak `
  -Method Post `
  -ContentType 'application/json' `
  -Body '{"text":"您好，我是灵境导游，正在为您播报路线摘要。","emotion":"happy","source":"route","interrupt":true}'
```

## 降级策略

- `AVATAR_SPEAKER_MODE=mock`：不需要任何 API Key，直接返回 `accepted=true`。
- `AVATAR_SPEAKER_MODE=sidecar` 但 bridge 离线：主后端返回 mock fallback，不影响 QA、路线、识景、后台或分享页。
- bridge 返回错误或超时：主后端不抛 500，仍降级 mock。
- 当前 React/SVG/CSS mock 数字人和浏览器 TTS fallback 必须继续保留。

## 能力边界

已实现：

- 后端可信文本到本地 HTTP JSON bridge。
- bridge 干跑接受文本。
- bridge 在 Windows 上可用系统 SAPI 做本机发声 smoke。
- 主后端在线/离线降级均稳定。

未实现：

- 真实 OpenAvatarChat WebUI 会话内的 `AVATAR_TEXT` 注入。
- LiteAvatar 视频人像按该文本实时口型播报。
- 多会话 session 选择与鉴权。

后续若继续推进，应在 ignored OpenAvatarChat sidecar 内做最小 `AVATAR_TEXT` endpoint 补丁，并继续禁止 `SendHumanText` 作为可信播报入口。

## 2026-05-16 D2 addendum: LiteAvatar lip-sync endpoint spike

An ignored spike patch has been added under:

```text
external/OpenAvatarChat/src/handlers/client/rtc_client/client_handler_rtc.py
```

It registers `GET /lingjing/avatar/sessions` and `POST /lingjing/avatar/speak`, then submits trusted backend text as `ChatDataType.AVATAR_TEXT` instead of `HUMAN_TEXT`. The endpoint design explicitly avoids `SendHumanText` and marks response metadata with `llm_bypassed=true`.

The patch passed Python syntax compilation, but the patched OpenAvatarChat service could not be restarted to verify actual LiteAvatar video lip-sync. Startup is currently blocked in the LiteAvatar worker Windows multiprocessing spawn phase:

```text
PermissionError: [WinError 5] 拒绝访问。
```

So the current state is: trusted `AVATAR_TEXT` endpoint patch exists in ignored sidecar source, but this run has not proven real LiteAvatar WebUI speech + lip-sync. Full D2 notes are in `docs/AVATAR_LITEAVATAR_LIPSYNC_SPIKE_RESULT.md`.

## 2026-05-16 D3 addendum: backend trusted text reached LiteAvatar audio/video

D3 identified the D2 startup blocker as an LLM API-key configuration issue in the official dialogue preset, with Windows multiprocessing `WinError 5` as a secondary child-process symptom.

The ignored OpenAvatarChat sidecar now has a pure presentation config:

```text
external/OpenAvatarChat/config/lingjing_trusted_liteavatar_edge_tts.yaml
```

Using that config, the trusted path was verified programmatically:

```text
Lingjing backend /api/avatar/speak
-> http_json adapter
-> OpenAvatarChat /lingjing/avatar/speak
-> ChatDataType.AVATAR_TEXT
-> Edge_TTS AVATAR_AUDIO
-> LiteAvatar AVATAR_VIDEO / AVATAR_AUDIO
-> WebRTC receiver
```

The main backend returned `mode="sidecar"` and the local WebRTC receiver observed remote audio/video frames. The OAC log for the request shows `AVATAR_TEXT`, `AVATAR_AUDIO`, and `AVATAR_VIDEO`; it does not show `HUMAN_TEXT` or an LLM handler for the trusted speak request.
