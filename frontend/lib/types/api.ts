export type ChangeType =
  | "UNCHANGED"
  | "ADDITION"
  | "DELETION"
  | "MODIFICATION"
  | "NUMERICAL_CHANGE"
  | "TEMPORAL_CHANGE"
  | "ENTITY_CHANGE"
  | "CONTRADICTION"
  | "REFINEMENT";

export interface DocumentMeta {
  filename: string;
  pages: number;
  file_type: string | null;
  document_id: string | null;
}

export interface ComparisonSummary {
  total_changes: number;
  additions: number;
  deletions: number;
  modifications: number;
  numerical_changes: number;
  temporal_changes: number;
  entity_changes: number;
  contradictions: number;
  refinements: number;
  unchanged: number;
}

export interface ChangeRecord {
  id: string;
  type: ChangeType;
  old_text: string | null;
  new_text: string | null;
  old_page: number | null;
  new_page: number | null;
  old_sentence_id: string | null;
  new_sentence_id: string | null;
  old_section: string | null;
  new_section: string | null;
  similarity: number | null;
  confidence: number;
  explanation: string;
  details: Record<string, unknown>;
}

export interface ComparisonResult {
  comparison_id: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | string;
  created_at: string;
  old_document: DocumentMeta;
  new_document: DocumentMeta;
  summary: ComparisonSummary;
  changes: ChangeRecord[];
}

export interface ComparisonHistoryItem {
  comparison_id: string;
  status: ComparisonResult["status"];
  created_at: string;
  old_document: DocumentMeta;
  new_document: DocumentMeta;
  summary: ComparisonSummary;
}

export interface ComparisonHistoryResponse {
  items: ComparisonHistoryItem[];
  limit: number;
  offset: number;
}

export interface ParsedDocument {
  document_id: string;
  filename: string;
  file_type: string;
  pages: number;
  paragraph_count: number;
  sentence_count: number;
  sections: Array<{ id: string; title: string; paragraph_ids: string[] }>;
  paragraphs: Array<{
    id: string;
    text: string;
    section_id: string | null;
    section_title: string | null;
    page_number: number | null;
    sentence_ids: string[];
  }>;
  sentences: Array<{
    id: string;
    text: string;
    section_id: string | null;
    section_title: string | null;
    paragraph_id: string | null;
    page_number: number | null;
    start_char: number | null;
    end_char: number | null;
  }>;
}

export interface ApiError {
  error: string;
  message: string;
}
