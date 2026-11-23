import SourceCard from "./SourceCard";

export default function SourcesList({ sources }) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <section className="sources-section">
      <div className="section-title-row">
        <h3>Sources used</h3>
        <span>Retrieved material</span>
      </div>
      <div className="sources-grid">
        {sources.map((source) => (
          <SourceCard key={`${source.chunk_id || source.source_id}-${source.url || source.title}`} source={source} />
        ))}
      </div>
    </section>
  );
}
