import fs from 'node:fs';
import '../extension/core.js';
const rows = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(rows.map(row => WebGuard.features(row.state))));
