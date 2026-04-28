import { Camera, Map, MessageSquareText, Mic, Navigation, Send } from "lucide-react";

import { Button } from "../components/Button";
import { DigitalHumanMock } from "../components/DigitalHumanMock";
import { IconButton } from "../components/IconButton";
import { PageShell } from "../components/Shell";
import { SpotCard } from "../components/SpotCard";
import { StatusBadge } from "../components/StatusBadge";

export function MobileHomePage() {
  return (
    <PageShell className="mobile-page">
      <header className="mobile-header">
        <div>
          <span className="eyebrow">灵山胜境</span>
          <h1>灵境导游</h1>
        </div>
        <StatusBadge tone="ok">mock 在线</StatusBadge>
      </header>

      <DigitalHumanMock state="speaking" className="mobile-avatar" />

      <section className="mobile-greeting" aria-labelledby="mobile-greeting-title">
        <span className="eyebrow">当前讲解</span>
        <h2 id="mobile-greeting-title">你好，我是灵境。现在可以为你讲解景点、识别照片或规划路线。</h2>
      </section>

      <section className="mobile-chat" aria-label="模拟讲解对话">
        <div className="chat-row chat-row--guide">
          <strong>灵境</strong>
          <p>九龙灌浴是灵山胜境的动态标志景观，我可以结合演出时间为你安排下一站。</p>
        </div>
        <div className="chat-row chat-row--visitor">
          <strong>游客</strong>
          <p>我带孩子，想轻松一点。</p>
        </div>
      </section>

      <SpotCard
        title="九龙灌浴"
        description="适合亲子观看的佛陀诞生故事演绎，建议提前 15 分钟到广场侧前方等候。"
        meta="中轴线核心广场 · 推荐停留 30 分钟"
      />

      <form className="mobile-input" aria-label="文本提问">
        <label className="sr-only" htmlFor="mobile-question">
          输入问题
        </label>
        <input
          className="text-input"
          id="mobile-question"
          placeholder="问问灵境，例如：梵宫怎么走？"
          type="text"
        />
        <Button type="submit" aria-label="发送问题" icon={<Send size={18} />} variant="primary">
          发送
        </Button>
      </form>

      <nav className="mobile-actions" aria-label="游客主操作">
        <IconButton icon={Mic} label="语音" />
        <IconButton icon={MessageSquareText} label="文本" />
        <IconButton icon={Camera} label="拍照" />
        <IconButton icon={Map} label="路线" />
      </nav>

      <a className="route-link" href="/kiosk">
        <Navigation aria-hidden="true" size={18} />
        查看景区终端演示
      </a>
    </PageShell>
  );
}
