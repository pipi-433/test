import type { AvatarStatusResponse } from "../../api/client";
import type { DigitalHumanState } from "../DigitalHumanMock";
import { AvatarRtcViewer } from "./AvatarRtcViewer";

export const DEFAULT_AVATAR_SIDECAR_URL = "http://127.0.0.1:8011";

type AvatarLivePanelProps = {
  autoStart?: boolean;
  broadcastDisabled?: boolean;
  broadcasting?: boolean;
  caption?: string;
  chrome?: "full" | "preview";
  onStartBroadcast?: () => Promise<void> | void;
  onStopBroadcast?: () => Promise<void> | void;
  onSessionChange?: (sessionId: string | null) => void;
  sidecarUrl?: string;
  state?: DigitalHumanState;
  status?: AvatarStatusResponse | null;
  title?: string;
  variant?: "mobile" | "kiosk";
};

export function AvatarLivePanel({
  autoStart = true,
  broadcastDisabled,
  broadcasting,
  caption,
  chrome = "full",
  onStartBroadcast,
  onStopBroadcast,
  onSessionChange,
  sidecarUrl,
  status,
  title = "灵境数字人",
  variant = "mobile",
}: AvatarLivePanelProps) {
  const statusLoaded = status !== undefined && status !== null;
  const sidecarKnownDown = statusLoaded && !status.sidecar_ready;
  const hasActiveSession = Boolean(status?.active_session_id);
  const engineLabel = status?.engine === "openavatarchat" ? "legacy" : "LiveTalking";
  const statusText = sidecarKnownDown ? "mock fallback" : hasActiveSession ? "直播接收中" : `${engineLabel} 主线`;
  const helperText = sidecarKnownDown
    ? "数字人表现层暂不可用，已保留 mock fallback，导览主流程继续可用。"
    : hasActiveSession
      ? "数字人表现层已接入，播报由灵境后端统一触发。"
      : `正在连接 ${engineLabel} 数字人表现层 ${sidecarUrl || DEFAULT_AVATAR_SIDECAR_URL}`;

  return (
    <section className={`avatar-live-panel avatar-live-panel--${variant}`} aria-label={`${title}直播画面`}>
      <div className="avatar-live-panel__bar">
        <div className="avatar-live-panel__title">
          <span className="avatar-live-panel__live-dot" aria-hidden="true" />
          <div>
            <strong>{title}</strong>
            <span>{statusText}</span>
          </div>
        </div>
      </div>

      <div className="avatar-live-panel__frame is-live">
        <AvatarRtcViewer
          autoStart={autoStart}
          broadcastDisabled={broadcastDisabled}
          broadcasting={broadcasting}
          caption={caption || helperText}
          chrome={chrome}
          disabled={false}
          onStartBroadcast={onStartBroadcast}
          onStopBroadcast={onStopBroadcast}
          onSessionChange={onSessionChange}
          variant={variant}
        />
      </div>

      <div className="avatar-live-panel__caption">
        <span>{caption}</span>
        <small>{helperText}</small>
      </div>
    </section>
  );
}
