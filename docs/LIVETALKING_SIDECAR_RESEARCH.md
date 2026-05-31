# LiveTalking Sidecar Research

## Task 07.8 Mainline Switch

Status: LiveTalking + Wav2Lip is now the main digital-human demo route for Lingjing Guide.

The earlier 07.7 conclusion treated LiveTalking as optional while assets were still being prepared. After local single-session validation with `lingshan_guide_avatar1`, the demo mainline now uses:

```text
D:\py\dota\external\LiveTalking
D:\py\dota\external\LiveTalking\data\avatars\lingshan_guide_avatar1
D:\py\dota\external\LiveTalking\models\wav2lip.pth
D:\py\dota\external\LiveTalking\s3fd.pth
http://127.0.0.1:8011
```

These paths remain ignored sidecar/assets and must not be added to git.

Current backend contract:

| Lingjing API | LiveTalking target | Rule |
| --- | --- | --- |
| `GET /api/avatar/status` | `GET /webrtcapi.html`, optional `/is_speaking` | Reports `engine=livetalking`, readiness, sidecar URL, active/default session info, and fallback availability. |
| `POST /api/avatar/webrtc/offer` | `POST /offer` | Frontend still calls Lingjing backend only; backend returns LiveTalking `sessionid`. |
| `POST /api/avatar/speak` | `POST /human` | Forced `type="echo"` for backend-trusted text. `type="chat"` is prohibited. |
| `POST /api/avatar/play-clip` | `POST /humanaudio` | Backend resolves whitelist `clip_id` to local wav; frontend cannot pass arbitrary paths. |
| `POST /api/avatar/stop` | `POST /interrupt_talk` | Uses the current `session_id` when available. |
| `POST /api/avatar/warmup` | `POST /human` | Sends a very short trusted `type="echo"` warmup text after a WebRTC session exists; fallback is non-fatal. |

Default demo startup:

```powershell
cd D:\py\dota
.\scripts\start_avatar_demo.ps1 -OpenVisitor -ForceLowMemory -Voice zh-CN-XiaoxiaoNeural
```

This starts LiveTalking with Wav2Lip, `avatar_id=lingshan_guide_avatar1`, `--transport webrtc`, `--tts edgetts`, `--listenport 8011`, and `--max_session 1`. OpenAvatarChat + LiteAvatar is preserved as legacy fallback:

```powershell
.\scripts\start_avatar_demo.ps1 -Engine openavatarchat -OpenWebUI
```

Boundary for the demo: LiveTalking is only the voice/avatar/lip-sync layer. RAG, Route Planner, Vision, Analytics, source attribution, and route constraints stay in the Lingjing FastAPI backend. Frontend pages must not call LiveTalking `/human`, `/humanaudio`, `/offer`, or model vendors directly.

Current risk: this machine is a 3060 Laptop 6 GB setup and the stable demo command uses `--max_session 1`; run only one active visitor/Kiosk WebRTC view at a time unless concurrency is remeasured.

## Task 07.8B First-Packet Latency Tuning

Goal: reduce perceived wait after the user clicks "数字人播报 / 讲解" without changing the Lingjing business brain.

Changes:

- Added backend `POST /api/avatar/warmup`.
- Warmup reuses the same trusted text path as speak: LiveTalking `/human` with `type="echo"` only.
- Default warmup text is short: `您好。`.
- Visitor and Kiosk pages run one best-effort warmup after `POST /api/avatar/webrtc/offer` returns a session id.
- Startup script does not force warmup into session `0` when LiveTalking reports `session not found`; it prints that browser session warmup will happen after the page connects.
- Visitor and Kiosk clicks now immediately show "数字人正在生成语音，请稍候。" before waiting for the backend response.
- Kiosk quick attraction speeches remain realtime `/api/avatar/speak`, but the three texts are shortened to roughly 60-100 Chinese characters to reduce TTS first-packet pressure.

Warmup contract:

```http
POST /api/avatar/warmup
```

