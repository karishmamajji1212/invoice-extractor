import type {
  SSEDoneEvent,
  SSEErrorEvent,
  SSEQueueEvent,
  SSEStartEvent,
  SSESuccessEvent,
  SSETokenEvent,
} from "@/types";

interface SSEHandlers {
  onQueue: (e: SSEQueueEvent) => void;
  onStart: (e: SSEStartEvent) => void;
  onToken: (e: SSETokenEvent) => void;
  onSuccess: (e: SSESuccessEvent) => void;
  onError: (e: SSEErrorEvent) => void;
  onDone: (e: SSEDoneEvent) => void;
}

/**
 * Posts files to the /extract endpoint and processes the SSE stream.
 * Returns an AbortController so the caller can cancel an in-flight run.
 */
export function streamExtraction(
  files: File[],
  handlers: SSEHandlers,
): AbortController {
  const controller = new AbortController();

  const formData = new FormData();
  for (const f of files) formData.append("files", f);

  fetch("/api/extract", {
    method: "POST",
    body: formData,
    signal: controller.signal,
  })
    .then(async (resp) => {
      if (!resp.ok || !resp.body) {
        let errorMsg = `Server error (${resp.status})`;
        try {
          const json = await resp.json();
          if (json.detail) {
            errorMsg = typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail);
          }
        } catch {
          const text = await resp.text().catch(() => "");
          if (text) errorMsg = text;
        }
        throw new Error(errorMsg);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE frames are separated by a blank line.
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          if (!frame.trim()) continue;
          const lines = frame.split("\n");
          let event = "message";
          const dataLines: string[] = [];
          for (const line of lines) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
            // heartbeat comment lines (": heartbeat") are ignored
          }
          if (event === "heartbeat" || event === "message") continue;
          if (dataLines.length === 0) continue;

          const payload = JSON.parse(dataLines.join("\n"));
          switch (event) {
            case "queue":
              handlers.onQueue(payload as SSEQueueEvent);
              break;
            case "start":
              handlers.onStart(payload as SSEStartEvent);
              break;
            case "token":
              handlers.onToken(payload as SSETokenEvent);
              break;
            case "success":
              handlers.onSuccess(payload as SSESuccessEvent);
              break;
            case "error":
              handlers.onError(payload as SSEErrorEvent);
              break;
            case "done":
              handlers.onDone(payload as SSEDoneEvent);
              break;
          }
        }
      }
    })
    .catch((err) => {
      if (err.name === "AbortError") return;
      handlers.onError({
        filename: "",
        index: 0,
        total: 0,
        error: err.message || "Connection failed",
      });
      handlers.onDone({ total: 0, success_count: 0, error_count: 1 });
    });

  return controller;
}
