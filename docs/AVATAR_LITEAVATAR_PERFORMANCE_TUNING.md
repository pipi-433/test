# LiteAvatar Performance Tuning

## 2026-05-16 Receive-Only Viewer Update

Task 07.6I replaces the 07.6H iframe panel with a local React WebRTC viewer in the visitor `/` guide tab and Kiosk `/kiosk` avatar area.

The new frontend path:

- Does not call `navigator.mediaDevices.getUserMedia`.
- Does not request camera or microphone permission.
- Calls only the Lingjing backend signaling proxy: `POST /api/avatar/webrtc/offer`.
- Keeps trusted speech and preset clips on the existing backend APIs: `POST /api/avatar/speak` and `POST /api/avatar/play-clip`.
- Does not use `SendHumanText`, `HUMAN_TEXT`, or any LLM path for trusted speech/clip playback.

Current OpenAvatarChat/FastRTC is configured as `mode="send-receive", modality="audio-video"`. A pure recvonly SDP can receive an answer but does not create an active Lingjing RTC session in the current sidecar. To avoid camera/microphone prompts while still satisfying that session bootstrap, the viewer creates local synthetic tracks only: a silent Web Audio track and a blank 16x16 canvas video track. These tracks contain no real visitor media and exist only to let the sidecar create the RTC session; the useful output remains LiteAvatar audio/video from the sidecar.

The sidecar remains an ignored presentation-layer spike. RAG, route planning, vision, analytics, and speech/clip trigger policy stay in the Lingjing backend.

## 2026-05-16 Clip Silence Fix

人工校验发现一个关键差异：`/lingjing/avatar/speak` 的测试播报正常，但
`/lingjing/avatar/play-clip` 预存音频无声、口型不动。排查后确认浏览器
WebRTC、LiteAvatar 视频链路、主后端 adapter、源 wav 格式都不是主因。

根因在 ignored OpenAvatarChat spike 的 `put_avatar_audio` 注入语义：
预存 clip 之前把整段 wav 放在同一个 `AVATAR_AUDIO` 包里，并同时标记
`finish_stream=True`。而正常工作的 Windows SAPI TTS 链路是先提交音频包，
再单独提交一个很短的结束包。LiteAvatar 的 audio processor 依赖这种
stream 结束语义，否则可能只看到结束信号，导致无声且不生成有效口型。

本轮 ignored patch 已把 clip 注入改为 SAPI-compatible：

```text
1. submit full AVATAR_AUDIO with finish_stream=False
2. submit 10ms silent AVATAR_AUDIO tail with finish_stream=True
```

验证日志显示：

```text
lingjing trusted clip submitted audio samples=127824 sample_rate=24000 duration_ms=5326.0 finish_mode=sapi_compatible
LiteAvatar: CLIENT_PLAYBACK stream opened
generate first audio slice
Avatar status changed ... SPEAKING
audio2signal input audio durtaion 1.0
```

人工复测结果：

- `Speak Test`：正常发声。
- `Play Clip`：修复后已正常发声。
- 流畅度：人工确认已达到当前演示合格标准。
- 结论：clip 无声无口型问题的主因是 direct wav 注入的 stream finish 语义，不是源 wav 静音、浏览器静音、主后端 adapter 或前端触发问题。

这仍属于 ignored sidecar spike，不进入主仓库源码。主业务边界不变：
OpenAvatarChat + LiteAvatar 只作为表现层，不接管 RAG、路线、识景或运营分析。

## 结论

Task 07.6G 新增了一个 ignored fast 配置副本，用来隔离 LiteAvatar 生成压力是否是预存 clip 卡顿的主因，并已把启动入口接到游客端/Kiosk 实际演示链路。

fast 配置可以启动到 ready，主后端 `POST /api/avatar/play-clip` 在 active RTC session 存在时可以返回 `mode=sidecar, accepted=true`。游客端和 Kiosk 前端仍只调用灵境后端 `/api/avatar/speak`、`/api/avatar/play-clip`，不直连 OpenAvatarChat API 或模型厂商。RAG、Route、Vision、Analytics 业务大脑不变。

