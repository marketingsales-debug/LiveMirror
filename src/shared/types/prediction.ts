export enum PredictionStatus {
  DRAFT = "draft",
  ACTIVE = "active",
  VALIDATED_CORRECT = "validated_correct",
  VALIDATED_WRONG = "validated_wrong",
  PARTIALLY_CORRECT = "partially_correct",
  EXPIRED = "expired"
}

export enum ConfidenceLevel {
  VERY_LOW = "very_low",
  LOW = "low",
  MODERATE = "moderate",
  HIGH = "high",
  VERY_HIGH = "very_high"
}

export enum NarrativeStage {
  SEED = "seed",
  EARLY_SPREAD = "early_spread",
  COUNTER_NARRATIVE = "counter_narrative",
  MAINSTREAM = "mainstream",
  PEAK = "peak",
  FATIGUE = "fatigue",
  RESOLUTION = "resolution"
}

export interface Prediction {
  prediction_id: string;
  topic: string;
  prediction_text: string;
  confidence: number;
  predicted_at: Date | string;
  predicted_timeframe_hours: number;
  source_signals_count: number;
  source_platforms: string[];
  simulation_rounds: number;
  bull_score: number;
  bear_score: number;
  debate_consensus: number;
  status: PredictionStatus;
  actual_outcome?: string;
  validated_at?: Date | string;
  accuracy_score?: number;
  narrative_stage: NarrativeStage;
}

export interface PredictionReport {
  report_id: string;
  topic: string;
  generated_at: Date | string;
  predictions: Prediction[];
  executive_summary: string;
  sources_cited: Record<string, string>[];
  narrative_analysis: string;
  risk_assessment: string;
  confidence_calibration_note: string;
}
