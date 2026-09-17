import { classify, decide, modelVersion } from './veto.mjs';

const state = {
  tag: 'div', text: 'Advertisement · Shop the latest collection',
  attributes: 'advertisement banner', width: 300, height: 250, visible: true,
};
console.log(JSON.stringify({ modelVersion, prediction: classify(state), action: decide(state) }, null, 2));
