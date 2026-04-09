"use client";

import { startTransition, useDeferredValue, useEffect, useState } from "react";

const presets = [
  "pharmaceuticals",
  "technology",
  "agriculture",
  "banking",
  "energy",
];

const focusNotes = {
  pharmaceuticals:
    "Track domestic prescription growth, export approvals, and regulatory headlines that can quickly reprice leaders.",
  technology:
    "Watch deal momentum, AI budget commentary, and margin guidance from large-cap IT services names.",
  agriculture:
    "Monsoon progress, sowing data, and subsidy updates are the fastest-moving inputs for sentiment here.",
  banking:
    "Credit growth, deposit costs, and RBI policy signals tend to shape sector leadership in short windows.",
  energy:
    "Crude direction, power demand, and transmission or renewable capex announcements often drive the next move.",
};

function buildFileName(sector) {
  const safeSector = sector.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const date = new Date().toISOString().slice(0, 10);
  return `${safeSector || "sector"}-${date}.md`;
}

function toTitle(value) {
  return value
    .split(" ")
    .filter(Boolean)
    .map((item) => item.charAt(0).toUpperCase() + item.slice(1))
    .join(" ");
}

function extractSectionSummary(report, heading) {
  if (!report) {
    return "";
  }

  const lines = report.split("\n");
  const startIndex = lines.findIndex((line) => line.trim() === heading);

  if (startIndex === -1) {
    return "";
  }

  for (let index = startIndex + 1; index < lines.length; index += 1) {
    const line = lines[index].trim();

    if (!line) {
      continue;
    }

    if (line.startsWith("#")) {
      break;
    }

    return line;
  }

  return "";
}

function renderInlineMarkdown(text, keyPrefix) {
  const parts = [];
  const pattern = /(\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*)/g;
  let lastIndex = 0;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    if (match[2] && match[3]) {
      parts.push(
        <a
          key={`${keyPrefix}-link-${match.index}`}
          href={match[3]}
          target="_blank"
          rel="noreferrer"
        >
          {match[2]}
        </a>,
      );
    } else if (match[4]) {
      parts.push(
        <strong key={`${keyPrefix}-strong-${match.index}`}>{match[4]}</strong>,
      );
    }

    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length ? parts : text;
}

function renderFormattedReport(report) {
  const blocks = [];
  const lines = report.split("\n");
  let listItems = [];
  let listKey = 0;

  const flushList = () => {
    if (!listItems.length) {
      return;
    }

    blocks.push(
      <ul className="markdown-list" key={`list-${listKey}`}>
        {listItems.map((item, index) => (
          <li key={`list-item-${listKey}-${index}`}>
            {renderInlineMarkdown(item, `list-${listKey}-${index}`)}
          </li>
        ))}
      </ul>,
    );

    listItems = [];
    listKey += 1;
  };

  lines.forEach((rawLine, index) => {
    const line = rawLine.trim();

    if (!line) {
      flushList();
      return;
    }

    if (line.startsWith("- ")) {
      listItems.push(line.slice(2));
      return;
    }

    flushList();

    if (line.startsWith("# ")) {
      blocks.push(
        <h2 className="markdown-title" key={`title-${index}`}>
          {renderInlineMarkdown(line.slice(2), `title-${index}`)}
        </h2>,
      );
      return;
    }

    if (line.startsWith("## ")) {
      blocks.push(
        <h3 className="markdown-section" key={`section-${index}`}>
          {renderInlineMarkdown(line.slice(3), `section-${index}`)}
        </h3>,
      );
      return;
    }

    if (line.startsWith("### ")) {
      blocks.push(
        <h4 className="markdown-subsection" key={`subsection-${index}`}>
          {renderInlineMarkdown(line.slice(4), `subsection-${index}`)}
        </h4>,
      );
      return;
    }

    blocks.push(
      <p className="markdown-paragraph" key={`paragraph-${index}`}>
        {renderInlineMarkdown(line, `paragraph-${index}`)}
      </p>,
    );
  });

  flushList();
  return blocks;
}

