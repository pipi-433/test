import { MapPin } from "lucide-react";

export function SpotCard({
  description,
  meta,
  title,
}: {
  description: string;
  meta: string;
  title: string;
}) {
  return (
    <article className="spot-card">
      <div>
        <span className="spot-card__label">推荐景点</span>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      <div className="spot-card__meta">
        <MapPin aria-hidden="true" size={16} />
        <span>{meta}</span>
      </div>
    </article>
  );
}
