export type Category = 'content' | 'ad' | 'cookie' | 'newsletter' | 'notification' | 'paywall';
export interface ElementState {
  text?: string;
  attributes?: string;
  resource?: string;
  tag?: string;
  role?: string;
  fixed?: boolean;
  dialog?: boolean;
  iframe?: boolean;
  image?: boolean;
  thirdParty?: boolean;
  width?: number;
  height?: number;
  links?: number;
  hasForm?: boolean;
  protected?: boolean;
  bannerShape?: boolean;
  visible?: boolean;
}
export interface Decision {
  category: { type: 'choice'; choice: Category; probabilities: Record<Category, number>; confidence: number };
  isAd: { type: 'binary'; probability: number };
  isAnnoyance: { type: 'binary'; probability: number };
  isPaywall: { type: 'binary'; probability: number };
}
export interface Settings {
  enabled: boolean;
  ads: boolean;
  network: boolean;
  annoyances: boolean;
  paywalls: boolean;
  disabledHosts: string[];
}
export interface ModelArtifact {
  version: string;
  featureVersion: string;
  dimensions: number;
  labels: Category[];
  weights: string;
  scales: number[];
  intercepts: number[];
  temperature: number;
  thresholds: Partial<Record<Category, number>>;
}
export interface Model extends ModelArtifact { coefficients: Int8Array }
export interface WebGuardAPI {
  LABELS: Category[];
  DIMENSIONS: number;
  FEATURE_VERSION: string;
  defaults: Readonly<Settings>;
  features(state: ElementState): [number, number][];
  loadModel(artifact: ModelArtifact): Model;
  classify(state: ElementState, model: Model): Decision;
  decide(state: ElementState, decision: Decision, settings: Settings, thresholds: ModelArtifact['thresholds']): { action: 'hide' | 'keep'; reason: string };
  baseline(state: ElementState): boolean;
}
declare global { var WebGuard: WebGuardAPI; }
