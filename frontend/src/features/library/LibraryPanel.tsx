import type { DocumentSummary } from "../../types/api";

interface LibraryPanelProps {
  documents: DocumentSummary[];
  loading: boolean;
}

export function LibraryPanel({ documents, loading }: LibraryPanelProps) {
  const counts = documents.reduce<Record<string, number>>((all, document) => {
    all[document.status] = (all[document.status] ?? 0) + 1;
    return all;
  }, {});

  return (
    <aside className="library-panel">
      <div className="library-heading">
        <div>
          <p className="eyebrow">Corpus</p>
          <h2>{loading ? "Loading…" : `${documents.length} documents`}</h2>
        </div>
        <span className="ready-count">{counts.ready ?? 0} ready</span>
      </div>
      <div className="status-summary">
        <span>Ready {counts.ready ?? 0}</span>
        <span>Failed {counts.failed ?? 0}</span>
        <span>Stale {counts.stale ?? 0}</span>
      </div>
      <div className="document-list">
        {documents.map((document) => (
          <article className="document-row" key={document.id}>
            <span className={`status-dot status-${document.status}`} aria-label={document.status} />
            <div>
              <p title={document.sourcePath}>{document.displayName}</p>
              <span>
                S{document.semester ?? "—"} · {document.course ?? "unclassified"} · {document.pageCount ?? "—"} pp
              </span>
            </div>
          </article>
        ))}
        {!loading && documents.length === 0 && (
          <p className="empty-state">No documents are cataloged yet. Start an indexing job.</p>
        )}
      </div>
    </aside>
  );
}

