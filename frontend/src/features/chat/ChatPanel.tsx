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

  const courses = [
    ...new Set(
      documents
        .map((document) => document.course)
        .filter((value): value is string => Boolean(value)),
    ),
  ].sort();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
      setError(caught instanceof ApiError ? caught.message : "The answer request failed.");
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
            <select value={semester} onChange={(event) => setSemester(event.target.value)}>
              <option value="">All semesters</option>
              {Array.from({ length: 8 }, (_, index) => index + 1).map((value) => (
                <option key={value} value={value}>Semester {value}</option>
              ))}
            </select>
          </label>
          <label>
            Course
            <select value={course} onChange={(event) => setCourse(event.target.value)}>
              <option value="">All courses</option>
              {courses.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <button type="submit" disabled={isAsking || !question.trim()}>
            {isAsking ? "Grounding answer…" : "Ask notes"}
          </button>
        </div>
      </form>

      {error && <p className="error-message" role="alert">{error}</p>}
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