更关键的发现是：测试前存在一个旧 OpenAvatarChat/LiteAvatar orphan 子进程，导致 GPU 显存接近占满。清理该孤儿进程后，GPU 显存从约 `5930 MiB / 6144 MiB` 降到约 `3003 MiB / 6144 MiB`。因此当前卡顿排查必须先把“残留 sidecar 子进程和 GPU 显存压力”作为一号嫌疑项，而不是继续优先改前端。

## fast 配置

ignored 文件：

```text
external/OpenAvatarChat/config/lingjing_trusted_liteavatar_fast.yaml
```

它从主配置复制而来，主配置 `external/OpenAvatarChat/config/lingjing_trusted_liteavatar_edge_tts.yaml` 未覆盖。

只改 LiteAvatar 参数：

```yaml
LiteAvatar:
  fps: 15
  enable_fast_mode: true
  use_gpu: true
```

启动日志确认：

```text
Handler LiteAvatar ... fps=15 enable_fast_mode=True use_gpu=True
init avatar processor audio_sample_rate=24000 video_frame_rate=15 ...
Avatar process is ready
```

同时日志显示当前机器没有可用硬件 H.264 encoder，OAC 回退到 CPU `libx264`：

```text
No hardware encoder available, will use libx264 (CPU encoding)
```

这会让 WebRTC 视频编码成为卡顿风险之一。

## 实际游客端接入

`scripts/start_avatar_demo.ps1` 已改为面向真实 UI 演示的启动器：

- 默认优先使用 ignored `config/lingjing_trusted_liteavatar_fast.yaml`，不存在时回退 `config/lingjing_trusted_liteavatar_edge_tts.yaml`。
- 默认把灵境后端启动在 `8000`，对齐 Vite `/api -> http://127.0.0.1:8000` 代理。
- 默认启动游客端前端在 `5174`，按钮触发会进入同一个后端和 sidecar。
- `-OpenWebUI` 打开 `http://127.0.0.1:8282` 用于建立 RTC session；`-OpenVisitor` 打开游客端。

Task 07.6H 后，游客端 `/` 的“游灵山”tab 和 Kiosk `/kiosk` 的左侧主视觉区会优先以内嵌 iframe 展示 `http://127.0.0.1:8282` 的数字人画面，形成同屏直播式体验。业务边界不变：iframe 只负责显示 sidecar WebUI，问答、路线、识景、运营分析和播报触发仍只调用灵境后端 API。

新增只读状态接口：
```http
GET /api/avatar/status
```

该接口仅用于前端判断 sidecar 是否 ready，并在 mock/sidecar 不在线时返回 200 与 fallback 状态，不影响既有 `/api/avatar/speak` 和 `/api/avatar/play-clip` 契约。

推荐演示启动：

```powershell
cd D:\py\dota
& .\scripts\stop_avatar_demo.ps1
& .\scripts\start_avatar_demo.ps1 -OpenWebUI -OpenVisitor
```

建立 WebUI RTC session 后，在游客端 `/` 或 Kiosk `/kiosk` 点击：

- 游客端路线 tab：`数字人播报路线`。
- 游客端识景 tab：确认灵山大佛/灵山梵宫/九龙灌浴后点 `数字人讲解`。
- 游灵山 tab：`发送给数字人` / `数字人播报`。
- Kiosk：固定景点讲解或 `播报推荐路线`。

这些按钮不再走浏览器本地 TTS。若返回 `mode=sidecar`，声音和口型来自 8282 WebUI 的 LiteAvatar；若 sidecar 不在线，后端会降级 mock 队列，页面仍不白屏。

## 启动与停止

停止旧演示进程：

```powershell
cd D:\py\dota
& .\scripts\stop_avatar_demo.ps1 -Preview
& .\scripts\stop_avatar_demo.ps1
```

本轮该脚本清理了 8282 和 8015 的主 demo 进程，但发现一个旧 LiteAvatar worker orphan：

```text
PID=30384
CommandLine contains D:\py\dota\.sidecar-python ... parent_pid=14208
WorkingSet about 11131 MB
```

该孤儿进程已按规则单独停止，因为它明确来自已停止的旧 OpenAvatarChat parent。清理后 GPU 显存占用明显下降。

单独启动 fast sidecar：

