import type { ButtonHTMLAttributes } from "react";
import type { LucideIcon } from "lucide-react";

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  icon: LucideIcon;
  label: string;
  size?: "mobile" | "kiosk" | "compact";
};

export function IconButton({
  className = "",
  icon: Icon,
  label,
  size = "mobile",
  ...props
}: IconButtonProps) {
  return (
    <button
      className={`icon-button icon-button--${size} ${className}`}
      aria-label={label}
      title={label}
      {...props}
    >
      <Icon aria-hidden="true" />
      <span>{label}</span>
    </button>
  );
}
