import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & {
  strokeWidth?: number;
};

function IconBase({ children, strokeWidth = 1.8, ...props }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      focusable="false"
      height="24"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={strokeWidth}
      viewBox="0 0 24 24"
      width="24"
      {...props}
    >
      {children}
    </svg>
  );
}

export function LotusIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 20c-4.4-2.1-6.7-5.2-6.9-9.1 3 .3 5.3 2.1 6.9 5.1 1.6-3 3.9-4.8 6.9-5.1-.2 3.9-2.5 7-6.9 9.1Z" />
      <path d="M12 16c-2.4-2.8-2.4-6.4 0-10 2.4 3.6 2.4 7.2 0 10Z" />
      <path d="M4.2 18.6c2.5 1 5.1 1.5 7.8 1.5s5.3-.5 7.8-1.5" />
    </IconBase>
  );
}

export function BuddhaIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M7.3 19.5h9.4" />
      <path d="M8.8 17.4c.8-1.8 1.1-3.5 1-5.1" />
      <path d="M15.2 17.4c-.8-1.8-1.1-3.5-1-5.1" />
      <path d="M9.8 9.2a2.2 2.2 0 0 1 4.4 0v2.1a2.2 2.2 0 0 1-4.4 0V9.2Z" />
      <path d="M10.2 7.3c.4-1.8 1-2.8 1.8-3.1.8.3 1.4 1.3 1.8 3.1" />
      <path d="M6.1 17.8c1.1-2.3 3.1-3.4 5.9-3.4 2.8 0 4.8 1.1 5.9 3.4" />
      <path d="M6.3 14.2c1.6.4 2.9.3 3.9-.5" />
      <path d="M17.7 14.2c-1.6.4-2.9.3-3.9-.5" />
    </IconBase>
  );
}

export function ScenicCameraIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M4.5 8.3h3.1l1.2-2h6.4l1.2 2h3.1v10.2h-15V8.3Z" />
      <circle cx="12" cy="13.4" r="3.1" />
      <path d="M10.4 13.4 12 11.8l1.6 1.6" />
      <path d="M7.2 10.1h.1" />
    </IconBase>
  );
}

export function RoutePathIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M5.4 18.2c3.1-4.2 10.1-.4 13.2-4.6 1.3-1.8.4-4.3-1.8-4.8" />
      <path d="M6.1 18.3a2 2 0 1 1-2.6-2.9 2 2 0 0 1 2.6 2.9Z" />
      <path d="M18.7 8.7a2 2 0 1 0-2.7-2.9 2 2 0 0 0 2.7 2.9Z" />
    </IconBase>
  );
}

export function VisitorIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M6.5 20.2v-1.9c0-2.8 2.2-5 5.5-5s5.5 2.2 5.5 5v1.9" />
      <path d="M9 9a3 3 0 0 1 6 0 3 3 0 0 1-6 0Z" />
      <path d="M6.5 19.9h11" />
      <path d="M7.4 12.8a8.2 8.2 0 0 1 9.2 0" />
    </IconBase>
  );
}

export function BridgeIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M4 16.6h16" />
      <path d="M5.2 16.5c.6-4 3-6 6.8-6s6.2 2 6.8 6" />
      <path d="M8.3 16.5c.4-2.2 1.6-3.3 3.7-3.3s3.3 1.1 3.7 3.3" />
      <path d="M5.2 11.2h13.6" />
      <path d="M6.5 9.2v2" />
      <path d="M17.5 9.2v2" />
      <path d="M6.3 19.2c1.3-.5 2.6-.5 3.9 0s2.6.5 3.9 0 2.6-.5 3.9 0" />
    </IconBase>
  );
}

export function BodhiLeafIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12.4 20.2c-.2-5.8 1.9-10.6 6.4-14.4-5.4-.3-9.2 1.5-11.3 5.4-1.9 3.5-.7 6.4 2.4 7.7" />
      <path d="M12.4 20.2 8.2 12" />
      <path d="M10 15.6 7.2 15" />
      <path d="M11 13.1 8.5 11.8" />
      <path d="M12 10.8 10.4 8.9" />
    </IconBase>
  );
}

export function BrahmaPalaceIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M4.4 19.4h15.2" />
      <path d="M5.5 19.4v-6.1h13v6.1" />
      <path d="M7.3 19.4v-4h3.1v4" />
      <path d="M13.6 19.4v-4h3.1v4" />
      <path d="M5 13.3c1.9-.5 3.4-1.4 4.5-2.8h5c1.1 1.4 2.6 2.3 4.5 2.8" />
      <path d="M8 10.5c1.2-2.1 2.5-3.4 4-3.9 1.5.5 2.8 1.8 4 3.9" />
      <path d="M12 6.6V4.2" />
      <path d="M10.8 4.2h2.4" />
    </IconBase>
  );
}

export function CrowdWaveIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M4.4 10.6a2.1 2.1 0 0 1 4.2 0" />
      <path d="M9.9 10.6a2.1 2.1 0 0 1 4.2 0" />
      <path d="M15.4 10.6a2.1 2.1 0 0 1 4.2 0" />
      <path d="M4 15.1c1.5-1 3-1 4.5 0s3 1 4.5 0 3-1 4.5 0 1.8 1 2.5.5" />
      <path d="M4 18.4c1.5-1 3-1 4.5 0s3 1 4.5 0 3-1 4.5 0 1.8 1 2.5.5" />
    </IconBase>
  );
}

export function QrHandoffIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M5 5h5v5H5z" />
      <path d="M14 5h5v5h-5z" />
      <path d="M5 14h5v5H5z" />
      <path d="M14 14h2.2" />
      <path d="M19 14v2.2" />
      <path d="M14 19h5v-2" />
      <path d="M16.5 16.5h.1" />
      <path d="M7 7h1" />
      <path d="M16 7h1" />
      <path d="M7 16h1" />
    </IconBase>
  );
}

export function SourceDocIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M7 4.4h6.5L18 8.9v10.7H7V4.4Z" />
      <path d="M13.5 4.5v4.4H18" />
      <path d="M9.5 12.2h5" />
      <path d="M9.5 15h5" />
      <path d="M15.3 18.5c.8-.7 1.8-1.1 3-1.1" />
      <path d="M18.3 17.4c-.9.7-1.9 1.1-3 1.1" />
    </IconBase>
  );
}

export function EventBellIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M7.2 17.5h9.6" />
      <path d="M8 17.5v-5.4a4 4 0 0 1 8 0v5.4" />
      <path d="M10.4 19.2a1.8 1.8 0 0 0 3.2 0" />
      <path d="M12 6.1V4.3" />
      <path d="M10 21.1c1.3-.6 2.7-.6 4 0" />
    </IconBase>
  );
}
