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
      <div className="digital-human__stage" aria-hidden="true">
        <svg className="digital-human__portrait" viewBox="0 0 280 300">
          <path className="digital-human__backplate" d="M53 255c9-61 40-103 87-103s78 42 87 103H53Z" />
          <path className="digital-human__guide-shadow" d="M63 258h154c-10 16-34 25-77 25s-67-9-77-25Z" />
          <path className="digital-human__coat" d="M56 258c8-65 42-98 84-98s76 33 84 98H56Z" />
          <path className="digital-human__coat-left" d="M92 175c8 32 21 60 39 83H59c5-36 16-64 33-83Z" />
          <path className="digital-human__coat-right" d="M188 175c-8 32-21 60-39 83h72c-5-36-16-64-33-83Z" />
          <path className="digital-human__collar digital-human__collar--left" d="M101 162l39 36-32 19-30-38Z" />
          <path className="digital-human__collar digital-human__collar--right" d="M179 162l-39 36 32 19 30-38Z" />
          <path className="digital-human__trim digital-human__trim--left" d="M93 179c13 31 29 57 47 79" />
          <path className="digital-human__trim digital-human__trim--right" d="M187 179c-13 31-29 57-47 79" />
          <rect className="digital-human__badge" x="154" y="210" width="54" height="24" rx="8" />
          <text className="digital-human__badge-text" x="181" y="226" textAnchor="middle">
            灵境
          </text>
          <path className="digital-human__neck" d="M122 138h36v38c-7 8-29 8-36 0V138Z" />
          <path className="digital-human__hair-back" d="M83 91c0-39 28-68 58-68 36 0 61 29 61 70 0 28-10 50-24 65H102c-13-16-19-39-19-67Z" />
          <path className="digital-human__ear digital-human__ear--left" d="M89 106c-14 1-18 24-5 33 8 5 14-1 14-11v-16c0-4-3-7-9-6Z" />
          <path className="digital-human__ear digital-human__ear--right" d="M191 106c14 1 18 24 5 33-8 5-14-1-14-11v-16c0-4 3-7 9-6Z" />
          <path className="digital-human__face" d="M93 88c3-34 28-53 47-53 30 0 51 24 52 58 2 43-20 76-52 76s-52-34-47-81Z" />
          <path className="digital-human__hair-front" d="M90 96c4-42 35-65 70-58 26 5 43 26 43 60-18-3-32-12-43-26-14 15-38 24-70 24Z" />
          <path className="digital-human__side-hair digital-human__side-hair--left" d="M91 96c-10 16-9 42 5 58 2-18 3-36-1-55Z" />
          <path className="digital-human__side-hair digital-human__side-hair--right" d="M189 96c10 16 9 42-5 58-2-18-3-36 1-55Z" />
          <path className="digital-human__brow digital-human__brow--left" d="M111 102c7-4 15-4 22 0" />
          <path className="digital-human__brow digital-human__brow--right" d="M147 102c7-4 15-4 22 0" />
          <g className="digital-human__eyes">
            <ellipse className="digital-human__eye digital-human__eye--left" cx="122" cy="116" rx="6.5" ry="7.5" />
            <ellipse className="digital-human__eye digital-human__eye--right" cx="158" cy="116" rx="6.5" ry="7.5" />
            <circle className="digital-human__pupil digital-human__pupil--left" cx="124" cy="117" r="2.2" />
            <circle className="digital-human__pupil digital-human__pupil--right" cx="160" cy="117" r="2.2" />
          </g>
          <path className="digital-human__nose" d="M140 120c-2 8-4 14-7 19 5 3 10 3 15 0" />
          <g className="digital-human__mouth-set">
            <path className="digital-human__mouth-shape digital-human__mouth-smile" d="M124 146c7 9 25 9 32 0" />
            <ellipse className="digital-human__mouth-shape digital-human__mouth-small" cx="140" cy="148" rx="5.8" ry="4" />
            <ellipse className="digital-human__mouth-shape digital-human__mouth-open" cx="140" cy="148" rx="7.5" ry="10.5" />
            <path className="digital-human__mouth-shape digital-human__mouth-wide" d="M124 144c8 14 24 14 32 0-8 5-24 5-32 0Z" />
          </g>
          <path className="digital-human__hand digital-human__hand--left" d="M82 238c16-10 34-8 48 4" />
          <path className="digital-human__hand digital-human__hand--right" d="M198 238c-16-10-34-8-48 4" />
          <path className="digital-human__desk-light" d="M76 267h128" />
        </svg>
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
