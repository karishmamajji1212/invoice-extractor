import { useCallback, useEffect, useRef, useState } from "react";
import {
  FileSpreadsheet,
  Loader2,
  AlertCircle,
  Globe,
  Sparkles,
} from "lucide-react";
import { Dropzone, ResultsPanel } from "@/components/Dropzone";
import { streamExtraction } from "@/sseClient";
import type {
  FileResult,
  HealthResponse,
  SSEQueueEvent,
  SSETokenEvent,
} from "@/types";

function App() {
  const [files, setFiles] = useState<File[]>([]);
  const [results, setResults] = useState<FileResult[]>([]);
  const [processing, setProcessing] = useState(false);
  const [done, setDone] = useState(false);
  const [successCount, setSuccessCount] = useState(0);
  const [errorCount, setErrorCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? r.json() : null))
      .then((d: HealthResponse | null) => setHealth(d))
      .catch(() => setHealth(null));
  }, []);

  const addFiles = useCallback((incoming: File[]) => {
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      const fresh = incoming.filter((f) => !existing.has(f.name));
      return [...prev, ...fresh];
    });
  }, []);

  const removeFile = useCallback((name: string) => {
    setFiles((prev) => prev.filter((f) => f.name !== name));
  }, []);

  const clearFiles = useCallback(() => {
    setFiles([]);
    setResults([]);
    setDone(false);
    setSuccessCount(0);
    setErrorCount(0);
    setError(null);
  }, []);

  const handleExtract = useCallback(() => {
    if (files.length === 0) return;
    setProcessing(true);
    setDone(false);
    setError(null);
    setSuccessCount(0);
    setErrorCount(0);
    // Pre-populate results as "queued"
    setResults(
      files.map((f) => ({ filename: f.name, status: "queued" as const })),
    );

    abortRef.current = streamExtraction(files, {
      onQueue: (e: SSEQueueEvent) => {
        setResults(
          e.filenames.map((fn) => ({
            filename: fn,
            status: "queued" as const,
          })),
        );
      },
      onStart: (e) => {
        setResults((prev) =>
          prev.map((r) =>
            r.filename === e.filename
              ? { ...r, status: "processing", streamingText: "" }
              : r,
          ),
        );
      },
      onToken: (e: SSETokenEvent) => {
        setResults((prev) =>
          prev.map((r) =>
            r.filename === e.filename
              ? { ...r, streamingText: (r.streamingText ?? "") + e.token }
              : r,
          ),
        );
      },
      onSuccess: (e) => {
        setResults((prev) =>
          prev.map((r) =>
            r.filename === e.filename
              ? {
                  ...r,
                  status: "success",
                  data: e.data,
                  extra_fields: e.extra_fields,
                  streamingText: undefined,
                }
              : r,
          ),
        );
        setSuccessCount((c) => c + 1);
      },
      onError: (e) => {
        if (!e.filename) {
          // Global connection / 4xx / 5xx error
          setError(e.error);
          setResults((prev) =>
            prev.map((r) =>
              r.status === "queued" || r.status === "processing"
                ? {
                    ...r,
                    status: "error",
                    error: e.error,
                    streamingText: undefined,
                  }
                : r,
            ),
          );
          setErrorCount((c) => (c === 0 ? files.length : c));
          return;
        }
        setResults((prev) =>
          prev.map((r) =>
            r.filename === e.filename
              ? {
                  ...r,
                  status: "error",
                  error: e.error,
                  streamingText: undefined,
                }
              : r,
          ),
        );
        setErrorCount((c) => c + 1);
      },
      onDone: (e) => {
        setProcessing(false);
        setDone(true);
        if (e.success_count !== undefined) setSuccessCount(e.success_count);
        if (e.error_count !== undefined)
          setErrorCount((c) => Math.max(c, e.error_count));
      },
    });
  }, [files]);

  const handleCancel = useCallback(() => {
    abortRef.current?.abort();
    setProcessing(false);
    setDone(true);
  }, []);

  const handleDownload = useCallback(() => {
    window.location.href = "/api/download";
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-800">
              <FileSpreadsheet className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-slate-900">
                Utility Invoice Extractor
              </h1>
              <p className="text-xs text-slate-500">
                Multilingual Invoice Extraction
              </p>
            </div>
          </div>
          {health && (
            <div className="hidden items-center gap-2 text-xs text-slate-500 sm:flex">
              <span className="flex h-2 w-2 rounded-full bg-emerald-500" />
              {health.model ? "Connected" : "Disconnected"}
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">
        {/* Intro */}
        <div className="mb-8">
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
            Batch extract structured data from utility invoices
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Upload electricity, gas, or water invoices in any language. Watch
            the live LLM extraction stream in real-time. Once the batch is
            complete, export the whole batch to CSV or start a new batch.
          </p>
          <div className="mt-4 flex flex-wrap gap-4 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1.5">
              <Globe className="h-4 w-4 text-slate-400" />
              Multilingual support
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-slate-400" />
              Live LLM Token Streaming
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Loader2 className="h-4 w-4 text-slate-400" />
              Batch Extraction & CSV Export
            </span>
          </div>
        </div>

        {error && (
          <div className="mb-6 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 shadow-sm">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p className="font-semibold">Batch Processing Error</p>
              <p className="mt-0.5 text-xs text-rose-600">{error}</p>
            </div>
          </div>
        )}

        <Dropzone
          files={files}
          onFiles={addFiles}
          onRemove={removeFile}
          onClear={clearFiles}
          onExtract={handleExtract}
          processing={processing}
          done={done}
          onCancel={handleCancel}
        />

        <ResultsPanel
          results={results}
          done={done}
          successCount={successCount}
          errorCount={errorCount}
          onDownload={handleDownload}
          onNewBatch={clearFiles}
        />

        {/* Footer note */}
        <p className="mt-8 text-center text-xs text-slate-400">
          Supported formats: PDF (text-based), TXT · OCR is not supported
        </p>
      </main>
    </div>
  );
}

export default App;
