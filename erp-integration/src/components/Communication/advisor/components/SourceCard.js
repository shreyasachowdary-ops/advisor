export default function SourceCard({ source }) {
  const href = typeof source.url === "string" && /^https?:\/\//i.test(source.url) ? source.url : null;

  return (
    <article className="source-card">
      <div>
        <p>{source.publisher ?? source.section ?? "Source"}</p>
        <h4>{source.title}</h4>
        {source.description && <span>{source.description}</span>}
      </div>
      {href ? (
        <a href={href} target="_blank" rel="noreferrer">
          View source
        </a>
      ) : (
        <span>{source.source_id || source.chunk_id || "Retrieved chunk"}</span>
      )}
    </article>
  );
}