```json
{
  "session_id": "0",
  "text": "您好。",
  "source": "system",
  "interrupt": false,
  "silent": false
}
```

The response mirrors `AvatarActionResponse` and includes:

```json
{
  "metadata": {
    "warmup": true,
    "llm_bypassed": true,
    "policy": "presentation_warmup_only"
  }
}
```

If there is no active session or LiveTalking is offline, warmup degrades to mock/fallback and must not affect QA, routes, vision, analytics, or page navigation.

## Task 07.8C Low-Latency Speaking Strategy

Observation: first and second dynamic `/api/avatar/speak` playback can still take about 6-7 seconds. The main cause is LiveTalking's EdgeTTS path: it generates the whole audio clip before decoding, resampling, chunking, and pushing audio/video frames to Wav2Lip. Session warmup cannot remove this per-text synthesis wait.

Current strategy:

- Fixed scenic explanations use preset wav through `POST /api/avatar/play-clip` -> LiveTalking `/humanaudio`.
- Dynamic QA, route summaries, and ad-hoc narration continue to use `POST /api/avatar/speak` -> LiveTalking `/human type="echo"`.
- Kiosk fixed scenic buttons use `play-clip` again for low-latency demo playback.
- Visitor vision-confirmed scenic explanation remains on `play-clip` when the attraction maps to a whitelist clip.
- Frontend never sends local file paths; it only sends `clip_id`.

Clip inventory:

```text
external/avatar-clips/welcome_intro_5s.wav
external/avatar-clips/lingshan_buddha_intro_45s.wav
external/avatar-clips/fan_gong_intro_45s.wav
external/avatar-clips/jiulong_guanyu_intro_30s.wav
```

Backend metadata now exposes `audio_exists`, `audio_path_configured`, `clip_id`, and `duration_seconds`. Missing files return a clear fallback reason such as `preset clip audio file missing; using mock preset clip queue.` and must not 500.

TTS cache skeleton:

- `AVATAR_TTS_CACHE_ENABLED=false` by default.
- `AVATAR_TTS_CACHE_DIR=` defaults to ignored `external/avatar-tts-cache`.
- Backend trusted text is normalized and hashed for a future wav cache key.
- No vendor TTS call, real API key, or audio file writing is introduced in this task.

Detailed tradeoffs are in `docs/AVATAR_LOW_LATENCY_SPEAKING_PLAN.md`.

## Task 07.8E Welcome Intro Clip

Status: implemented as a conservative interaction buffer before existing playback actions.

New whitelist clip:

| Field | Value |
| --- | --- |
| `clip_id` | `welcome_intro_5s` |
| Text | `您好，我是灵境导游小灵，正在为您准备讲解。` |
| Target voice | `zh-CN-XiaoxiaoNeural` |
| Local ignored wav | `D:\py\dota\external\avatar-clips\welcome_intro_5s.wav` |
| Backend API | `POST /api/avatar/play-clip` |

Visitor and Kiosk actions now call backend `POST /api/avatar/play-clip` with `clip_id="welcome_intro_5s"` before the original speak or preset-clip action. After about 5 seconds the page sends the original `/api/avatar/speak` or `/api/avatar/play-clip` request. The local wav is about 4.6 seconds, so this leaves a small buffer while keeping the follow-up responsive. If the welcome clip fails or falls back, the original action continues instead of being blocked.

The welcome line is only a UX buffer to cover LiveTalking startup/TTS/per-clip waiting time. It must not be presented as evidence that RAG, route planning, vision recognition, or the final narration has already completed. Stop clears the delayed follow-up timer and then calls backend `/api/avatar/stop`, so stopping during the welcome line should not accidentally trigger the original narration.

Follow-up fix for the mobile "游灵山" question flow: question submit now starts the welcome clip immediately while the backend answer is still being prepared. The later answer broadcast reuses the active welcome delay instead of starting another intro. If the clip path fails, the frontend falls back to the same welcome sentence through backend `/api/avatar/speak` and waits longer before the real answer so the fallback intro is not immediately interrupted.

Generation command:

