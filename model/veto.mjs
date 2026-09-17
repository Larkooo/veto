import './core.js';
import './model.js';

const runtime = globalThis.WebGuard;
export const defaults = runtime.defaults;
export const modelVersion = globalThis.WebGuardModel.version;
export function createClassifier(artifact = globalThis.WebGuardModel) {
  const model = runtime.loadModel(artifact);
  return Object.freeze({
    classify: state => runtime.classify(state, model),
    decide: (state, settings = {}) => runtime.decide(state, runtime.classify(state, model),
      { ...defaults, ...settings }, model.thresholds),
  });
}
export const { classify, decide } = createClassifier();
