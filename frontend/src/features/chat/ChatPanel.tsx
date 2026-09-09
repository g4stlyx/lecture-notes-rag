import { useState, type FormEvent } from "react";

import { ApiError, askQuestion } from "../../lib/api";
import type { ChatResponse, DocumentSummary } from "../../types/api";
import { SourceList } from "../sources/SourceList";

interface ChatPanelProps {
  documents: DocumentSummary[];
}

export function ChatPanel({ documents }: ChatPanelProps) {
  const [question, setQuestion] = useState("");
  const [semester, setSemester] = useState<string>("");
  const [course, setCourse] = useState("");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const readyDocuments = documents.filter((document) => document.status === "ready");
  const selectedSemester = semester ? Number(semester) : undefined;
  const courses = [
    ...new Set(
      readyDocuments
        .filter((document) => selectedSemester === undefined || document.semester === selectedSemester)
        .map((document) => document.course)
        .filter((value): value is string => Boolean(value)),
    ),
  ].sort();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await askQuestionFromNotes();
  }

  async function askQuestionFromNotes() {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isAsking) {
      return;
    }
    setIsAsking(true);
    setError(null);
    setResponse(null);
    try {
      const answer = await askQuestion({
        question: trimmedQuestion,
        ...(semester ? { semester: Number(semester) } : {}),
        ...(course ? { course } : {}),
      });
      setResponse(answer);
    } catch (caught) {
      setError(messageForChatError(caught));
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <main className="chat-panel">
      <div className="hero">
        <p className="eyebrow">Private study copilot</p>
        <h1>Ask your eight semesters.</h1>
        <p>Every answer is constrained to your notes and linked back to the exact source page.</p>
      </div>

      <form className="question-form" onSubmit={submit}>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="For example: Explain the difference between a process and a thread."
          rows={4}
          maxLength={4000}
          aria-label="Question about lecture notes"
        />
        <div className="scope-row">
          <label>
            Semester
            <select
              value={semester}
              onChange={(event) => {
                setSemester(event.target.value);
                setCourse("");
              }}
            >
              <option value="">All semesters</option>
              {Array.from({ length: 8 }, (_, index) => index + 1).map((value) => (
                <option key={value} value={value}>Semester {value}</option>
              ))}
            </select>
          </label>
          <label>
            Course
            <select
              value={course}
              disabled={courses.length === 0}
              onChange={(event) => setCourse(event.target.value)}
            >
              <option value="">
                {courses.length === 0 ? "No indexed courses" : "All courses"}
              </option>
              {courses.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <button type="submit" disabled={isAsking || !question.trim() || readyDocuments.length === 0}>
            {isAsking ? "Grounding answer…" : readyDocuments.length === 0 ? "Index corpus first" : "Ask notes"}
          </button>
        </div>
      </form>
      {readyDocuments.length === 0 && (
        <p className="indexing-hint">
          No indexed notes are available yet. Start <strong>Index corpus</strong> before asking a question.
        </p>
      )}

      {error && (
        <section className="error-message" role="alert">
          <div>
            <strong>Answer generation is temporarily unavailable</strong>
            <p>{error}</p>
          </div>
          <button onClick={() => void askQuestionFromNotes()} disabled={isAsking} type="button">
            Try again
          </button>
        </section>
      )}
      {response && (
        <section className="answer-card" aria-live="polite">
          <div className="answer-heading">
            <p className="eyebrow">Grounded answer</p>
            <span className={response.grounded ? "grounded" : "ungrounded"}>
              {response.grounded ? "Evidence supported" : "Insufficient evidence"}
            </span>
          </div>
          <p className="answer-text">{response.answer}</p>
          <SourceList sources={response.sources} />
          <p className="answer-footer">{response.latencyMs} ms {response.model ? `· ${response.model}` : ""}</p>
        </section>
      )}
    </main>
  );
}

function messageForChatError(error: unknown): string {
  if (error instanceof ApiError && error.status === 503) {
    return "Gemini is experiencing high demand. Your notes are indexed and safe; wait a moment, then retry.";
  }
  if (error instanceof ApiError) {
    return error.message;
  }
  return "The answer request failed before a response was generated. Please try again.";
}