```powershell
cd D:\py\dota
powershell -ExecutionPolicy Bypass -File .\scripts\generate_avatar_clips.ps1 -Voice zh-CN-XiaoxiaoNeural
powershell -ExecutionPolicy Bypass -File .\scripts\avatar_clip_inventory.ps1
```

## Scope

Task 07.7 originally evaluated LiveTalking as an optional digital-human presentation sidecar for Lingjing Guide. Task 07.8 supersedes that early conclusion and makes LiveTalking + Wav2Lip the current demo mainline. It still must not take over RAG, route planning, vision, analytics, or factual question answering.

Frontend policy stays unchanged: visitor pages and Kiosk call Lingjing backend APIs only. LiveTalking would sit behind the backend adapter.

## Source And Environment

- Source path: `D:\py\dota\external\LiveTalking`
- Source URL: `https://github.com/lipku/LiveTalking.git`
- Checked revision: `ca043b8 feat: register rtcpush output in WebRTCOutput class`
- Ignore protection: `external/.gitignore` contains `*`, so `external/LiveTalking`, model weights, avatar assets, venvs, caches, and logs are ignored.

Current local checks:

| Item | Result | Notes |
| --- | --- | --- |
| Git | available | Source clone succeeded with `--depth 1`. |
| Python | `3.12.0` | LiveTalking README recommends Python 3.10+. A dedicated environment is still needed. |
| Docker | available | Docker image exists upstream, but this spike did not run it. |
| GPU | NVIDIA RTX 3060 Laptop, 6 GB | At check time GPU memory was almost full because the existing OAC sidecar was running. |
| LiveTalking dependencies | not installed | `python app.py --help` fails at `ModuleNotFoundError: No module named 'flask'`. |
| Wav2Lip model | missing | Expected `external/LiveTalking/models/wav2lip.pth`. |
| Wav2Lip avatar | missing | Expected `external/LiveTalking/data/avatars/wav2lip256_avatar1`. |

No model weights or avatar packages were downloaded in this run.

## Upstream Capability Observations

LiveTalking is a real-time streaming digital-human project. Its README lists support for Wav2Lip, MuseTalk, ER-NeRF-style history, Ultralight Digital Human, WebRTC/RTMP/virtual camera output, custom avatars, voice cloning, interruptions, and concurrency.

The relevant local API routes are in `external/LiveTalking/server/routes.py`:

| Route | Purpose | Lingjing relevance |
| --- | --- | --- |
| `POST /offer` | WebRTC offer endpoint | Candidate backend proxy target for `POST /api/avatar/webrtc/offer`. |
| `POST /human` | Text input | Use `type="echo"` for trusted backend text. Do not use `type="chat"` for Lingjing facts. |
| `POST /humanaudio` | Uploaded audio file | Candidate target for preset wav playback. |
| `POST /interrupt_talk` | Interrupt current speech | Maps to Lingjing `interrupt=true`. |
| `POST /is_speaking` | Speech status | Candidate status signal for `GET /api/avatar/status`. |

The critical point: `POST /human` supports `type="echo"`, which calls `avatar_session.put_msg_txt(params["text"], datainfo)`. That sends the trusted text to TTS and avatar rendering without asking LiveTalking's LLM to answer. `type="chat"` calls `llm_response` and must not be used for Lingjing trusted content.

For wav playback, `POST /humanaudio` reads the uploaded file and calls `avatar_session.put_audio_file(filebytes, datainfo)`. In `avatars/base_avatar.py`, `put_audio_file` reads audio, resamples it to the avatar sample rate, chunks it, and pushes audio frames to the ASR/lip-sync path. This is a cleaner native audio path than the custom OAC wav patch.

## Recommended Lightweight Model

For this 3060 Laptop 6 GB machine, the recommended first target is Wav2Lip / `wav2lip256`.

Reasons:

- LiveTalking README performance table lists `wav2lip256` at about 60 fps on 3060-class GPU.
- The same README says MuseTalk needs a much larger GPU class, with 3080Ti listed for real-time use.
- Wav2Lip has the simplest required assets in this repo: `models/wav2lip.pth` and `data/avatars/wav2lip256_avatar1`.

