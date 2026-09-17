import type { ElementState, Decision, Settings, ModelArtifact } from './types.js';
export type { ElementState, Decision, Settings, ModelArtifact } from './types.js';
export const defaults: Readonly<Settings>;
export const modelVersion: string;
export interface Classifier {
  classify(state: ElementState): Decision;
  decide(state: ElementState, settings?: Partial<Settings>): { action: 'hide' | 'keep'; reason: string };
}
export function createClassifier(artifact?: ModelArtifact): Readonly<Classifier>;
export const classify: Classifier['classify'];
export const decide: Classifier['decide'];
