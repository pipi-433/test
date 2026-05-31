from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLIP_DIR = PROJECT_ROOT / "external" / "avatar-clips"
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


@dataclass(frozen=True)
class ClipSpec:
    clip_id: str
    filename: str
    text: str


CLIPS: tuple[ClipSpec, ...] = (
    ClipSpec(
        clip_id="welcome_intro_5s",
        filename="welcome_intro_5s.wav",
        text=(
            "\u60a8\u597d\uff0c\u6211\u662f\u7075\u5883\u5bfc\u6e38\u5c0f\u7075\uff0c"
            "\u6b63\u5728\u4e3a\u60a8\u51c6\u5907\u8bb2\u89e3\u3002"
        ),
    ),
    ClipSpec(
        clip_id="lingshan_buddha_intro_45s",
        filename="lingshan_buddha_intro_45s.wav",
        text=(
            "\u73b0\u5728\u4e3a\u60a8\u4ecb\u7ecd\u7075\u5c71\u5927\u4f5b\u3002"
            "\u7075\u5c71\u5927\u4f5b\u662f\u7075\u5c71\u80dc\u5883\u6700\u9192\u76ee\u7684\u6838\u5fc3\u5730\u6807\uff0c"
            "\u4f5b\u50cf\u77d7\u7acb\u5728\u79e6\u5c65\u5cf0\u5357\u9e93\uff0c\u4e0e\u592a\u6e56\u5c71\u6c34\u76f8\u671b\u3002"
            "\u6e38\u89c8\u65f6\u5efa\u8bae\u6cbf\u4e2d\u8f74\u7ebf\u6162\u6162\u524d\u884c\uff0c"
            "\u7ecf\u8fc7\u4e94\u667a\u95e8\u3001\u83e9\u63d0\u5927\u9053\u3001\u4e5d\u9f99\u704c\u6d74\u548c\u7965\u7b26\u7985\u5bfa\uff0c"
            "\u518d\u6765\u5230\u5927\u4f5b\u811a\u4e0b\u3002"
            "\u8fd9\u91cc\u9002\u5408\u653e\u6162\u811a\u6b65\uff0c\u5148\u8fdc\u89c2\u6574\u4f53\u6c14\u52bf\uff0c"
            "\u518d\u8fd1\u770b\u83b2\u82b1\u5ea7\u548c\u53f0\u9636\u7a7a\u95f4\u3002"
            "\u5f53\u524d\u8bb2\u89e3\u57fa\u4e8e\u672c\u5730\u666f\u533a\u8d44\u6599\uff0c"
            "\u53ea\u4f5c\u4e3a\u5bfc\u89c8\u63d0\u793a\uff0c\u4e0d\u4ee3\u8868\u5b9e\u65f6\u5bfc\u822a\u3002"
        ),
    ),
    ClipSpec(
        clip_id="fan_gong_intro_45s",
        filename="fan_gong_intro_45s.wav",
        text=(
            "\u73b0\u5728\u4e3a\u60a8\u4ecb\u7ecd\u7075\u5c71\u68b5\u5bab\u3002"
            "\u68b5\u5bab\u662f\u7075\u5c71\u80dc\u5883\u91cd\u8981\u7684\u5ba4\u5185\u6587\u5316\u7a7a\u95f4\uff0c"
            "\u5916\u90e8\u5efa\u7b51\u5e84\u4e25\u5927\u6c14\uff0c"
            "\u5185\u90e8\u878d\u5408\u4e1c\u9633\u6728\u96d5\u3001\u7409\u7483\u3001\u58c1\u753b\u548c\u7a79\u9876\u827a\u672f\uff0c"
            "\u9002\u5408\u5728\u5348\u540e\u6216\u5929\u6c14\u4e0d\u4f73\u65f6\u5b89\u6392\u53c2\u89c2\u3002"
            "\u6e38\u5ba2\u53ef\u4ee5\u91cd\u70b9\u89c2\u770b\u5efa\u7b51\u7ec6\u8282\u3001\u4f5b\u6559\u827a\u672f\u5c55\u793a\uff0c"
            "\u4ee5\u53ca\u5409\u7965\u9882\u6f14\u51fa\u76f8\u5173\u533a\u57df\u3002"
            "\u56e0\u4e3a\u5ba4\u5185\u52a8\u7ebf\u8f83\u4e30\u5bcc\uff0c"
            "\u5efa\u8bae\u8ddf\u968f\u73b0\u573a\u6807\u8bc6\u6709\u5e8f\u6e38\u89c8\uff0c"
            "\u7ed9\u62cd\u7167\u548c\u4f11\u606f\u7559\u51fa\u65f6\u95f4\u3002"
            "\u5f53\u524d\u8bb2\u89e3\u57fa\u4e8e\u672c\u5730\u666f\u533a\u8d44\u6599\uff0c"
            "\u4e0d\u4ee3\u8868\u5b9e\u65f6\u5ba2\u6d41\u6216\u771f\u5b9e\u786c\u4ef6\u72b6\u6001\u3002"
        ),
    ),
    ClipSpec(
        clip_id="jiulong_guanyu_intro_30s",
        filename="jiulong_guanyu_intro_30s.wav",
        text=(
            "\u73b0\u5728\u4e3a\u60a8\u4ecb\u7ecd\u4e5d\u9f99\u704c\u6d74\u3002"
            "\u8fd9\u91cc\u4f4d\u4e8e\u7075\u5c71\u80dc\u5883\u4e2d\u8f74\u7ebf\u6838\u5fc3\u4f4d\u7f6e\uff0c"
            "\u662f\u4ee5\u91ca\u8fe6\u725f\u5c3c\u8bde\u751f\u4f20\u8bf4\u4e3a\u4e3b\u9898\u7684\u52a8\u6001\u666f\u89c2\u3002"
            "\u6e38\u89c8\u65f6\u53ef\u4ee5\u63d0\u524d\u5230\u5e7f\u573a\u9009\u62e9\u5f00\u9614\u89c6\u89d2\uff0c"
            "\u89c2\u5bdf\u4e5d\u9f99\u3001\u6c34\u666f\u548c\u592a\u5b50\u4f5b\u9020\u50cf\u7684\u53d8\u5316\u3002"
            "\u82e5\u73b0\u573a\u6e38\u5ba2\u8f83\u591a\uff0c\u5efa\u8bae\u5148\u5728\u5468\u8fb9\u7a0d\u4f5c\u505c\u7559\uff0c"
            "\u6216\u6839\u636e\u6f14\u51fa\u63d0\u9192\u9519\u5cf0\u8fd4\u56de\u3002"
            "\u5f53\u524d\u8bb2\u89e3\u57fa\u4e8e\u672c\u5730\u666f\u533a\u8d44\u6599\u548c\u6f14\u793a\u89c4\u5219\uff0c"
            "\u4e0d\u4ee3\u8868\u5b9e\u65f6\u5ba2\u6d41\u3002"
        ),
    ),
)


