import type { SourceCitation } from "../../types/api";

interface SourceListProps {
  sources: SourceCitation[];
}

export function SourceList({ sources }: SourceListProps) {
  if (sources.length === 0) {
    return null;
  }

  return (
    <section className="sources" aria-label="Answer sources">
      <p className="eyebrow">Sources used</p>
      {sources.map((source) => (
        <article className="source-card" key={source.label}>
          <div className="source-title-row">
            <span className="citation-label">[{source.label}]</span>
            <a href={`${source.openUrl}#page=${source.pageStart}`} target="_blank" rel="noreferrer">
              {source.title}
            </a>
          </div>
          <p className="source-meta">
            Semester {source.semester ?? "—"} · {source.course ?? "Unclassified"} · page
            {source.pageStart === source.pageEnd ? " " : "s "}
            {source.pageStart}{source.pageStart === source.pageEnd ? "" : `–${source.pageEnd}`}
          </p>
          <p className="source-excerpt">{source.excerpt}</p>
        </article>
      ))}
    </section>
  );
}

