# Avatar Low-Latency Speaking Plan

## Goal

LiveTalking + Wav2Lip is the current digital-human presentation mainline. The business brain remains Lingjing backend RAG, Route Planner, Vision, and Analytics.

The latency issue is specific to dynamic text playback: LiveTalking's EdgeTTS path first generates a full audio file, then decodes/resamples/chunks it into the avatar pipeline. Warmup helps session readiness but cannot remove every new text's TTS generation wait.

## Current Strategy

Use two playback lanes:

| Lane | Use case | Lingjing API | LiveTalking target | Latency profile |
| --- | --- | --- | --- | --- |
| Welcome buffer clip | Short pre-roll before user-triggered playback | `POST /api/avatar/play-clip` | `/humanaudio` | Masks perceived wait; does not mean final content is ready |
| Preset wav | Fixed scenic explanations | `POST /api/avatar/play-clip` | `/humanaudio` | Low, best for demo |
| Dynamic text | QA, route summaries, ad-hoc narration | `POST /api/avatar/speak` | `/human type=echo` | Can still wait for full EdgeTTS generation |

Fixed Kiosk scenic explanations and visitor vision-confirmed clips should use preset wav. Dynamic QA and route summaries stay on trusted text speak.

## Welcome Buffer Clip

Task 07.8E adds a reusable whitelist clip:

```text
clip_id: welcome_intro_5s
text: 您好，我是灵境导游小灵，正在为您准备讲解。
target voice: zh-CN-XiaoxiaoNeural
ignored wav: D:\py\dota\external\avatar-clips\welcome_intro_5s.wav
```

Visitor and Kiosk playback actions first play `welcome_intro_5s`, wait about 5 seconds, then continue with the original speak or preset-clip action. The wav is about 4.6 seconds, so this leaves a small buffer while keeping the follow-up responsive. If the welcome clip is missing or fails, the original action continues without being blocked. The stop control cancels the delayed follow-up.

This clip is deliberately framed as an interaction buffer. It does not prove that the business answer, route summary, vision explanation, or scenic clip has already been generated.

For the mobile "游灵山" question flow, the welcome clip starts as soon as the user submits a question. The answer broadcast then waits for the in-flight welcome buffer instead of starting a second intro. If the preset clip is unavailable, the page uses the same short sentence through backend `/api/avatar/speak` as a fallback opener and waits longer before sending the real answer.

## Preset Clip Requirements

Preset clip files are local ignored assets:

```text
D:\py\dota\external\avatar-clips\welcome_intro_5s.wav
D:\py\dota\external\avatar-clips\lingshan_buddha_intro_45s.wav
D:\py\dota\external\avatar-clips\fan_gong_intro_45s.wav
D:\py\dota\external\avatar-clips\jiulong_guanyu_intro_30s.wav
```

Frontend only sends `clip_id`; it never sends file paths. The backend resolves clip ids through a whitelist and reports `audio_exists`, `audio_path_configured`, `clip_id`, and `duration_seconds` in metadata. Missing wav files must not 500; the API falls back with a clear reason.

## Option Comparison

| Option | Pros | Cons | Current recommendation |
| --- | --- | --- | --- |
| Preset wav | Fastest first sound, predictable, no vendor key at runtime | Needs pre-generation and asset management | Use now for fixed scenic explanations |
| Backend TTS cache | Repeated text can reuse wav through `/humanaudio`; keeps frontend API stable | Needs a safe TTS generator and cache lifecycle | Add skeleton now, implement generation later |
| Streaming TTS | Could reduce first-packet latency for arbitrary text | Requires LiveTalking/TTS internals patching; higher regression risk | Defer until demo is stable |
| Different TTS engine | May reduce synthesis delay or unify voice | Needs evaluation, dependencies, voice licensing | Evaluate after preset lane is stable |

## TTS Cache Skeleton

Current code only records cache metadata; it does not generate or write audio by default.

Configuration:

```env
AVATAR_TTS_CACHE_ENABLED=false
AVATAR_TTS_CACHE_DIR=
```

Design:

1. Normalize trusted backend text.
2. Hash it with SHA-256 to form a cache key.
3. Restrict cache files to `external/avatar-tts-cache/`.
4. If cache is enabled and a wav exists, a future adapter can send it to LiveTalking `/humanaudio`.
5. If there is no cache hit, keep the current `/human type=echo` path.

No real API keys, vendor TTS calls, or generated wav files are introduced in this task.

## Demo Guidance

For the lowest perceived delay in the contest demo, start with Kiosk fixed attraction explanations or visitor vision-confirmed clip playback. QA and route narration remain dynamic and may still take several seconds while EdgeTTS generates audio.

## 2026-05-22 Next Action

The chosen demo voice is `zh-CN-XiaoxiaoNeural`. Before more UI work, run the clip inventory and regenerate or fill every preset wav with the same voice:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\avatar_clip_inventory.ps1
```

Required ignored files:

```text
D:\py\dota\external\avatar-clips\welcome_intro_5s.wav
D:\py\dota\external\avatar-clips\lingshan_buddha_intro_45s.wav
D:\py\dota\external\avatar-clips\fan_gong_intro_45s.wav
D:\py\dota\external\avatar-clips\jiulong_guanyu_intro_30s.wav
```

After the files are present, run a single-session live QA pass with either visitor or Kiosk open, not both at once unless concurrency is remeasured:

1. Establish a WebRTC session.
2. Trigger a dynamic question and confirm the welcome clip starts immediately.
3. Confirm the real answer starts after the configured delay.
4. Click stop during the delay and confirm the delayed follow-up is cancelled.
5. Trigger each fixed scenic clip and confirm the voice is consistent.
