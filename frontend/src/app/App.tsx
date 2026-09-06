import { useCallback, useEffect, useState } from "react";

import { ApiError, createIngestionJob, getIngestionJob, listDocuments } from "../lib/api";
import type { DocumentSummary, IngestionJob } from "../types/api";
import { ChatPanel } from "../features/chat/ChatPanel";
import { LibraryPanel } from "../features/library/LibraryPanel";

export function App() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [job, setJob] = useState<IngestionJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const response = await listDocuments();
      setDocuments(response.items);
      setError(null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not reach the API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) {
      return;
    }
    const timer = window.setInterval(() => {
      void getIngestionJob(job.id).then((nextJob) => {
        setJob(nextJob);
        if (["completed", "failed"].includes(nextJob.status)) {
          void refreshDocuments();
        }
      }).catch(() => undefined);
    }, 1_500);
    return () => window.clearInterval(timer);
  }, [job, refreshDocuments]);

  async function startIngestion() {
    try {
      const nextJob = await createIngestionJob();
      setJob(nextJob);
      setError(null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not start indexing.");
    }
  }

  const jobRunning = job && ["queued", "running"].includes(job.status);

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/">Lecture Notes <span>RAG</span></a>
        <div className="indexing-control">
          {job && <span className={`job-status job-${job.status}`}>{job.status}: {job.processedCount + job.skippedCount}/{job.discoveredCount || "?"}</span>}
          <button className="secondary-button" onClick={() => void startIngestion()} disabled={Boolean(jobRunning)}>
            {jobRunning ? "Indexing…" : "Index corpus"}
          </button>
        </div>
      </header>
      {error && <p className="top-error" role="alert">{error}</p>}
      {job?.status === "paused" && job.errorSummary && (
        <p className="top-error" role="status">{job.errorSummary}</p>
      )}
      <div className="workspace">
        <ChatPanel documents={documents} />
        <LibraryPanel documents={documents} loading={loading} />
      </div>
    </div>
  );
}
