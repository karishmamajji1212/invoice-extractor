import {
  FileSpreadsheet,
  Upload,
  X,
  FileText,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Download,
  Zap,
  Droplet,
  Flame,
  RotateCcw,
  Globe,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
} from "lucide-react";
import type { FileResult, InvoiceField } from "@/types";

interface ResultRowProps {
  result: FileResult;
}

function UtilityIcon({ type }: { type?: InvoiceField["utility_type"] }) {
  if (type === "electricity") return <Zap className="h-4 w-4 text-amber-500" />;
  if (type === "gas") return <Flame className="h-4 w-4 text-orange-500" />;
  if (type === "water") return <Droplet className="h-4 w-4 text-sky-500" />;
  return <FileText className="h-4 w-4 text-slate-400" />;
}

function StatusBadge({ status }: { status: FileResult["status"] }) {
  if (status === "processing")
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Streaming & Processing
      </span>
    );
  if (status === "success")
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
        <CheckCircle2 className="h-3.5 w-3.5" />
        Extracted
      </span>
    );
  if (status === "error")
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700">
        <AlertCircle className="h-3.5 w-3.5" />
        Error
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-500">
      Queued
    </span>
  );
}

function ConfidenceBadge({ score }: { score?: number }) {
  if (score === undefined || score === null) return null;

  // Convert decimal (e.g. 0.95) to percentage integer (95%)
  const percentage = score <= 1.0 ? Math.round(score * 100) : Math.round(score);

  if (percentage >= 85) {
    return (
      <span
        title={`Extraction confidence score: ${percentage}%`}
        className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 shadow-2xs"
      >
        <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
        {percentage}% Confidence
      </span>
    );
  }
  if (percentage >= 70) {
    return (
      <span
        title={`Extraction confidence score: ${percentage}%`}
        className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700 shadow-2xs"
      >
        <Sparkles className="h-3.5 w-3.5 text-amber-600" />
        {percentage}% Medium
      </span>
    );
  }
  return (
    <span
      title={`Extraction confidence score: ${percentage}%`}
      className="inline-flex items-center gap-1 rounded-full border border-rose-200 bg-rose-50 px-2.5 py-0.5 text-xs font-semibold text-rose-700 shadow-2xs"
    >
      <ShieldAlert className="h-3.5 w-3.5 text-rose-600" />
      {percentage}% Low
    </span>
  );
}

function LanguageBadge({ lang }: { lang?: string }) {
  if (!lang) return null;
  return (
    <span
      title={`Detected document language: ${lang}`}
      className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700"
    >
      <Globe className="h-3 w-3 text-slate-500" />
      {lang}
    </span>
  );
}

function snakeToTitle(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

function formatFieldValue(val: any): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "boolean") return val ? "Yes" : "No";
  if (typeof val === "number") {
    // If it's a decimal confidence score key, render as percentage
    return val.toLocaleString();
  }
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

