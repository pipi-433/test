# Task 07.6D2 LiteAvatar Trusted Text Lip-Sync Spike Result

日期：2026-05-16

## 目标

验证“灵境后端可信短文本 -> OpenAvatarChat/LiteAvatar 发声 + 口型”的最小入口，并确认该入口不经过 `SendHumanText`、`HUMAN_TEXT` 或 LLM 对话链路。

## 当前结论

本轮已在 ignored 的 `external/OpenAvatarChat` 中实现一个进程内 spike patch：

- `POST /lingjing/avatar/speak`
- `GET /lingjing/avatar/sessions`
- 入口把灵境后端传入的可信文本直接提交为 `ChatDataType.AVATAR_TEXT`
- 提交前可发送 `ChatSignalType.INTERRUPT`
- metadata 标记 `llm_bypassed=true`

但本机本轮没有完成“LiteAvatar 视频人像实际发声 + 对口型”的现场验证。阻塞点不是主后端 adapter，而是 patched OpenAvatarChat 重新启动时，LiteAvatar worker 在 Windows multiprocessing spawn 阶段报错：

```text
PermissionError: [WinError 5] 拒绝访问。
```

因此当前不能声称已经看到 LiteAvatar WebUI 中视频人像按后端文本完成口型播报。

## 关键源码链路

调查结论：

1. WebUI `SendHumanText` 会进入 `RtcStream.set_channel()`，再调用 `client_session_delegate.put_data(EngineChannelType.TEXT, ..., loopback=True)`。
2. `RtcClientSessionDelegate.put_data()` 将 `EngineChannelType.TEXT` 映射为 `ChatDataType.HUMAN_TEXT`。
3. `HUMAN_TEXT` 后续进入 LLM/TTS/avatar 对话链路，因此不能作为可信播报入口。
4. OpenAvatarChat 已存在后半段纯表现链路：
   - `ChatDataType.AVATAR_TEXT`
   - TTS handler 消费 `AVATAR_TEXT` 并输出 `AVATAR_AUDIO`
   - LiteAvatar handler 消费 `AVATAR_AUDIO` 并输出 `AVATAR_AUDIO` / `AVATAR_VIDEO`
   - RTC client 再把 audio/video 输出到 WebRTC tracks
5. 当前缺口是 RTC client 原本没有对外暴露“提交 `AVATAR_TEXT`”的本地 HTTP 入口，也没有在 outputs 中声明可提交的 `AVATAR_TEXT` output definition。

## Spike Patch 摘要

patch 文件位于 ignored 第三方目录：

```text
external/OpenAvatarChat/src/handlers/client/rtc_client/client_handler_rtc.py
```

主要改动：

- 增加 `LingjingTrustedSpeakRequest`。
- 增加 `RtcClientSessionDelegate.put_avatar_text()`。
- 给 `ClientHandlerRtc` 增加 `avatar_text_output_definition`。
- 在 `create_handler_detail()` 的 outputs 中声明 `ChatDataType.AVATAR_TEXT`。
- 在 `on_setup_app()` 注册：
  - `GET /lingjing/avatar/sessions`
  - `POST /lingjing/avatar/speak`
- endpoint 选择请求中的 `session_id`，或最近一个 active RTC session。
- 没有 active session 时返回 `accepted=false`，不抛 500。

该 patch 不在 git 提交范围内；`external/` 仍应保持 ignored。

## Endpoint 契约

请求：

```json
{
  "text": "您好，我是灵境导游，正在为您播报路线摘要。",
  "emotion": "happy",
  "source": "route",
  "interrupt": true,
  "session_id": "<optional active session id>"
}
```

成功响应形态：

```json
{
  "accepted": true,
  "mode": "sidecar",
  "message": "trusted text accepted for LiteAvatar speech",
  "metadata": {
    "adapter": "liteavatar_trusted_avatar_text",
    "llm_bypassed": true,
    "session_id": "<active session id>",
    "latency_ms": 0
  }
}
```

无 active RTC session 响应形态：

```json
{
  "accepted": false,
  "mode": "sidecar",
  "message": "no active RTC session; open the LiteAvatar WebUI first",
  "metadata": {
    "adapter": "liteavatar_trusted_avatar_text",
    "llm_bypassed": true,
    "session_id": null
  }
}
```

## 启动命令

如果 Windows multiprocessing 问题已解决，可用如下命令启动 patched OpenAvatarChat：

