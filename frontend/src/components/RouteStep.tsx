export function RouteStep({
  description,
  index,
  time,
  title,
}: {
  description: string;
  index: number;
  time: string;
  title: string;
}) {
  return (
    <article className="route-step">
      <span className="route-step__index">{index}</span>
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
        <time>{time}</time>
      </div>
    </article>
  );
}