Do not start with MuseTalk or heavier models for the contest demo machine unless Wav2Lip is already stable.

## Smoke Status

This run did not start LiveTalking.

Attempted lightweight import smoke:

```powershell
cd D:\py\dota\external\LiveTalking
python app.py --help
```

Result:

```text
ModuleNotFoundError: No module named 'flask'
```

This is expected because dependencies were not installed. The next blocker after dependencies would be missing model and avatar assets:

```text
external/LiveTalking/models/wav2lip.pth
external/LiveTalking/data/avatars/wav2lip256_avatar1
```

Because the required model/avatar assets are absent, text smoke, wav smoke, WebRTC visual confirmation, latency, and VRAM measurements were not executed.

## Candidate Start And Smoke Commands

After dependencies, `wav2lip.pth`, and `wav2lip256_avatar1` are present:

```powershell
cd D:\py\dota\external\LiveTalking
python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1 --tts edgetts --listenport 8010 --max_session 1
```

Open local WebRTC page:

```text
http://127.0.0.1:8010/dashboard.html
```

Trusted text smoke, after a WebRTC session exists and the page provides a `sessionid`:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8010/human `
  -ContentType 'application/json' `
  -Body '{"sessionid":"<sessionid>","type":"echo","text":"您好，我是灵境导游，正在为您播报路线摘要。","interrupt":true}'