```powershell
cd D:\py\dota\external\OpenAvatarChat
$env:PATH='D:\py\dota\external\OpenAvatarChat\.runtime-dll;D:\py\dota\.sidecar-tools\Scripts;' + $env:PATH
D:\py\dota\.sidecar-tools\Scripts\uv.exe run --python 3.11 src/demo.py --host 127.0.0.1 --port 8282 --config config/local_sidecar_probe.yaml
```

WebUI：

```text
http://127.0.0.1:8282/ui/index.html
```

灵境后端指向该 endpoint：

```powershell
$env:AVATAR_SPEAKER_MODE='sidecar'
$env:AVATAR_SIDECAR_ADAPTER='http_json'
$env:AVATAR_SIDECAR_BASE_URL='http://127.0.0.1:8282'
$env:AVATAR_SIDECAR_SPEAK_PATH='/lingjing/avatar/speak'
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8015
```

调用：

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8015/api/avatar/speak -ContentType 'application/json' -Body '{"text":"您好，我是灵境导游，正在为您播报路线摘要。","emotion":"happy","source":"route","interrupt":true}'
```

## 验证结果

- `client_handler_rtc.py` 已通过 `python -m py_compile`。
- 旧的 `127.0.0.1:8282` OpenAvatarChat 进程来自 patch 前版本，`/readiness` 返回 ok，但 `/lingjing/avatar/speak` 返回 404。
- 停止旧进程后，使用 venv Python 和 `uv run --python 3.11` 均无法让 patched OpenAvatarChat 监听成功。
- 失败原因一致：LiteAvatar worker 在 Windows multiprocessing spawn 阶段 `WinError 5`。

## 是否绕过 LLM

代码路径设计上绕过 LLM：

- 不使用 `SendHumanText`
- 不提交 `ChatDataType.HUMAN_TEXT`
- 直接提交 `ChatDataType.AVATAR_TEXT`
- endpoint 只接收后端传入文本，不调用 RAG、Route Planner、Vision、Analytics 或 LLM

但因为 patched OAC 未能启动到可访问状态，本轮尚未完成端到端口型验证。

## 降级行为

灵境主后端仍保留现有策略：

- `AVATAR_SPEAKER_MODE=mock`：无 API Key 可运行，返回 `accepted=true`。
- `AVATAR_SPEAKER_MODE=sidecar` 且 sidecar 不在线：不 500，降级 mock。
- `AVATAR_SPEAKER_MODE=sidecar` 且 sidecar 返回 `accepted=false`：不 500，降级 mock，并记录 `fallback_reason`。

## 下一步建议

1. 优先解决 OpenAvatarChat LiteAvatar worker 的 Windows multiprocessing `WinError 5`，否则无法验证真实视频口型。
2. 若继续 patch OAC，最小位置仍是 `client_handler_rtc.py`；不要改 WebUI `SendHumanText` 验收路径。
3. 在能稳定启动 patched OAC 后，先打开 WebUI 建立 RTC session，再调用 `/lingjing/avatar/sessions` 确认 active session。
4. 再通过灵境后端 `/api/avatar/speak` 指向 `/lingjing/avatar/speak` 验证视频人像是否按后端文本发声并对口型。
5. 若 TTS 依赖真实厂商 Key，Key 只放本机 ignored `.env` 或当前 shell 环境，不能写入 tracked 文件。

## 2026-05-16 D3 追加结果

D3 已确认 D2 的 `WinError 5` 不是文件权限、模型目录、runtime DLL 或端口占用的原发错误。完整日志显示，在 `PermissionError: [WinError 5]` 之前，父进程已经先报：

```text
llm.openai_compatible.llm_handler_openai_compatible:load - api_key is required in config/xxx.yaml, when use handler_llm
```

父进程因官方对话配置缺少 LLM API key 退出后，LiteAvatar 子进程仍处在 Windows multiprocessing spawn / pipe handle 反序列化阶段，于是表现为 `DuplicateHandle` access denied。`WinError 5` 是父进程提前退出后的二次症状。

### D3 修复/绕过方式

在 ignored sidecar 内新增纯表现层配置：

```text
external/OpenAvatarChat/config/lingjing_trusted_liteavatar_edge_tts.yaml
```

该配置只加载：

- `RtcClient`
- `InterruptHandler`
- `Edge_TTS`
- `LiteAvatar`

它不加载 `LLMOpenAICompatible`、`SenseVoice` 或 `SileroVad`，因此 trusted speak 验收不再需要 LLM API key，也不会把后端可信文本送进 OpenAvatarChat 对话链路。

同时在 ignored patch 中补充：

```text
DataBundle metadata: avatar_text_end=true
```

这样 Edge TTS 能把一次性 `AVATAR_TEXT` 当作最终播报文本处理。

本轮还在 ignored `.venv` 中安装了轻量依赖 `edge-tts`，pip cache 限定在：

```text
external/.pip-cache
```

未做全局安装，未写入真实 API key。

### D3 启动验证

启动命令：

```powershell
cd D:\py\dota\external\OpenAvatarChat
$env:PATH='D:\py\dota\external\OpenAvatarChat\.runtime-dll;D:\py\dota\.sidecar-tools\Scripts;' + $env:PATH
D:\py\dota\.sidecar-tools\Scripts\uv.exe run --python 3.11 src/demo.py --host 127.0.0.1 --port 8282 --config config/lingjing_trusted_liteavatar_edge_tts.yaml
```

验证结果：

- `/liveness` 200
- `/readiness` 200
- `/openavatarchat/initconfig` 200
- LiteAvatar worker 日志出现 `Avatar process is ready`
- `/lingjing/avatar/sessions` 可返回 active session

### D3 trusted speak 验收

由于当前执行环境没有可用的 Playwright/Puppeteer 控制器，本轮使用 `aiortc` 建立等价的本地 WebRTC session，而不是手动点击 WebUI。该 session 通过同一个 `/webrtc/offer` 入口连接 OpenAvatarChat，并接收远端 audio/video tracks。

OAC 直接验收：

- session id: `lingjing-d3-aiortc-media`
- `/lingjing/avatar/sessions` 返回该 active session
- `POST /lingjing/avatar/speak` 返回 `accepted=true`
- 本地 WebRTC 客户端收到远端 `audio=45` 帧、`video=24` 帧

主后端联调验收：

- session id: `lingjing-d3-backend-smoke2`
- `/api/avatar/speak` 返回 `mode=sidecar`, `accepted=true`
- OAC sidecar response metadata: `adapter=liteavatar_trusted_avatar_text`, `llm_bypassed=true`
- 本地 WebRTC 客户端收到远端 `audio=51` 帧、`video=25` 帧

关键日志链路：

```text
Starting session lingjing-d3-backend-smoke2
Received signal: STREAM_BEGIN for stream: ChatDataType.AVATAR_TEXT
Received signal: STREAM_END for stream: ChatDataType.AVATAR_TEXT
Received signal: STREAM_BEGIN for stream: ChatDataType.AVATAR_AUDIO
Received signal: STREAM_BEGIN for stream: ChatDataType.AVATAR_VIDEO
```

日志中未出现该 trusted speak 请求走 `HUMAN_TEXT` 或 LLM handler。当前结论是：本机已通过 WebRTC 程序化验收“后端可信文本 -> LiteAvatar audio/video 输出”，并可证明绕过 LLM。视觉 WebUI 人工观察仍建议作为下一轮演示确认项。

### D3 稳定性备注

一次 WebRTC 客户端关闭后，OpenAvatarChat 偶发出现 HTTP 响应超时，需要重启 sidecar 后再验收。这不影响主后端降级：sidecar 超时或离线时 `/api/avatar/speak` 返回 `mode=mock`, `accepted=true`，不抛 500。

## 2026-05-16 D4 追加：WebUI 人工验收边界与 SOP

D4 已再次完成程序化 WebRTC 验收：

- session id: `lingjing-d4-backend-smoke`
- 主后端 `/api/avatar/speak` 返回 `mode=sidecar`, `accepted=true`
- 后端 POST 总耗时约 `229ms`
- sidecar response latency `79.61ms`
- WebRTC 接收端收到 `audio=49` 帧、`video=25` 帧
- 日志显示 `AVATAR_TEXT -> AVATAR_AUDIO -> AVATAR_VIDEO`

但 D4 未能由我独立完成人工肉眼 WebUI 视觉确认。已尝试打开默认浏览器到 `/ui/index.html`，但该页面不会自动建立 RTC session；当前执行环境的 browser automation/screenshot 工具也无法稳定返回该 WebUI 的截图或 DOM。因此当前不能写成“已人工看到视频人像发声 + 对口型”。

新增演示前检查脚本：

```text
scripts/avatar_sidecar_healthcheck.ps1
```

详细人工验收待确认清单、健康检查和重启 SOP 见 `docs/AVATAR_LITEAVATAR_WEBUI_ACCEPTANCE.md`。