```powershell
cd D:\py\dota\external\OpenAvatarChat
$env:PATH='D:\py\dota\external\OpenAvatarChat\.runtime-dll;D:\py\dota\.sidecar-tools\Scripts;' + $env:PATH
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
D:\py\dota\.sidecar-tools\Scripts\uv.exe run --python 3.11 src/demo.py --host 127.0.0.1 --port 8282 --config config/lingjing_trusted_liteavatar_fast.yaml
```

通常不需要手动执行上面的 sidecar 命令；优先用 `scripts/start_avatar_demo.ps1`，它会把 8282 sidecar、8000 后端和 5174 游客端串起来。

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8282/readiness
Invoke-RestMethod http://127.0.0.1:8282/lingjing/avatar/sessions
```

## API 验证

在程序化 WebRTC session `lingjing-g-fast-audio-session` active 时，主后端直调：

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/avatar/play-clip `
  -ContentType 'application/json' `
  -Body '{"clip_id":"lingshan_buddha_intro_45s","source":"attraction","interrupt":true}'
```

返回摘要：

```json
{
  "mode": "sidecar",
  "accepted": true,
  "fallback_reason": null,
  "metadata": {
    "adapter": "http_json_clip",
    "sidecar_response": {
      "accepted": true,
      "metadata": {
        "adapter": "liteavatar_trusted_clip_audio",
        "llm_bypassed": true,
        "session_id": "lingjing-g-fast-audio-session",
        "clip_id": "lingshan_buddha_intro_45s",
        "sample_rate": 24000,
        "audio_samples": 127824,
        "latency_ms": 9.06
      }
    },
    "latency_ms": 41
  }
}
```

程序化接收端拿到 audio frames。后续人工 WebUI 复测确认：在清理旧 sidecar 进程、使用 fast 配置，并修正 `AVATAR_AUDIO` finish 语义后，预存 clip 的发声和流畅度达到当前演示合格标准。

## 资源观察

清理孤儿进程前：

```text
GPU: 5930 MiB / 6144 MiB, util about 17%
largest python working set: about 11131 MB, stale parent_pid=14208
```

清理孤儿进程后：

```text
GPU: 3003 MiB / 6144 MiB, util about 0%
current fast OAC python working sets: about 2284 MB + 1223 MB
```

一次 fast clip 调用后：

```text
GPU: 3097 MiB / 6144 MiB
current fast OAC python working sets: about 3183 MB + 1200 MB
```

## 卡顿判断

已排除或弱化的因素：

- 前端并发：已有单播锁/冷却；PowerShell 直调也能复现卡顿。
- 源 wav 格式：已由 `scripts/prepare_avatar_clips.py` 标准化为 mono、24 kHz、16-bit PCM，并压缩长静音。
- 主后端调用：sidecar accepted latency 约 9 ms，主后端总延迟约 41 ms，不像主阻塞点。

仍然高风险的因素：

- OpenAvatarChat/LiteAvatar orphan 子进程残留导致 GPU/内存压力。
- 当前机器 H.264 硬件编码不可用，WebRTC 视频编码走 CPU `libx264`。
- `AVATAR_AUDIO` 当前仍是整段音频包 + 10ms 结束包的演示方案，长音频可能让 LiteAvatar 或 RTC playback 队列瞬时承压。
- fast 配置降低了目标 fps，但还没有人工 WebUI 主观对比记录。

## 下一步

演示前 SOP 必须加入：

1. 运行 `scripts/stop_avatar_demo.ps1 -Preview`。
2. 检查 8282/8000/5174 端口。
3. 检查是否有 `D:\py\dota\.sidecar-python` 或 OpenAvatarChat 的 orphan 子进程。
4. 运行 `nvidia-smi`，确认 6GB 显存没有被旧 sidecar 占满。
5. 再启动 fast 或默认 sidecar。

如果清理孤儿进程、fast 配置和 finish 语义修复后人工 WebUI 仍卡，下一步应进入 `AVATAR_AUDIO` chunk/queue 注入方案：把长 wav 分片按时间推进到 LiteAvatar，而不是一次性提交整段音频。继续改前端按钮或冷却策略收益有限。
