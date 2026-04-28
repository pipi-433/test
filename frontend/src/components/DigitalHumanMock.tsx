import { AudioLines, LoaderCircle, Sparkles } from "lucide-react";

export type DigitalHumanState = "welcome" | "thinking" | "speaking" | "happy";

const stateMeta = {
  welcome: { label: "欢迎态", icon: Sparkles },
  thinking: { label: "检索中", icon: LoaderCircle },
  speaking: { label: "讲解中", icon: AudioLines },
  happy: { label: "推荐完成", icon: Sparkles },
};

export function DigitalHumanMock({
  className = "",
  state = "welcome",
}: {
  className?: string;
  state?: DigitalHumanState;
}) {
  const Icon = stateMeta[state].icon;

  return (
    <section className={`digital-human digital-human--${state} ${className}`} aria-label="灵境数字人导游">
      <div className="digital-human__halo" aria-hidden="true" />
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
        </div>
      </div>
      <div className="digital-human__status">
        <Icon aria-hidden="true" size={18} />
        <span>{stateMeta[state].label}</span>
      </div>
    </section>
  );
}
