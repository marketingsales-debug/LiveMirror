export enum Platform {
  REDDIT = "reddit",
  TWITTER = "twitter",
  BLUESKY = "bluesky",
  YOUTUBE = "youtube",
  TIKTOK = "tiktok",
  INSTAGRAM = "instagram",
  HACKERNEWS = "hackernews",
  POLYMARKET = "polymarket",
  WEB = "web",
  NEWS = "news"
}

export enum SignalType {
  SOCIAL_POST = "social_post",
  COMMENT = "comment",
  REACTION = "reaction",
  SHARE = "share",
  PREDICTION_MARKET = "prediction_market",
  NEWS_ARTICLE = "news_article",
  ECONOMIC = "economic",
  GOVERNMENT = "government",
  SENSOR = "sensor"
}

export interface RawSignal {
  platform: Platform;
  signal_type: SignalType;
  content: string;
  author?: string;
  url?: string;
  timestamp?: Date | string;
  engagement: Record<string, number>;
  metadata: Record<string, any>;
  raw_data?: Record<string, any>;
}

export interface ScoredSignal {
  signal: RawSignal;
  relevance_score: number;
  engagement_velocity: number;
  recency_score: number;
  cross_platform_score: number;
  composite_score: number;
}