```

Preset wav smoke:

```powershell
$form = @{
  sessionid = "<sessionid>"
  file = Get-Item "D:\py\dota\external\avatar-clips\lingshan_buddha_intro_45s.wav"
}
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8010/humanaudio -Form $form
```

`type="chat"` is intentionally excluded from Lingjing adapter tests because it enters LiveTalking's LLM response path.

## Adapter Design

Keep the current Lingjing API surface:

- `POST /api/avatar/speak`
- `POST /api/avatar/play-clip`
- `GET /api/avatar/status`
- `POST /api/avatar/webrtc/offer`

Add optional configuration later:

```env
AVATAR_ENGINE=openavatarchat
AVATAR_LIVETALKING_BASE_URL=
AVATAR_LIVETALKING_TEXT_PATH=/human
AVATAR_LIVETALKING_AUDIO_PATH=/humanaudio
AVATAR_LIVETALKING_WEBRTC_PATH=/offer
```

Mapping:

| Lingjing API | LiveTalking target | Notes |
| --- | --- | --- |
| `POST /api/avatar/speak` | `POST /human` | Send `type="echo"`, text, sessionid, optional TTS voice metadata. |
| `POST /api/avatar/play-clip` | `POST /humanaudio` | Backend resolves whitelist `clip_id` to local wav, uploads the file, never accepts arbitrary frontend paths. |
| `GET /api/avatar/status` | `POST /is_speaking` plus local health | Needs sessionid-aware status. |
| `POST /api/avatar/webrtc/offer` | `POST /offer` | Backend proxy keeps frontend from directly calling LiveTalking. |

Fallback behavior should match the current OAC adapter: sidecar offline or injection failure must not 500 the main app; mock mode remains API-key-free.

## Comparison With OpenAvatarChat + LiteAvatar

| Dimension | OpenAvatarChat + LiteAvatar | LiveTalking |
| --- | --- | --- |
| Current Lingjing integration | Legacy ignored sidecar spike, still preserved | Current backend/main demo route after Task 07.8 |
| Trusted text | Requires Lingjing-specific `AVATAR_TEXT` patch | Native `/human` with `type="echo"` appears suitable |
| Preset wav | Requires Lingjing-specific `/lingjing/avatar/play-clip` patch and stream finish fix | Native `/humanaudio` exists |
| WebRTC | Working through OAC `/webrtc/offer` and backend proxy | Native `/offer` exists |
| LLM bypass | Proven in current OAC patch | Must use `echo`, not `chat` |
| Maintainability | Current OAC trusted endpoints are local ignored patches | LiveTalking API shape is closer to Lingjing needs |
| GPU fit | LiteAvatar now works but 6 GB VRAM is tight | Wav2Lip is likely the right first target; heavier models are risky |
| Multi-session | OAC current demo is effectively single-sidecar constrained | LiveTalking has `--max_session`, but real 6 GB concurrency still needs measurement |

## Historical 07.7 Recommendation

This section records the earlier 07.7 reasoning before local Wav2Lip assets were validated. It is superseded by the Task 07.8 mainline switch above.

Reasons that led to the switch:

- Native trusted text echo and uploaded-audio endpoints.
- Wav2Lip is lighter and more stable for this 3060 Laptop 6 GB demo than the current OAC + LiteAvatar setup.
- Less ignored third-party patching is needed for text and wav playback.

Former blockers that are now resolved locally:

- Ignored LiveTalking venv exists.
- `wav2lip.pth`, `s3fd.pth`, and `lingshan_guide_avatar1` exist under ignored `external/LiveTalking`.
- Single-session text and wav WebRTC smoke was manually accepted before the mainline switch.

## Boundaries

- LiveTalking must remain presentation-only.
- It must not answer Lingjing facts, plan routes, identify images, read analytics, or call model vendors from the frontend.
- Do not use `type="chat"` for Lingjing trusted content.
- Do not download or commit model weights, avatar assets, logs, caches, venvs, or real API keys.
- Do not describe this as production-grade until session lifecycle, recovery, concurrency, and GPU pressure are measured.

## Task 07.7C: Backend Adapter Integration

Status: implemented first as an optional backend adapter, then promoted to the current demo mainline in Task 07.8. The existing OpenAvatarChat + LiteAvatar path is preserved as legacy fallback.

Configuration:

```env
AVATAR_ENGINE=mock
AVATAR_ENGINE=openavatarchat
AVATAR_ENGINE=livetalking
AVATAR_LIVETALKING_BASE_URL=http://127.0.0.1:8011
AVATAR_LIVETALKING_SESSION_ID=0
AVATAR_LIVETALKING_SPEAK_PATH=/human
AVATAR_LIVETALKING_AUDIO_PATH=/humanaudio
AVATAR_LIVETALKING_WEBRTC_PATH=/offer
```

Backend mapping:

| Lingjing API | LiveTalking target | Adapter behavior |
| --- | --- | --- |
| `GET /api/avatar/status` | `GET /webrtcapi.html`, optional `POST /is_speaking` | Reports `engine=livetalking`, readiness, public sidecar URL, and fallback availability. |
| `POST /api/avatar/webrtc/offer` | `POST /offer` | Proxies WebRTC offer through Lingjing backend and returns LiveTalking `sessionid` to the frontend. |
| `POST /api/avatar/speak` | `POST /human` | Sends `type="echo"` only, with backend-trusted text and `interrupt`; never uses `type="chat"`. |
| `POST /api/avatar/play-clip` | `POST /humanaudio` | Resolves `clip_id` through the backend whitelist, uploads only the resolved local wav, and never accepts frontend file paths. |

Fallback behavior:

- No sidecar or offline `8011`: `speak` and `play-clip` return stable mock fallback and do not 500.
- Missing preset wav: `play-clip` remains accepted in mock fallback with an explanatory `fallback_reason`.
- WebRTC offer failures return `accepted=false` with `mode=mock`; the visitor/Kiosk UI keeps its fallback display.

Frontend boundary:

- Visitor and Kiosk pages still call only Lingjing backend APIs.
- `AvatarRtcViewer` now uses the `sessionid` returned by `/api/avatar/webrtc/offer` when present. This lets LiveTalking `/human` and `/humanaudio` target the active session without exposing the LiveTalking business APIs to the frontend.

Startup:

```powershell
cd D:\py\dota
.\scripts\start_avatar_demo.ps1 -Engine livetalking -OpenWebUI
```

This uses `external/LiveTalking` as an ignored sidecar workspace, `avatar_id=lingshan_guide_avatar1`, and port `8011` by default. OpenAvatarChat can still be started explicitly as legacy fallback with:

```powershell
.\scripts\start_avatar_demo.ps1 -Engine openavatarchat -OpenWebUI
```

Validation commands:

```powershell
$env:AVATAR_ENGINE='livetalking'
$env:AVATAR_LIVETALKING_BASE_URL='http://127.0.0.1:8011'
$env:AVATAR_LIVETALKING_SESSION_ID='<sessionid from WebRTC offer or page>'
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8021

