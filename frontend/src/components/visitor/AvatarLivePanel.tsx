import type { AvatarStatusResponse } from "../../api/client";
import type { DigitalHumanState } from "../DigitalHumanMock";
import { AvatarRtcViewer } from "./AvatarRtcViewer";

export const DEFAULT_AVATAR_SIDECAR_URL = "http://127.0.0.1:8282";

type AvatarLivePanelProps = {
  broadcastDisabled?: boolean;
  broadcasting?: boolean;
  caption?: string;
  chrome?: "full" | "preview";
  onStartBroadcast?: () => Promise<void> | void;
  onStopBroadcast?: () => Promise<void> | void;
  sidecarUrl?: string;
  state?: DigitalHumanState;
  status?: AvatarStatusResponse | null;
  title?: string;
  variant?: "mobile" | "kiosk";
};

export function AvatarLivePanel({
  broadcastDisabled,
  broadcasting,
  caption,
  chrome = "full",
  onStartBroadcast,
  onStopBroadcast,
  sidecarUrl,
  status,
  title = "灵境数字人",
  variant = "mobile",
}: AvatarLivePanelProps) {
  const statusLoaded = status !== undefined && status !== null;
  const sidecarKnownDown = statusLoaded && !status.sidecar_ready;
  const hasActiveSession = Boolean(status?.active_session_id);
  const statusText = sidecarKnownDown ? "备用展示" : hasActiveSession ? "直播接收中" : "自动启动";
  const helperText = sidecarKnownDown
    ? "数字人画面暂不可用，主流程继续可用。"
    : hasActiveSession
      ? "数字人表现层已接入，播报由灵境后端统一触发。"
      : `正在连接 ${sidecarUrl || DEFAULT_AVATAR_SIDECAR_URL}`;

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
          autoStart={!sidecarKnownDown}
          broadcastDisabled={broadcastDisabled}
          broadcasting={broadcasting}
          caption={caption || helperText}
          chrome={chrome}
          disabled={sidecarKnownDown}
          onStartBroadcast={onStartBroadcast}
          onStopBroadcast={onStopBroadcast}
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
