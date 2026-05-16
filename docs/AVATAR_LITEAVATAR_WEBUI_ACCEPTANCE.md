# Task 07.6D4 WebUI Acceptance And Sidecar SOP

日期：2026-05-16

## 结论

本轮已完成 sidecar 演示前 healthcheck 与重启 SOP，并再次验证主后端到 LiteAvatar audio/video 的 trusted speak 链路。

2026-05-16 后续补充：用户已在 WebUI 中完成人工验收，确认短句实时播报和预存 clip 播放两种路径都能正常发声，预存 clip 效果良好。因此当前演示状态可表述为：本机演示环境中，主后端可信短文本和预存 wav clip 均可驱动 LiteAvatar 表现层播报。

历史限制说明：在 D4 自动化阶段，不能声称“已由我亲眼人工确认 WebUI 视频人像发声 + 对口型”。原因：

- 已尝试打开默认浏览器到 `http://127.0.0.1:8282/ui/index.html`。
- 当前执行环境中 `gstack browse` 对该 WebUI 页面无法稳定返回截图/DOM，可视 Chrome/DevTools 控制也不可用。
- 默认浏览器打开后不会自动建立 RTC session，需要人工在 WebUI 中点击连接。
- 因此我无法在本轮独立获得肉眼观察证据。

已经被程序化验证的能力仍然成立：通过同一个 `/webrtc/offer` RTC 入口创建 session 后，主后端可信文本可以进入 `AVATAR_TEXT -> Edge_TTS -> LiteAvatar -> WebRTC audio/video`，接收端能收到 audio/video 帧。

## D4 验收记录

OpenAvatarChat sidecar 使用 ignored 纯表现配置启动：

```powershell
cd D:\py\dota\external\OpenAvatarChat
$env:PATH='D:\py\dota\external\OpenAvatarChat\.runtime-dll;D:\py\dota\.sidecar-tools\Scripts;' + $env:PATH
D:\py\dota\.sidecar-tools\Scripts\uv.exe run --python 3.11 src/demo.py --host 127.0.0.1 --port 8282 --config config/lingjing_trusted_liteavatar_edge_tts.yaml
```

健康检查：

- `/liveness`: 200
- `/readiness`: 200
- `/openavatarchat/initconfig`: 200
- LiteAvatar worker: `Avatar process is ready`

主后端 sidecar 模式：

```powershell
cd D:\py\dota
$env:AVATAR_SPEAKER_MODE='sidecar'
$env:AVATAR_SIDECAR_ADAPTER='http_json'
$env:AVATAR_SIDECAR_BASE_URL='http://127.0.0.1:8282'
$env:AVATAR_SIDECAR_SPEAK_PATH='/lingjing/avatar/speak'
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8015
```

程序化 WebRTC 验收：

- session id: `lingjing-d4-backend-smoke`
- `/lingjing/avatar/sessions` 返回 active session
- `/api/avatar/speak` 返回 `mode=sidecar`, `accepted=true`
- 后端 POST 总耗时约 `229ms`
- sidecar response latency `79.61ms`
- WebRTC 接收端收到 `audio=49` 帧、`video=25` 帧

关键日志：

```text
Starting session lingjing-d4-backend-smoke
STREAM_BEGIN for ChatDataType.AVATAR_TEXT
STREAM_END for ChatDataType.AVATAR_TEXT
STREAM_BEGIN for ChatDataType.AVATAR_AUDIO
STREAM_BEGIN for ChatDataType.AVATAR_VIDEO
```

未使用 `SendHumanText`，未出现 `HUMAN_TEXT` 或 LLM handler。

## 人工 WebUI 待确认清单

人工打开 WebUI 后，需要记录：

- 是否能听到发声
- 视频人像是否有明显口型
- 是否播报原文：“您好，我是灵境导游，正在为您播报路线摘要。”
- 是否被 OpenAvatarChat 改写或重新回答
- 从 POST 到开始发声的大概延迟
- 首字是否吞音
- 音频是否自然
- 口型是否明显跟随
- 断开 WebUI 后是否能重新建立 session
- 第二次播报是否稳定

2026-05-16 人工补充验收结论：

- 短句实时播报：通过，用户确认播放正常。
- 预存 clip 播放：通过，用户确认播放正常且效果很好。
- 演示结论：两条路径都可进入本机演示 SOP。
- 边界：该结论来自本机 WebUI 人工验收，仍不是生产级数字人系统承诺。

## 演示前 Healthcheck

新增主仓库脚本：

```powershell
cd D:\py\dota
powershell -ExecutionPolicy Bypass -File .\scripts\avatar_sidecar_healthcheck.ps1 -BaseUrl http://127.0.0.1:8282 -BackendUrl http://127.0.0.1:8015
```

检查项：

- sidecar `/liveness`
- sidecar `/readiness`
- sidecar `/openavatarchat/initconfig`
- sidecar `/lingjing/avatar/sessions`
- 可选主后端 `/api/health`
- 监听端口 PID

如果任何检查超时或失败，按下面 SOP 重启 sidecar。

## 演示 SOP

1. 确认没有旧的 OAC 测试进程占用 `8282`。
2. 启动 OpenAvatarChat sidecar，使用 `config/lingjing_trusted_liteavatar_edge_tts.yaml`。
3. 等到日志出现 `Avatar process is ready`。
4. 运行 `scripts/avatar_sidecar_healthcheck.ps1`。
5. 打开 `http://127.0.0.1:8282/ui/index.html`。
6. 在 WebUI 中建立 RTC session。
7. 运行：

```powershell
Invoke-RestMethod http://127.0.0.1:8282/lingjing/avatar/sessions
```

8. 确认 `active_session_id` 不为空。
9. 启动主后端 sidecar 模式。
10. 调用 `/api/avatar/speak`。
11. 观察发声、口型、原文一致性和延迟。
12. 如果 sidecar 超时或断开后无法恢复，只重启 OpenAvatarChat sidecar，不改主业务。

## 降级行为

已验证：

- mock 模式无 API Key 可运行：`mode=mock`, `accepted=true`
- sidecar 离线：主后端返回 `mode=mock`, `accepted=true`，不 500
- sidecar 在线且有 active RTC session：主后端返回 `mode=sidecar`, `accepted=true`

## 风险

- 当前 OpenAvatarChat sidecar 关闭 WebRTC 客户端后仍可能出现 HTTP 响应超时。
- 这仍是 ignored sidecar spike，不是生产级数字人能力。
- 主演示路径必须继续保留 React/SVG/CSS mock 数字人 fallback。
- sidecar 不接管 RAG、Route Planner、Vision、Analytics 或任何业务大脑决策。
