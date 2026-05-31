import { LoaderCircle, Play, RotateCcw, Square, Volume2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { sendAvatarWebrtcOffer } from "../../api/client";

type RtcState = "idle" | "connecting" | "connected" | "media" | "failed" | "unsupported";

type AvatarRtcViewerProps = {
  autoStart?: boolean;
  broadcastDisabled?: boolean;
  broadcasting?: boolean;
  caption?: string;
  chrome?: "full" | "preview";
  disabled?: boolean;
  onFallback?: (reason: string) => void;
  onSessionChange?: (sessionId: string | null) => void;
  onStartBroadcast?: () => Promise<void> | void;
  onStopBroadcast?: () => Promise<void> | void;
  variant?: "mobile" | "kiosk";
};

function createViewerId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `lingjing-viewer-${crypto.randomUUID()}`;
  }
  return `lingjing-viewer-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function waitForIceGatheringComplete(peerConnection: RTCPeerConnection, timeoutMs = 3000) {
  if (peerConnection.iceGatheringState === "complete") {
    return Promise.resolve();
  }
  return new Promise<void>((resolve) => {
    const timer = window.setTimeout(() => {
      peerConnection.removeEventListener("icegatheringstatechange", handleChange);
      resolve();
    }, timeoutMs);
    function handleChange() {
      if (peerConnection.iceGatheringState === "complete") {
        window.clearTimeout(timer);
        peerConnection.removeEventListener("icegatheringstatechange", handleChange);
        resolve();
      }
    }
    peerConnection.addEventListener("icegatheringstatechange", handleChange);
  });
}

export function AvatarRtcViewer({
  autoStart = true,
  broadcastDisabled = false,
  broadcasting = false,
  caption,
  chrome = "full",
  disabled = false,
  onFallback,
  onSessionChange,
  onStartBroadcast,
  onStopBroadcast,
  variant = "mobile",
}: AvatarRtcViewerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const peerRef = useRef<RTCPeerConnection | null>(null);
  const dataChannelRef = useRef<RTCDataChannel | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const localBootstrapRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const startedRef = useRef(false);
  const autoStartTimerRef = useRef<number | null>(null);
  const runIdRef = useRef(0);
  const [rtcState, setRtcState] = useState<RtcState>("idle");
  const [message, setMessage] = useState("正在准备数字人观看画面。");
  const [soundEnabled, setSoundEnabled] = useState(false);

  function cleanupPeer(resetState = true) {
    runIdRef.current += 1;
    if (autoStartTimerRef.current) {
      window.clearTimeout(autoStartTimerRef.current);
      autoStartTimerRef.current = null;
    }
    peerRef.current?.getSenders().forEach((sender) => sender.track?.stop());
    peerRef.current?.getReceivers().forEach((receiver) => receiver.track?.stop());
    dataChannelRef.current?.close();
    dataChannelRef.current = null;
    peerRef.current?.close();
    peerRef.current = null;
    localBootstrapRef.current?.getTracks().forEach((track) => track.stop());
    localBootstrapRef.current = null;
    void audioContextRef.current?.close();
    audioContextRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    onSessionChange?.(null);
    if (resetState) {
      startedRef.current = false;
      setRtcState("idle");
      setSoundEnabled(false);
      setMessage("数字人直播已停止，可重新启动。");
    }
  }

  async function playVideo(withSound: boolean) {
    const video = videoRef.current;
    if (!video) {
      return;
    }
    video.muted = !withSound;
    video.volume = withSound ? 1 : 0;
    try {
      await video.play();
      setSoundEnabled(withSound);
    } catch {
      setSoundEnabled(false);
      setMessage("浏览器暂停了自动播放，点击启用声音后继续观看。");
    }
  }

  async function handleStartBroadcast() {
    await playVideo(true);
    await onStartBroadcast?.();
  }

  async function handleStopBroadcast() {
    sendInterruptSignal();
    const video = videoRef.current;
    if (video) {
      video.muted = true;
      video.volume = 0;
    }
    setSoundEnabled(false);
    await onStopBroadcast?.();
  }

  function sendInterruptSignal() {
    const dataChannel = dataChannelRef.current;
    if (!dataChannel || dataChannel.readyState !== "open") {
      setMessage("数字人停止指令暂未送达，直播通道还在连接中。");
      return false;
    }
    dataChannel.send(
      JSON.stringify({
        header: {
          name: "Interrupt",
          request_id: createViewerId(),
        },
        payload: {},
      }),
    );
    setMessage("已发送停止播报指令。");
    return true;
  }

  function restartViewer() {
    cleanupPeer(true);
    window.setTimeout(() => {
      void startViewer();
    }, 0);
  }

  async function startViewer() {
    if (peerRef.current || rtcState === "connecting") {
      return;
    }
    startedRef.current = true;
    if (disabled) {
      setRtcState("failed");
      setMessage("数字人表现层暂不可用，页面已保留 mock fallback。");
      onFallback?.("sidecar_unavailable");
      return;
    }
    if (!("RTCPeerConnection" in window)) {
      setRtcState("unsupported");
      setMessage("当前浏览器不支持 WebRTC，页面已保留降级展示。");
      onFallback?.("webrtc_unsupported");
      return;
    }

    cleanupPeer(false);
    const runId = runIdRef.current;
    const webrtcId = createViewerId();
    const peerConnection = new RTCPeerConnection();
    const remoteStream = new MediaStream();
    let audioContext: AudioContext;
    let localBootstrap: MediaStream;
    try {
      ({ audioContext, stream: localBootstrap } = await createPermissionlessBootstrapStream());
    } catch (cause) {
      const reason = cause instanceof Error ? cause.message : "permissionless_bootstrap_unavailable";
      peerConnection.close();
      setRtcState("failed");
      setMessage("当前浏览器无法创建无权限观看连接，页面已保留降级展示。");
      onFallback?.(reason);
      return;
    }
    if (runId !== runIdRef.current) {
      localBootstrap.getTracks().forEach((track) => track.stop());
      void audioContext.close();
      peerConnection.close();
      return;
    }

    peerRef.current = peerConnection;
    streamRef.current = remoteStream;
    localBootstrapRef.current = localBootstrap;
    audioContextRef.current = audioContext;
    setRtcState("connecting");
    setMessage("数字人启动中，正在接入本页观看画面。");
    setSoundEnabled(false);

    if (videoRef.current) {
      videoRef.current.srcObject = remoteStream;
      videoRef.current.muted = true;
      videoRef.current.volume = 0;
    }

    const dataChannel = peerConnection.createDataChannel("text");
    dataChannelRef.current = dataChannel;
    localBootstrap.getTracks().forEach((track) => {
      peerConnection.addTrack(track, localBootstrap);
    });
    peerConnection.addEventListener("connectionstatechange", () => {
      if (peerConnection.connectionState === "connected") {
        setRtcState((current) => (current === "media" ? "media" : "connected"));
        setMessage("数字人直播已连接，播报仍由灵境后端触发。");
      }
      if (peerConnection.connectionState === "disconnected") {
        setMessage("数字人直播正在恢复连接。");
      }
      if (["failed", "closed"].includes(peerConnection.connectionState)) {
        if (peerRef.current === peerConnection) {
          setRtcState("failed");
          setMessage("数字人直播连接已断开，页面已保留降级展示。");
          onFallback?.(`peer_${peerConnection.connectionState}`);
        }
      }
    });
    peerConnection.addEventListener("track", (event) => {
      remoteStream.addTrack(event.track);
      setRtcState("media");
      setMessage("数字人画面已接入，点击播报按钮即可同屏观看。");
      void playVideo(false);
    });

    try {
      const offer = await peerConnection.createOffer();
      await peerConnection.setLocalDescription(offer);
      await waitForIceGatheringComplete(peerConnection);
      if (runId !== runIdRef.current) {
        return;
      }
      const localDescription = peerConnection.localDescription;
      if (!localDescription?.sdp) {
        throw new Error("missing_local_sdp");
      }
      const answer = await sendAvatarWebrtcOffer({
        sdp: localDescription.sdp,
        type: "offer",
        webrtc_id: webrtcId,
      });
      if (runId !== runIdRef.current) {
        return;
      }
      if (answer.accepted === false || !answer.sdp || !answer.type) {
        throw new Error(answer.fallback_reason || answer.message || "sidecar_webrtc_rejected");
      }
      await peerConnection.setRemoteDescription({ sdp: answer.sdp, type: answer.type });
      onSessionChange?.(answer.sessionid || webrtcId);
      void playVideo(false);
    } catch (cause) {
      const reason = cause instanceof Error ? cause.message : "webrtc_failed";
      setRtcState("failed");
      setMessage("数字人直播连接失败，稍后可重试。");
      onFallback?.(reason);
      peerConnection.close();
      peerRef.current = null;
    }
  }

  useEffect(() => () => cleanupPeer(false), []);

  useEffect(() => {
    if (disabled) {
      cleanupPeer(false);
      startedRef.current = false;
      setRtcState("failed");
      setMessage("数字人表现层暂不可用，页面已保留 mock fallback。");
      setSoundEnabled(false);
    }
  }, [disabled]);

  useEffect(() => {
    if (autoStart && !disabled && !startedRef.current) {
      autoStartTimerRef.current = window.setTimeout(() => {
        autoStartTimerRef.current = null;
        void startViewer();
      }, 450);
    }
    return () => {
      if (autoStartTimerRef.current) {
        window.clearTimeout(autoStartTimerRef.current);
        autoStartTimerRef.current = null;
      }
    };
  }, [autoStart, disabled]);

  const connected = rtcState === "connected" || rtcState === "media";
  const busy = rtcState === "connecting";
  const showStartup = busy || rtcState === "idle";
  const showRetry = rtcState === "failed" || rtcState === "unsupported";
  const showStatePanel = showStartup || showRetry;
  const statusText = connected ? "直播接收中" : busy ? "启动中" : showRetry ? "备用展示" : "准备中";
  const preview = chrome === "preview";

  return (
    <div className={`avatar-rtc-viewer avatar-rtc-viewer--${variant} avatar-rtc-viewer--${rtcState} avatar-rtc-viewer--${chrome}`}>
      <video
        aria-label="数字人 WebRTC 观看画面"
        autoPlay
        className="avatar-rtc-viewer__video"
        muted={!soundEnabled}
        playsInline
        ref={videoRef}
      />
      <div className="avatar-rtc-viewer__shade" aria-hidden="true" />
      {!preview ? <div className="avatar-rtc-viewer__hud">
        <span className="avatar-rtc-viewer__dot" aria-hidden="true" />
        <span>{statusText}</span>
      </div> : null}
      {showStatePanel ? (
        <div className={`avatar-rtc-viewer__startup ${preview ? "avatar-rtc-viewer__startup--preview" : ""}`} role="status" aria-live="polite">
          {showRetry ? <RotateCcw aria-hidden="true" /> : <LoaderCircle aria-hidden="true" />}
          <strong>数字人启动中</strong>
          <span>{caption || "正在接入本页观看画面"}</span>
        </div>
      ) : null}
      {!preview ? <div className="avatar-rtc-viewer__controls" aria-label="数字人直播控制">
        {connected && onStartBroadcast ? (
          <button disabled={broadcastDisabled || broadcasting} onClick={() => void handleStartBroadcast()} type="button">
            <Play aria-hidden="true" size={18} />
            {broadcasting ? "播报中" : "开始播报"}
          </button>
        ) : null}
        {connected && onStopBroadcast ? (
          <button onClick={() => void handleStopBroadcast()} type="button">
            <Square aria-hidden="true" size={18} />
            停止播报
          </button>
        ) : null}
        {showRetry ? (
          <button onClick={restartViewer} type="button">
            <RotateCcw aria-hidden="true" size={18} />
            重试连接
          </button>
        ) : null}
        {rtcState === "idle" && !autoStart ? (
          <button onClick={() => void startViewer()} type="button">
            <Play aria-hidden="true" size={18} />
            启动数字人直播
          </button>
        ) : null}
        {connected ? (
          <button onClick={() => void playVideo(true)} type="button">
            <Volume2 aria-hidden="true" size={18} />
            启用声音
          </button>
        ) : null}
      </div> : null}
      {!preview ? <p className="avatar-rtc-viewer__message">{message}</p> : null}
    </div>
  );
}

async function createPermissionlessBootstrapStream() {
  const stream = new MediaStream();
  const canvas = document.createElement("canvas");
  canvas.width = 16;
  canvas.height = 16;
  const context = canvas.getContext("2d");
  if (!context || typeof canvas.captureStream !== "function") {
    throw new Error("canvas_capture_stream_unavailable");
  }
  context.fillStyle = "#101816";
  context.fillRect(0, 0, canvas.width, canvas.height);
  const canvasStream = canvas.captureStream(1);
  const videoTrack = canvasStream.getVideoTracks()[0];
  if (!videoTrack) {
    throw new Error("synthetic_video_track_unavailable");
  }
  stream.addTrack(videoTrack);

  const AudioContextCtor = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextCtor) {
    videoTrack.stop();
    throw new Error("audio_context_unavailable");
  }
  const audioContext = new AudioContextCtor();
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();
  const destination = audioContext.createMediaStreamDestination();
  gain.gain.value = 0;
  oscillator.connect(gain);
  gain.connect(destination);
  oscillator.start();
  const audioTrack = destination.stream.getAudioTracks()[0];
  if (!audioTrack) {
    videoTrack.stop();
    oscillator.stop();
    await audioContext.close();
    throw new Error("synthetic_audio_track_unavailable");
  }
  stream.addTrack(audioTrack);
  return { audioContext, stream };
}