export function ResultRow({ result }: ResultRowProps) {
  // Collect all key-value entries to display dynamically
  const allDisplayEntries: Array<{ label: string; value: string }> = [];

  if (result.data) {
    Object.entries(result.data).forEach(([key, val]) => {
      // Exclude values displayed in special badges from grid duplicate
      if (key === "detected_language" || key === "confidence_score") return;
      allDisplayEntries.push({
        label: snakeToTitle(key),
        value: formatFieldValue(val),
      });
    });
  }

  if (result.extra_fields) {
    Object.entries(result.extra_fields).forEach(([key, val]) => {
      if (key === "detected_language" || key === "confidence_score") return;
      if (!result.data || !(key in result.data)) {
        allDisplayEntries.push({
          label: snakeToTitle(key),
          value: formatFieldValue(val),
        });
      }
    });
  }

  const language =
    result.data?.detected_language || result.extra_fields?.detected_language;
  const confidence =
    result.data?.confidence_score ?? result.extra_fields?.confidence_score;

  return (
    <div className="border-b border-slate-100 px-6 py-4 last:border-b-0">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-50">
            <FileText className="h-4.5 w-4.5 text-slate-400" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="truncate text-sm font-medium text-slate-800">
                {result.filename}
              </p>
              {language && <LanguageBadge lang={language} />}
              {confidence !== undefined && (
                <ConfidenceBadge score={confidence} />
              )}
            </div>
            {result.data && (
              <p className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-500">
                <UtilityIcon type={result.data.utility_type} />
                <span className="font-medium text-slate-700">
                  {result.data.vendor_name || "Invoice Data"}
                </span>
              </p>
            )}
          </div>
        </div>
        <StatusBadge status={result.status} />
      </div>

      {/* Streaming LLM text response box */}
      {result.status === "processing" && (
        <div className="mt-3 overflow-hidden rounded-lg bg-slate-900 p-3 text-xs text-slate-200 shadow-inner">
          <div className="mb-1.5 flex items-center justify-between border-b border-slate-800 pb-1.5 text-[10px] uppercase font-semibold text-slate-400">
            <span className="flex items-center gap-1.5">
              <Sparkles className="h-3 w-3 text-emerald-400" />
              LLM Real-time Output Stream
            </span>
            <span className="flex items-center gap-1 text-emerald-400 font-mono">
              <span className="h-1.5 w-1.5 animate-ping rounded-full bg-emerald-400" />
              Live Stream
            </span>
          </div>
          <pre className="whitespace-pre-wrap font-mono leading-relaxed text-emerald-300">
            {result.streamingText || "Connecting to model stream..."}
            <span className="inline-block animate-pulse font-bold text-white">
              ▌
            </span>
          </pre>
        </div>
      )}

      {/* Dynamic extracted fields display */}
      {result.status === "success" && (
        <div className="mt-3">
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 rounded-lg bg-slate-50 px-4 py-3.5 text-sm sm:grid-cols-3 lg:grid-cols-4 border border-slate-100">
            {allDisplayEntries.map((item, idx) => (
              <Field key={idx} label={item.label} value={item.value} />
            ))}
            {language && <Field label="Detected Language" value={language} />}
            {confidence !== undefined && (
              <Field
                label="Confidence Score"
                value={`${
                  confidence <= 1
                    ? Math.round(confidence * 100)
                    : Math.round(confidence)
                }%`}
              />
            )}
          </div>
        </div>
      )}

      {result.status === "error" && result.error && (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{result.error}</span>
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">
        {label}
      </dt>
      <dd className="mt-0.5 font-medium text-slate-700 break-words">{value}</dd>
    </div>
  );
}

interface ResultsPanelProps {
  results: FileResult[];
  done: boolean;
  successCount: number;
  errorCount: number;
  onDownload: () => void;
  onNewBatch?: () => void;
}

export function ResultsPanel({
  results,
  done,
  successCount,
  errorCount,
  onDownload,
  onNewBatch,
}: ResultsPanelProps) {
  if (results.length === 0) return null;

  return (
    <div className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 bg-slate-50/50 px-6 py-4">
        <div className="flex items-center gap-3">
          <FileSpreadsheet className="h-5 w-5 text-slate-600" />
          <div>
            <h2 className="text-sm font-semibold text-slate-800">
              Batch Extraction Results
            </h2>
            <p className="text-xs text-slate-500">
              {successCount} extracted · {errorCount} failed
              {!done && " · processing batch…"}
            </p>
          </div>
        </div>

        {done && (
          <div className="flex items-center gap-3">
            {successCount > 0 && (
              <button
                onClick={onDownload}
                className="inline-flex items-center gap-2 rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-900 shadow-sm"
              >
                <Download className="h-4 w-4" />
                Export Batch to CSV
              </button>
            )}
            {onNewBatch && (
              <button
                onClick={onNewBatch}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 shadow-sm"
              >
                <RotateCcw className="h-4 w-4" />
                New Batch Run
              </button>
            )}
          </div>
        )}
      </div>
      <div>
        {results.map((r) => (
          <ResultRow key={r.filename} result={r} />
        ))}
      </div>
    </div>
  );
}

interface DropzoneProps {
  files: File[];
  onFiles: (files: File[]) => void;
  onRemove: (name: string) => void;
  onClear: () => void;
  onExtract: () => void;
  processing: boolean;
  done?: boolean;
  onCancel: () => void;
}

export function Dropzone({
  files,
  onFiles,
  onRemove,
  onClear,
  onExtract,
  processing,
  done,
  onCancel,
}: DropzoneProps) {
  if (done) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
        <div className="flex flex-col items-center justify-center py-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 mb-3">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <h3 className="text-base font-semibold text-slate-800">
            Batch Run Completed
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Export the batch results to CSV or click "New Batch Run" to start
            processing a new set of invoices.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <label
        htmlFor="file-input"
        className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-slate-50/50 px-6 py-10 text-center transition-colors hover:border-slate-300 hover:bg-slate-50"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const dropped = Array.from(e.dataTransfer.files);
          if (dropped.length) onFiles(dropped);
        }}
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100">
          <Upload className="h-6 w-6 text-slate-400" />
        </div>
        <p className="mt-3 text-sm font-medium text-slate-700">
          Drop invoice PDFs or TXT files here
        </p>
        <p className="mt-1 text-xs text-slate-400">
          or click to browse — upload full batch for processing
        </p>
        <input
          id="file-input"
          type="file"
          multiple
          accept=".pdf,.txt"
          className="hidden"
          disabled={processing}
          onChange={(e) => {
            const selected = Array.from(e.target.files ?? []);
            if (selected.length) onFiles(selected);
            e.target.value = "";
          }}
        />
      </label>

      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          {files.map((f) => (
            <div
              key={f.name}
              className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-3 py-2"
            >
              <div className="flex min-w-0 items-center gap-2">
                <FileText className="h-4 w-4 shrink-0 text-slate-400" />
                <span className="truncate text-sm text-slate-700">
                  {f.name}
                </span>
                <span className="shrink-0 text-xs text-slate-400">
                  {(f.size / 1024).toFixed(0)} KB
                </span>
              </div>
              <button
                onClick={() => onRemove(f.name)}
                disabled={processing}
                className="rounded p-1 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-600 disabled:opacity-40"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="mt-5 flex items-center justify-between gap-3">
        {files.length > 0 && !processing && (
          <button
            onClick={onClear}
            className="text-sm font-medium text-slate-500 transition-colors hover:text-slate-700"
          >
            Clear all
          </button>
        )}
        <div className="ml-auto flex gap-3">
          {processing && (
            <button
              onClick={onCancel}
              className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50"
            >
              Cancel
            </button>
          )}
          <button
            onClick={onExtract}
            disabled={files.length === 0 || processing}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-800 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {processing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Processing Batch…
              </>
            ) : (
              <>
                <FileSpreadsheet className="h-4 w-4" />
                Extract Batch Data
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