async def _edge_tts_to_file(text: str, voice: str, output_path: Path) -> None:
    try:
        import edge_tts
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "edge_tts is required. Run this script through external/LiveTalking/.venv "
            "or install it in an ignored venv."
        ) from exc

    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(str(output_path))


def _safe_clip_dir(raw_clip_dir: Path) -> Path:
    clip_dir = raw_clip_dir if raw_clip_dir.is_absolute() else PROJECT_ROOT / raw_clip_dir
    clip_dir = clip_dir.resolve()
    allowed_root = DEFAULT_CLIP_DIR.resolve()
    if clip_dir != allowed_root and not clip_dir.is_relative_to(allowed_root):
        raise SystemExit(f"clip dir must stay inside {allowed_root}")
    clip_dir.mkdir(parents=True, exist_ok=True)
    return clip_dir


def generate_clip(*, spec: ClipSpec, clip_dir: Path, voice: str, force: bool) -> Path:
    target = clip_dir / spec.filename
    if target.exists() and not force:
        print(f"{spec.clip_id}: exists, skip without --force: {target}")
        return target

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required to convert EdgeTTS output to 24kHz mono PCM wav.")

    temp_mp3 = clip_dir / f"{spec.clip_id}.tmp.mp3"
    temp_wav = clip_dir / f"{spec.clip_id}.tmp.wav"
    try:
        asyncio.run(_edge_tts_to_file(spec.text, voice, temp_mp3))
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(temp_mp3),
                "-ac",
                "1",
                "-ar",
                "24000",
                "-sample_fmt",
                "s16",
                str(temp_wav),
            ],
            check=True,
        )
        temp_wav.replace(target)
        print(f"{spec.clip_id}: generated {target}")
        return target
    finally:
        temp_mp3.unlink(missing_ok=True)
        temp_wav.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ignored Lingjing avatar demo clips.")
    parser.add_argument("--clip-dir", type=Path, default=DEFAULT_CLIP_DIR)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    clip_dir = _safe_clip_dir(args.clip_dir)
    for spec in CLIPS:
        generate_clip(spec=spec, clip_dir=clip_dir, voice=args.voice, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
