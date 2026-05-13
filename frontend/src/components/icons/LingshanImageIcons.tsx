import type { CSSProperties } from "react";

export const lingshanImageIconPaths = {
  lotus: "/assets/icons/lingshan/lotus.png",
  buddha: "/assets/icons/lingshan/buddha.png",
  "scenic-camera": "/assets/icons/lingshan/scenic-camera.png",
  "route-path": "/assets/icons/lingshan/route-path.png",
  visitor: "/assets/icons/lingshan/visitor.png",
  bridge: "/assets/icons/lingshan/bridge.png",
  "bodhi-leaf": "/assets/icons/lingshan/bodhi-leaf.png",
  "brahma-palace": "/assets/icons/lingshan/brahma-palace.png",
  "crowd-wave": "/assets/icons/lingshan/crowd-wave.png",
  "qr-handoff": "/assets/icons/lingshan/qr-handoff.png",
  "source-doc": "/assets/icons/lingshan/source-doc.png",
  "event-bell": "/assets/icons/lingshan/event-bell.png",
} as const;

export type LingshanImageIconName = keyof typeof lingshanImageIconPaths;

export function ImageIcon({
  alt = "",
  className = "",
  name,
  size = 24,
}: {
  alt?: string;
  className?: string;
  name: LingshanImageIconName;
  size?: number | string;
}) {
  const decorative = alt === "";
  const style = {
    "--image-icon-size": typeof size === "number" ? `${size}px` : size,
  } as CSSProperties;

  return (
    <img
      alt={alt}
      aria-hidden={decorative ? "true" : undefined}
      className={`lingshan-image-icon ${className}`}
      draggable={false}
      src={lingshanImageIconPaths[name]}
      style={style}
    />
  );
}

export function LotusImageIcon(props: Omit<Parameters<typeof ImageIcon>[0], "name">) {
  return <ImageIcon name="lotus" {...props} />;
}

export function BuddhaImageIcon(props: Omit<Parameters<typeof ImageIcon>[0], "name">) {
  return <ImageIcon name="buddha" {...props} />;
}

export function ScenicCameraImageIcon(props: Omit<Parameters<typeof ImageIcon>[0], "name">) {
  return <ImageIcon name="scenic-camera" {...props} />;
}

export function RoutePathImageIcon(props: Omit<Parameters<typeof ImageIcon>[0], "name">) {
  return <ImageIcon name="route-path" {...props} />;
}

export function VisitorImageIcon(props: Omit<Parameters<typeof ImageIcon>[0], "name">) {
  return <ImageIcon name="visitor" {...props} />;
}
