"""Train a tiny multinomial classifier; export int8 weights for plain JavaScript.

Validation selects regularization, temperature, and action thresholds. Test families
are evaluated once at the end. All reported bootstrap metrics are synthetic.
"""
import argparse
import base64
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, log_loss

ROOT = Path(__file__).resolve().parents[1]
LABELS = ['content', 'ad', 'cookie', 'newsletter', 'notification', 'paywall']
DIMENSIONS = 4096


def softmax(logits):
    exp = np.exp(logits - logits.max(axis=1, keepdims=True))
    return exp / exp.sum(axis=1, keepdims=True)


def metrics(y, probabilities):
    predictions = probabilities.argmax(axis=1)
    confidence = probabilities.max(axis=1)
    correct = predictions == y
    ece = 0.0
    for low in np.arange(0, 1, 0.1):
        mask = (confidence >= low) & (confidence < low + 0.1 + (1e-9 if low > 0.89 else 0))
        if mask.any():
            ece += mask.mean() * abs(correct[mask].mean() - confidence[mask].mean())
    return {'accuracy': float(correct.mean()), 'log_loss': float(log_loss(y, probabilities, labels=list(range(len(LABELS))))),
            'brier_multiclass': float(np.square(probabilities - np.eye(len(LABELS))[y]).sum(axis=1).mean()),
            'ece_10_bins': float(ece),
            'confusion_matrix': confusion_matrix(y, predictions, labels=list(range(len(LABELS)))).tolist(),
            'per_class': classification_report(y, predictions, labels=list(range(len(LABELS))), target_names=LABELS, output_dict=True, zero_division=0)}


