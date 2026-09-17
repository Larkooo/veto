"""Generate the original small request ruleset and shared ad-host evidence."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def build():
    hosts = json.loads((ROOT / 'rules/hosts.json').read_text())
    rules = []
    for group, domains in hosts.items():
        for domain in domains:
            condition = {'urlFilter': f'||{domain}^'}
            if group == 'tracking':
                condition['excludedResourceTypes'] = ['main_frame']
            rules.append({'id': len(rules)+1, 'priority': 1, 'action': {'type': 'block'}, 'condition': condition})
    # Match ad resource paths, never article/page navigation containing these words.
    for pattern, types in [
        (r'^https?://[^/]+/(.*/)?ads?/', ['script', 'image', 'sub_frame', 'object', 'media']),
        (r'^https?://[^/]+/[^?]*[/_](advertising|advertisement|ads)[_-]banner[^/?]*\.(gif|png|jpg|jpeg|webp|swf)(\?|$)', ['image', 'object', 'xmlhttprequest']),
    ]:
        rules.append({'id': len(rules)+1, 'priority': 1, 'action': {'type': 'block'},
                      'condition': {'regexFilter': pattern, 'resourceTypes': types}})
    (ROOT / 'extension/network-rules.json').write_text(json.dumps(rules, indent=2)+'\n')
    (ROOT / 'extension/ad-hosts.js').write_text('globalThis.VetoAdHosts = Object.freeze('+json.dumps(hosts['ads'])+');\n')


if __name__ == '__main__':
    build()
