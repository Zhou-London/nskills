"use client";

import { useState } from "react";

/**
 * Buttons that act on files on the machine serving the UI, via /api/open:
 * open in the default app, reveal in the file manager, diff two files, or
 * copy the absolute path. Failures surface as a short inline message.
 */

async function post(body: unknown): Promise<string> {
  const res = await fetch("/api/open", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json?.error || `HTTP ${res.status}`);
  return json?.tool ?? "";
}

export function useOpener() {
  const [note, setNote] = useState("");
  async function call(body: unknown, ok: string) {
    setNote("…");
    try {
      const tool = await post(body);
      setNote(tool ? `${ok} (${tool})` : ok);
    } catch (err) {
      setNote(String(err instanceof Error ? err.message : err));
    }
    setTimeout(() => setNote(""), 4000);
  }
  return { note, call };
}

export function FileActions({
  path,
  label = "Open",
  compact = false,
}: {
  path: string;
  label?: string;
  compact?: boolean;
}) {
  const { note, call } = useOpener();
  const [copied, setCopied] = useState(false);
  return (
    <span className="file-actions">
      <button
        className="mini"
        title={`Open ${path} in the default application`}
        onClick={() => call({ action: "open", path }, "opened")}
      >
        ↗ {label}
      </button>
      {!compact && (
        <button
          className="mini"
          title={`Reveal ${path} in the file manager`}
          onClick={() => call({ action: "reveal", path }, "revealed")}
        >
          ⌸ Reveal
        </button>
      )}
      {!compact && (
        <button
          className="mini"
          title={path}
          onClick={() => {
            navigator.clipboard?.writeText(path);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
        >
          {copied ? "✓ copied" : "⧉ Path"}
        </button>
      )}
      {note && <span className="mini-note">{note}</span>}
    </span>
  );
}

export function DiffButton({
  a,
  b,
  label,
}: {
  a: string;
  b: string;
  label: string;
}) {
  const { note, call } = useOpener();
  return (
    <span className="file-actions">
      <button
        className="mini"
        title={`Diff locally:\n${a}\n${b}`}
        onClick={() => call({ action: "diff", paths: [a, b] }, "diffing")}
      >
        ⇄ {label}
      </button>
      {note && <span className="mini-note">{note}</span>}
    </span>
  );
}