def wilson(successes, total):
    if not total:
        return None
    z = 1.96
    p = successes / total
    center = (p + z*z/(2*total))/(1+z*z/total)
    margin = z*np.sqrt(p*(1-p)/total + z*z/(4*total*total))/(1+z*z/total)
    return [float(center-margin), float(center+margin)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=ROOT / 'data/bootstrap.jsonl')
    parser.add_argument('--real-data', type=Path, default=ROOT / 'data/reviewed-development.jsonl')
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.data.read_text().splitlines() if line.strip()]
    if args.real_data.exists():
        rows.extend(json.loads(line) for line in args.real_data.read_text().splitlines() if line.strip())
    groups = {}
    seen = {}
    for row in rows:
        assert row['label'] in LABELS and row['split'] in ['train', 'validation', 'test']
        assert groups.setdefault(row['group'], row['split']) == row['split'], 'Group leaked across splits'
        fingerprint = json.dumps(row['state'], sort_keys=True)
        assert seen.setdefault(fingerprint, row['split']) == row['split'], 'Identical state leaked across splits'
    vectors = json.loads(subprocess.check_output(['node', str(ROOT / 'tools/vectorize.mjs')], input=json.dumps(rows).encode()))
    rr, cc, vv = [], [], []
    for i, vector in enumerate(vectors):
        for index, value in vector:
            rr.append(i); cc.append(index); vv.append(value)
    X = csr_matrix((vv, (rr, cc)), shape=(len(rows), DIMENSIONS), dtype=np.float64)
    y = np.array([LABELS.index(row['label']) for row in rows])
    sample_weights = np.array([1.0 if r['source'] == 'authored-bootstrap-v1' else 4.0 for r in rows])
    masks = {split: np.array([r['split'] == split for r in rows]) for split in ['train', 'validation', 'test']}
    for split, mask in masks.items():
        assert set(y[mask]) == set(range(len(LABELS))), f'Missing labels in {split}'
    started = time.perf_counter()
    candidates = []
    for C in [0.5, 2.0, 8.0]:
        model = LogisticRegression(C=C, max_iter=1200, solver='lbfgs', random_state=817)
        model.fit(X[masks['train']], y[masks['train']], sample_weight=sample_weights[masks['train']])
        loss = log_loss(y[masks['validation']], model.predict_proba(X[masks['validation']]), sample_weight=sample_weights[masks['validation']])
        candidates.append((float(loss), C, model))
    loss, chosen_C, model = min(candidates, key=lambda x: x[0])
    scales = np.maximum(np.abs(model.coef_).max(axis=1) / 127, 1e-12)
    quantized = np.clip(np.rint(model.coef_ / scales[:, None]), -127, 127).astype(np.int8)
    coefficients = quantized.astype(np.float64) * scales[:, None]
    logits = X @ coefficients.T + model.intercept_
    temperatures = np.exp(np.linspace(np.log(0.5), np.log(3), 81))
    temperature = min(temperatures, key=lambda t: log_loss(y[masks['validation']], softmax(logits[masks['validation']] / t), sample_weight=sample_weights[masks['validation']]))
    probabilities = softmax(logits / temperature)
    validation = probabilities[masks['validation']]
    thresholds = {}
    threshold_support = {}
    for index, label in enumerate(LABELS[1:], 1):
        # Conservative minimum. If no threshold qualifies, that action stays off.
        threshold = 1.01
        support = 0
        for candidate in [0.97, 0.98, 0.99, 0.995]:
            selected = (validation.argmax(axis=1) == index) & (validation[:, index] >= candidate)
            if selected.sum() >= 8 and (y[masks['validation']][selected] == index).all():
                threshold, support = candidate, int(selected.sum())
                break
        thresholds[label] = threshold
        threshold_support[label] = support
    artifact = {'version': '0.3.0', 'featureVersion': 'dom-bow-2', 'dimensions': DIMENSIONS,
                'labels': LABELS, 'weights': base64.b64encode(quantized.tobytes()).decode(),
                'scales': scales.tolist(), 'intercepts': model.intercept_.tolist(),
                'temperature': float(temperature), 'thresholds': thresholds,
                'trainingDataSHA256': hashlib.sha256(args.data.read_bytes()).hexdigest(),
                'trainingSource': 'authored-bootstrap-v1 plus reviewed development DOM captures',
                'reviewedDataSHA256': hashlib.sha256(args.real_data.read_bytes()).hexdigest() if args.real_data.exists() else None,
                'confidenceStatus': 'validation-temperature-scaled; field calibration unvalidated'}
    (ROOT / 'extension/model.json').write_text(json.dumps(artifact, separators=(',', ':')) + '\n')
    (ROOT / 'extension/model.js').write_text('globalThis.WebGuardModel = ' + json.dumps(artifact, separators=(',', ':')) + ';\n')
    test = masks['test']
    ad_selected = (probabilities[test].argmax(axis=1) == 1) & (probabilities[test, 1] >= thresholds['ad'])
    ad_truth = y[test] == 1
    tp = int((ad_selected & ad_truth).sum()); fp = int((ad_selected & ~ad_truth).sum())
    # Shared runtime policy is exercised in the browser tests, including structural guards.
    report = {'scope': 'Bootstrap test was observed during v1 development; this regression score is not an independent real-web accuracy estimate.',
              'sources': {'bootstrap': sum(r['source'] == 'authored-bootstrap-v1' for r in rows), 'reviewed_real_dom': sum(r['source'] != 'authored-bootstrap-v1' for r in rows)},
              'labels': LABELS, 'samples': {s: int(m.sum()) for s, m in masks.items()},
              'groups': {s: len({r['group'] for r in rows if r['split'] == s}) for s in masks},
              'data_sha256': artifact['trainingDataSHA256'], 'training_seconds': time.perf_counter()-started,
              'selected_C': chosen_C, 'validation_regularization': [{'C': c, 'log_loss': l} for l, c, _ in candidates],
              'temperature': float(temperature), 'thresholds': thresholds, 'threshold_validation_support': threshold_support,
              'model_bytes': (ROOT / 'extension/model.js').stat().st_size, 'parameters': int(quantized.size + len(LABELS)),
              'validation': metrics(y[masks['validation']], probabilities[masks['validation']]),
              'test': metrics(y[test], probabilities[test]),
              'test_ad_gate': {'true_positives': tp, 'false_positives': fp, 'actual_ads': int(ad_truth.sum()),
                              'precision': tp/(tp+fp) if tp+fp else None, 'recall': tp/int(ad_truth.sum()),
                              'precision_wilson_95': wilson(tp, tp+fp),
                              'interval_caveat': 'Sample-level interval; variants are correlated within families.'},
              'quantization_max_probability_delta': float(np.max(abs(softmax((X @ model.coef_.T + model.intercept_)/temperature) - probabilities))),
              'hardware': platform.platform(),
              'limitations': ['Synthetic labels and correlated variants', 'English-heavy seed vocabulary',
                              'Closed shadow roots and image/video-only ads are not semantically understood',
                              'Confidence on new websites is unvalidated', 'No claim of undetectability or superiority to maintained filter lists']}
    (ROOT / 'reports/training.json').write_text(json.dumps(report, indent=2) + '\n')
    predictions = [{'id': row['id'], 'label': row['label'], 'probabilities': dict(zip(LABELS, p.tolist()))}
                   for row, p in zip(rows, probabilities) if row['split'] == 'test']
    (ROOT / 'reports/test-predictions.json').write_text(json.dumps(predictions, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['samples', 'groups', 'training_seconds', 'model_bytes', 'thresholds', 'test_ad_gate']}, indent=2))
    print('Test accuracy:', report['test']['accuracy'])


if __name__ == '__main__':
    main()