export default function AnalyzerShell() {
  const [sector, setSector] = useState("pharmaceuticals");
  const [report, setReport] = useState("");
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [viewMode, setViewMode] = useState("preview");
  const [copied, setCopied] = useState(false);

  const deferredSector = useDeferredValue(sector);
  const normalizedSector = deferredSector.trim().toLowerCase() || "pharmaceuticals";
  const currentFocus =
    focusNotes[normalizedSector] ||
    "Use the analyzer to gather current sector context, surface opportunities, and export the markdown report.";
  const summary = extractSectionSummary(report, "## Executive Summary");
  const fileName = buildFileName(sector);

  useEffect(() => {
    if (!copied) {
      return undefined;
    }

    const timer = window.setTimeout(() => setCopied(false), 1400);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function handleSubmit(event) {
    event.preventDefault();
    setIsLoading(true);
    setError("");
    setCopied(false);

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ sector }),
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload?.detail || "Analysis request failed.");
      }

      startTransition(() => {
        setReport(payload.report);
        setMeta(payload.meta);
        setViewMode("preview");
      });
    } catch (requestError) {
      setReport("");
      setMeta(null);
      setError(requestError.message || "Analysis request failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCopy() {
    if (!report) {
      return;
    }

    try {
      await navigator.clipboard.writeText(report);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  function handleDownload() {
    if (!report) {
      return;
    }

    const blob = new Blob([report], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="studio-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Market Intelligence Desk</p>
          <h1>Trade Opportunity Studio</h1>
          <p className="hero-text">
            Run sector analysis from a single screen, keep the backend API key on the
            server, and export the markdown report for submission or review.
          </p>

          <div className="hero-ribbon">
            <span className="ribbon-pill">Next.js + FastAPI</span>
            <span className="ribbon-pill">Gemini-backed insights</span>
            <span className="ribbon-pill">Markdown export ready</span>
          </div>
        </div>

        <div className="signal-card">
          <span className="signal-label">Sector Pulse</span>
          <strong>{toTitle(normalizedSector)}</strong>
          <p>{currentFocus}</p>

          <div className="signal-grid">
            <div className="signal-tile">
              <span>Route</span>
              <strong>/api/analyze</strong>
            </div>
            <div className="signal-tile">
              <span>Session</span>
              <strong>{meta?.sessionId ? meta.sessionId.slice(0, 8) : "pending"}</strong>
            </div>
            <div className="signal-tile">
              <span>Exports</span>
              <strong>.md report</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="workspace-grid">
        <article className="control-card">
          <div className="card-header">
            <p className="card-kicker">Control Deck</p>
            <h2>Analyze an Indian sector</h2>
          </div>

          <form className="analyzer-form" onSubmit={handleSubmit}>
            <label className="field-label" htmlFor="sector">
              Sector
            </label>
            <input
              id="sector"
              name="sector"
              value={sector}
              onChange={(event) => setSector(event.target.value)}
              className="sector-input"
              placeholder="technology"
              autoComplete="off"
            />

            <div className="preset-row">
              {presets.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`preset-chip ${sector === item ? "active" : ""}`}
                  onClick={() => setSector(item)}
                >
                  {toTitle(item)}
                </button>
              ))}
            </div>

            <button
              className="primary-button"
              type="submit"
              disabled={isLoading || !sector.trim()}
            >
              {isLoading ? "Analyzing..." : "Generate Report"}
            </button>
          </form>

          {error ? <p className="error-banner">{error}</p> : null}

          <div className="focus-panel">
            <span className="focus-badge">Current Brief</span>
            <p>{currentFocus}</p>
          </div>

          <div className="status-grid">
            <div className="status-tile">
              <span>Session</span>
              <strong>{meta?.sessionId || "Pending"}</strong>
            </div>
            <div className="status-tile">
              <span>Rate Limit Left</span>
              <strong>{meta?.rateLimit?.remaining ?? "--"}</strong>
            </div>
            <div className="status-tile">
              <span>Reset Window</span>
              <strong>{meta?.rateLimit?.reset ? `${meta.rateLimit.reset}s` : "--"}</strong>
            </div>
          </div>

          <div className="tip-stack">
            <div className="tip-card">
              <span>Workflow</span>
              Search, analyze, preview, and export from one screen.
            </div>
            <div className="tip-card">
              <span>Best Input</span>
              Try broad sectors like pharmaceuticals, banking, or energy.
            </div>
          </div>
        </article>

        <article className="report-card">
          <div className="card-header report-header">
            <div>
              <p className="card-kicker">Markdown Output</p>
              <h2>Report preview</h2>
            </div>

            <div className="toolbar-cluster">
              <div className="view-toggle">
                <button
                  type="button"
                  className={`toggle-pill ${viewMode === "preview" ? "active" : ""}`}
                  onClick={() => setViewMode("preview")}
                >
                  Preview
                </button>
                <button
                  type="button"
                  className={`toggle-pill ${viewMode === "markdown" ? "active" : ""}`}
                  onClick={() => setViewMode("markdown")}
                >
                  Raw Markdown
                </button>
              </div>

              <div className="report-actions">
                <button
                  type="button"
                  className="ghost-button"
                  onClick={handleCopy}
                  disabled={!report}
                >
                  {copied ? "Copied" : "Copy"}
                </button>
                <button
                  type="button"
                  className="ghost-button"
                  onClick={handleDownload}
                  disabled={!report}
                >
                  Download .md
                </button>
              </div>
            </div>
          </div>

          {report ? (
            <div className="summary-strip">
              <div className="summary-chip">
                <span>Sector</span>
                <strong>{toTitle(normalizedSector)}</strong>
              </div>
              <div className="summary-chip wide">
                <span>Executive Snapshot</span>
                <strong>{summary || "Report generated and ready for review."}</strong>
              </div>
              <div className="summary-chip">
                <span>Export Name</span>
                <strong>{fileName}</strong>
              </div>
            </div>
          ) : null}

          <div className="report-surface">
            {isLoading ? (
              <div className="loading-state">
                <div className="loading-orb" />
                <p>Building a sector brief...</p>
                <span>
                  Pulling live market context, sending it through the analysis pipeline,
                  and formatting the markdown report.
                </span>
              </div>
            ) : report ? (
              viewMode === "preview" ? (
                <div className="markdown-prose">{renderFormattedReport(report)}</div>
              ) : (
                <pre>{report}</pre>
              )
            ) : (
              <div className="empty-state">
                <p>No report generated yet.</p>
                <span>
                  Choose a sector, run the analysis, and switch between formatted preview
                  and raw markdown once the report is ready.
                </span>
              </div>
            )}
          </div>

          <div className="report-footer">
            <span>Session-aware requests are proxied through Next.js.</span>
            <span>Backend rate-limit feedback is surfaced above after each run.</span>
          </div>
        </article>
      </section>
    </main>
  );
}
