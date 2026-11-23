export interface CatalogOption { id: string; label: string; hint: string; min: number | null; max: number | null }
export interface CatalogItem {
  id: string; label: string; group: string; fundamental: string; question: string; measure: string; unit: string
  options: CatalogOption[]; bounds: number[]; base_uncertainty: number
  needs_video: boolean; needs_view: 'frontal' | 'side' | null; needs_3d: boolean
  conf_cap: number; experimental: boolean; limitations: string[]
}
export interface Catalog {
  framework: string; items: CatalogItem[]
  limits: { max_video_mb: number; max_image_mb: number; max_images: number; analysis_fps: number; max_analysis_seconds: number }
  video_extensions: string[]; image_extensions: string[]
}
export type Verdict = 'agree' | 'disagree' | 'inconclusive'
export interface Evidence { frame: number; caption: string; image?: string; t?: number; source?: string; pose_conf?: number }
export interface ItemResult {
  item_id: string; label: string; group: string; fundamental: string; experimental: boolean
  assessed: { rating: string; label: string; notes?: string | null }
  measured: null | { value: number | null; category: string; category_label: string; uncertainty: number | null; n_frames: number; n_turns: number | null }
  verdict: Verdict; reason: string; confidence: number; confidence_label: string
  method: string; unit: string
  thresholds: { bounds: number[]; options: string[]; labels: string[] }
  notes: string[]; limitations: string[]; evidence: Evidence[]
}
export interface Turn { start: number; end: number; peak: number; t_start: number; t_end: number; peak_deg: number; direction: string; direction_frame: string; complete: boolean; duration: number }
export interface Result {
  assessment: { run_label: string; skier?: string | null; assessed_by?: string | null; terrain?: string | null; camera_view: string; general_notes?: string | null }
  media: { kind: 'video' | 'images'; files: string[]; source_fps?: number; analysis_fps?: number; width?: number; height?: number; duration_s?: number }
  pose: { estimator: string; frames: number; frames_detected: number; frames_confident: number; mean_confidence: number; has_3d: boolean }
  view: { view: string; source: string; facing: string | null }
  turns: Turn[]
  results: ItemResult[]
  summary: { agree: number; disagree: number; inconclusive: number; total: number; decided: number; agreement_rate: number | null }
  series: Record<string, (number | null)[]>
  gallery: { frame: number; image: string; source: string; pose_conf: number; detected: boolean }[]
  annotated_video: string | null
  warnings: string[]
  processing_seconds: number
}
export interface RunBrief {
  id: string; status: 'pending' | 'processing' | 'completed' | 'failed'; run_label: string; media_kind: string
  media_files: string[]; created_at: string; finished_at: string | null
  summary: Result['summary'] | null; error: string | null; items_assessed: number
}
export interface RunDetail extends RunBrief { progress: { fraction: number; message: string } | null; result?: Result }
