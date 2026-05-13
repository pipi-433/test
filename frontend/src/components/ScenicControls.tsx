import type { ReactNode } from "react";

import {
  BuddhaImageIcon,
  LotusImageIcon,
  RoutePathImageIcon,
  ScenicCameraImageIcon,
  VisitorImageIcon,
} from "./icons/LingshanImageIcons";

type ScenicNavKey = "recommend" | "guide" | "vision" | "route" | "mine";

const navItems: Array<{
  key: ScenicNavKey;
  label: string;
  icon: ReactNode;
}> = [
  { key: "recommend", label: "推荐", icon: <LotusImageIcon size={31} /> },
  { key: "guide", label: "游灵山", icon: <BuddhaImageIcon size={31} /> },
  { key: "vision", label: "识景", icon: <ScenicCameraImageIcon size={31} /> },
  { key: "route", label: "路线", icon: <RoutePathImageIcon size={31} /> },
  { key: "mine", label: "我的", icon: <VisitorImageIcon size={31} /> },
];

export function ScenicBottomNav({
  active,
  onSelect,
}: {
  active: ScenicNavKey;
  onSelect: (key: ScenicNavKey) => void;
}) {
  return (
    <nav className="scenic-bottom-nav" aria-label="游客底部导航">
      {navItems.map((item) => (
        <button
          aria-current={active === item.key ? "page" : undefined}
          className={active === item.key ? "scenic-bottom-nav__item scenic-bottom-nav__item--active" : "scenic-bottom-nav__item"}
          key={item.key}
          onClick={() => onSelect(item.key)}
          type="button"
        >
          {item.icon}
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}

export function ScenicActionTile({
  active = false,
  caption,
  children,
  icon,
  onClick,
  tone = "default",
}: {
  active?: boolean;
  caption?: string;
  children: ReactNode;
  icon: ReactNode;
  onClick: () => void;
  tone?: "default" | "primary" | "warning" | "danger";
}) {
  return (
    <button
      className={`scenic-action-tile scenic-action-tile--${tone} ${active ? "scenic-action-tile--active" : ""}`}
      onClick={onClick}
      type="button"
    >
      <span className="scenic-action-tile__icon">{icon}</span>
      <span className="scenic-action-tile__label">{children}</span>
      {caption ? <small>{caption}</small> : null}
    </button>
  );
}

export function ScenicSegmentedControl<T extends string>({
  items,
  onChange,
  value,
}: {
  items: Array<{ icon?: ReactNode; label: string; value: T }>;
  onChange: (value: T) => void;
  value: T;
}) {
  return (
    <div className="scenic-segmented-control" role="group" aria-label="分段选项">
      {items.map((item) => (
        <button
          aria-pressed={value === item.value}
          className={value === item.value ? "scenic-segmented-control__item scenic-segmented-control__item--active" : "scenic-segmented-control__item"}
          key={item.value}
          onClick={() => onChange(item.value)}
          type="button"
        >
          {item.icon}
          <span>{item.label}</span>
        </button>
      ))}
    </div>
  );
}

export function RouteConstraintChip({
  children,
  onRemove,
  tone,
}: {
  children: ReactNode;
  onRemove: () => void;
  tone: "must" | "optional" | "avoid";
}) {
  return (
    <button className={`route-constraint-chip route-constraint-chip--${tone}`} onClick={onRemove} type="button">
      <span>{tone === "must" ? "必去" : tone === "optional" ? "可选" : "避开"}</span>
      {children}
      <small>移除</small>
    </button>
  );
}

export function SourceChip({ children, icon }: { children: ReactNode; icon?: ReactNode }) {
  return (
    <span className="source-chip">
      {icon}
      {children}
    </span>
  );
}

export type { ScenicNavKey };
