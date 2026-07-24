export type UtilityType = "electricity" | "gas" | "water";

export interface InvoiceField {
  vendor_name: string;
  invoice_date: string;
  service_address: string | null;
  utility_type: UtilityType;
  usage_amount: number;
  usage_unit: string;
  billing_period_start: string;
  billing_period_end: string;
  detected_language?: string;
  confidence_score?: number;
  [key: string]: any;
}

export type FileStatus = "queued" | "processing" | "success" | "error";

export interface FileResult {
  filename: string;
  status: FileStatus;
  data?: InvoiceField;
  extra_fields?: Record<string, any>;
  error?: string;
  streamingText?: string;
}

export interface SSEQueueEvent {
  filenames: string[];
  total: number;
}

export interface SSEStartEvent {
  filename: string;
  index: number;
  total: number;
}

export interface SSETokenEvent {
  filename: string;
  index: number;
  total: number;
  token: string;
}

export interface SSESuccessEvent {
  filename: string;
  index: number;
  total: number;
  data: InvoiceField;
  extra_fields?: Record<string, any>;
}

export interface SSEErrorEvent {
  filename: string;
  index: number;
  total: number;
  error: string;
}

export interface SSEDoneEvent {
  total: number;
  success_count: number;
  error_count: number;
}

export interface HealthResponse {
  status: string;
  model: string;
  base_url: string;
}