Invoke-RestMethod http://127.0.0.1:8021/api/avatar/status
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8021/api/avatar/speak `
  -ContentType 'application/json' `
  -Body '{"text":"您好，我是灵境导游，现在测试 LiveTalking 数字人播报。","emotion":"happy","source":"manual","interrupt":true}'
```

Security and product boundary:

- LiveTalking is a presentation sidecar only.
- RAG, Route Planner, Vision, Analytics, and factual QA stay in the Lingjing backend.
- Route planning remains the constrained Route Planner; LiveTalking never chooses route points.
- `POST /human` must be `type="echo"` for trusted Lingjing content. `type="chat"` is prohibited for this integration.

## Task 07.7B: Wav2Lip Single-Session Smoke

### Installation Result

An ignored local environment was created at:

```text
D:\py\dota\external\LiveTalking\.venv
```

Cache locations used:

```text
D:\py\dota\external\.uv-cache
D:\py\dota\external\.pip-cache
```

Commands run:

```powershell
cd D:\py\dota\external\LiveTalking
$env:UV_CACHE_DIR='D:\py\dota\external\.uv-cache'
$env:PIP_CACHE_DIR='D:\py\dota\external\.pip-cache'
D:\py\dota\.sidecar-tools\Scripts\uv.exe venv .venv --python D:\py\dota\.sidecar-python\cpython-3.11-windows-x86_64-none\python.exe
D:\py\dota\.sidecar-tools\Scripts\uv.exe pip install --python .venv\Scripts\python.exe torch==2.5.0 torchvision==0.20.0 torchaudio==2.5.0 --index-url https://download.pytorch.org/whl/cu124
D:\py\dota\.sidecar-tools\Scripts\uv.exe pip install --python .venv\Scripts\python.exe -r requirements.txt
```

Installed successfully:

```text
Python 3.11.15
torch 2.5.0+cu124
torch.cuda.is_available() == True
CUDA device: NVIDIA GeForce RTX 3060 Laptop GPU
```

`gdown` was installed into the same ignored venv only to try the official Google Drive folder:

```powershell
D:\py\dota\.sidecar-tools\Scripts\uv.exe pip install --python .venv\Scripts\python.exe gdown
```

### Model And Avatar Assets

Still missing:

```text
D:\py\dota\external\LiveTalking\models\wav2lip.pth
D:\py\dota\external\LiveTalking\data\avatars\wav2lip256_avatar1
```

Official README asset instructions say:

- Download `wav2lip256.pth`, copy it to `models`, and rename it to `wav2lip.pth`.
- Download `wav2lip256_avatar1.tar.gz`, extract it, and copy the extracted `wav2lip256_avatar1` folder to `data/avatars`.

Target layout:

```text
D:\py\dota\external\LiveTalking\models\wav2lip.pth
D:\py\dota\external\LiveTalking\data\avatars\wav2lip256_avatar1\
  coords.pkl
  full_imgs\
  face_imgs\
