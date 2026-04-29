import { AlertTriangle, AudioLines, HeartHandshake, LoaderCircle, Mic, Sparkles } from "lucide-react";

export type DigitalHumanState = "welcome" | "listening" | "thinking" | "speaking" | "comforting" | "error" | "happy";

const stateMeta = {
  welcome: { label: "欢迎待机", icon: Sparkles },
  listening: { label: "正在听取", icon: Mic },
  thinking: { label: "思考检索", icon: LoaderCircle },
  speaking: { label: "正在讲解", icon: AudioLines },
  comforting: { label: "安抚澄清", icon: HeartHandshake },
  error: { label: "能力降级", icon: AlertTriangle },
  happy: { label: "服务完成", icon: Sparkles },
};

export function DigitalHumanMock({
  className = "",
  caption,
  state = "welcome",
}: {
  className?: string;
  caption?: string;
  state?: DigitalHumanState;
}) {
  const Icon = stateMeta[state].icon;

  return (
    <section className={`digital-human digital-human--${state} ${className}`} aria-label="灵境数字人导游">
      <div className="digital-human__halo" aria-hidden="true" />
      <div className="digital-human__aura" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="digital-human__figure" aria-hidden="true">
        <div className="digital-human__head">
          <span className="digital-human__brow digital-human__brow--left" />
          <span className="digital-human__brow digital-human__brow--right" />
          <span className="digital-human__eye digital-human__eye--left" />
          <span className="digital-human__eye digital-human__eye--right" />
          <span className="digital-human__mouth" />
        </div>
        <div className="digital-human__body">
          <span className="digital-human__sash" />
          <span className="digital-human__hands" />
        </div>
      </div>
      <div className="digital-human__waves" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="digital-human__status">
        <Icon aria-hidden="true" size={18} />
        <span>{stateMeta[state].label}</span>
      </div>
      <p className="digital-human__caption">{caption || "文本提问优先，语音播报和识别会在浏览器支持时启用。"}</p>
    </section>
  );
}
