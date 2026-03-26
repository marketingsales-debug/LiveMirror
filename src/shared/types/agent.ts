export enum AgentRole {
  INDIVIDUAL = "individual",
  INFLUENCER = "influencer",
  MEDIA = "media",
  ORGANIZATION = "organization",
  GOVERNMENT = "government",
  EXPERT = "expert",
  BOT = "bot"
}

export enum Stance {
  SUPPORTIVE = "supportive",
  OPPOSING = "opposing",
  NEUTRAL = "neutral",
  OBSERVER = "observer"
}

export interface BehavioralFingerprint {
  avg_posts_per_day: number;
  avg_response_time_minutes: number;
  active_hours: number[];
  sentiment_distribution: Record<string, number>;
  preferred_platforms: string[];
  influence_radius: number;
  echo_chamber_score: number;
  persuadability: number;
  data_source: string;
  last_calibrated?: Date | string;
}

export interface AgentPersona {
  agent_id: number;
  name: string;
  role: AgentRole;
  entity_type: string;
  activity_level: number;
  stance: Stance;
  sentiment_bias: number;
  influence_weight: number;
  fingerprint: BehavioralFingerprint;
  belief_history: Record<string, any>[];
  trust_network: Record<number, number>;
  memory_summary: string;
  interaction_count: number;
}