```

After manually placing files, verify:

```powershell
Get-Item D:\py\dota\external\LiveTalking\models\wav2lip.pth
Get-ChildItem D:\py\dota\external\LiveTalking\data\avatars\wav2lip256_avatar1
Get-FileHash D:\py\dota\external\LiveTalking\models\wav2lip.pth -Algorithm SHA256
```

Automatic Google Drive attempt:

```powershell
cd D:\py\dota\external\LiveTalking
.venv\Scripts\python.exe -m gdown --folder "https://drive.google.com/drive/folders/1FOC_MD6wdogyyX_7V1d4NDIO7P9NlSAJ?usp=sharing" -O D:\py\dota\external\LiveTalking\_asset_download
```

Result:

```text
HTTPSConnectionPool(host='drive.google.com', port=443): connection timed out
```

No retry storm was performed.

### Startup Attempt

Command:

```powershell
cd D:\py\dota\external\LiveTalking
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
.venv\Scripts\python.exe app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1 --tts edgetts --listenport 8011 --max_session 1
```

Result: startup reached CUDA/Wav2Lip model loading, then failed because the model file is absent:

```text
Using cuda for inference.
Registered avatar/wav2lip: LipReal
Load checkpoint from: ./models/wav2lip.pth
FileNotFoundError: [Errno 2] No such file or directory: './models/wav2lip.pth'
```

This is a useful smoke result: dependency and CUDA setup are now past the first gate. The current blocker is asset availability, not Python dependencies.

### Text And Wav Smoke

Not executed because LiveTalking cannot start without `models/wav2lip.pth`. The intended commands after startup are:

```powershell
python .\scripts\livetalking_smoke.py --base-url http://127.0.0.1:8011 --session-id <sessionid>
```

Text path:

```text
POST /human
{"sessionid":"<sessionid>","type":"echo","text":"您好，我是灵境导游，现在测试 LiveTalking 数字人口型播报。","interrupt":true}
```

Wav path:

```text
POST /humanaudio
multipart form: sessionid=<sessionid>, file=external/avatar-clips/lingshan_buddha_intro_45s.wav
```

`type="chat"` remains forbidden for Lingjing trusted content.

### Resource Observation

Before LiveTalking asset startup, current checks showed:

```text
GPU memory: about 76-78 MiB / 6144 MiB
GPU util: about 4%
```

The current OpenAvatarChat listener was still present on `8282`, but its worker was not consuming the several-GB GPU load seen in earlier OAC runs. LiveTalking did not remain running after the missing-model failure, so no steady-state Wav2Lip VRAM number is available yet.

### 07.7B Conclusion

Status: blocked on model/avatar assets.

What is now proven:

- LiveTalking source exists in ignored `external/LiveTalking`.
- Dedicated ignored venv exists and imports CUDA PyTorch.
- LiveTalking can reach Wav2Lip loading on CUDA.
- The exact blocker is missing `models/wav2lip.pth`; next blocker will likely be `data/avatars/wav2lip256_avatar1` if the model is added.

Recommendation: proceed to Task 07.7C adapter only after the user provides or authorizes obtaining:

1. `wav2lip256.pth` placed as `external/LiveTalking/models/wav2lip.pth`.
2. `wav2lip256_avatar1` folder placed under `external/LiveTalking/data/avatars`.
3. A successful WebRTC session with `/human type=echo` and `/humanaudio` smoke.

## 2026-05-22 Update: Active Demo State

The historical 07.7 asset blockers above are superseded by the current local state: `lingshan_guide_avatar1`, `wav2lip.pth`, and `s3fd.pth` have been prepared locally under ignored `external/LiveTalking` paths, and LiveTalking is now the default demo engine.

Current chosen voice for the LiveTalking demo is `zh-CN-XiaoxiaoNeural`.

To reduce perceived delay for dynamic text, visitor and Kiosk playback now use a welcome buffer:

```text
clip_id: welcome_intro_5s
text: 您好，我是灵境导游小灵，正在为您准备讲解。
```

The page triggers the welcome clip first, waits about 5 seconds, then continues with the real action. The follow-up can be dynamic `/api/avatar/speak` or fixed `/api/avatar/play-clip`. Stop must interrupt the current playback and clear any delayed follow-up.

This is a UX buffer only. It does not mean the true RAG answer, route summary, vision explanation, or scenic clip has already been generated.

Next task: regenerate or fill every preset wav under `external/avatar-clips/` with `zh-CN-XiaoxiaoNeural`, then run one single-session live check for welcome, speak, play-clip, stop, and reconnect.
