"""Audit upstream domain overlaps without changing generated or active rules.

Usage: python3 factory/audit_domain_conflicts.py --output /tmp/rule-audit.md
Uses curl's system certificate store; downloads domain text only, no IP lists.
"""
import argparse
import base64
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = {
    'gfwlist': 'https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt',
    'cn-blocked': 'https://raw.githubusercontent.com/Johnshall/cn-blocked-domain/release/domains.txt',
    'china': 'https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/accelerated-domains.china.conf',
    'apple': 'https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/apple.china.conf',
}


def domains(text):
    result = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(('!', '#', '@@', '[AutoProxy')):
            continue
        line = re.sub(r'^\|?https?://', '', line)
        line = re.sub(r'^\|\|', '', line).lstrip('.*').rstrip('/^*').split('/')[0]
        if re.fullmatch(r'[\w.-]+', line):
            result.add(line.lower())
    return result


def match(domain, rules):
    parts = domain.split('.')
    return next(('.'.join(parts[i:]) for i in range(len(parts))
                 if '.'.join(parts[i:]) in rules), None)


def local_rules(*names):
    return set().union(*(domains((ROOT / name).read_text())
                         for name in names if (ROOT / name).exists()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, help='Reuse downloaded source JSON')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.snapshot:
        source = json.loads(args.snapshot.read_text())
    else:
        source = {}
        for name, url in SOURCES.items():
            data = subprocess.check_output(['curl', '-fsSL', '--connect-timeout', '5',
                                            '--max-time', '30', url])
            source[name] = (base64.b64decode(data) if name == 'gfwlist' else data).decode()
    china = {line.split('/')[1].lstrip('.') for name in ('china', 'apple')
             for line in source[name].splitlines() if line.startswith('server=/')}
    direct = local_rules('manual_direct.txt', 'custom_direct.txt')
    proxy = local_rules('manual_proxy.txt', 'custom_proxy.txt', 'manual_gfwlist.txt', 'custom_gfwlist.txt')
    excludes = local_rules('manual_gfwlist_excludes.txt', 'custom_gfwlist_excludes.txt')
    rows = []
    for name in ('gfwlist', 'cn-blocked'):
        for domain in sorted(domains(source[name])):
            parent = match(domain, china)
            if not parent:
                continue
            state = ('已直连覆盖' if match(domain, direct) else
                     '个人指定代理' if match(domain, proxy) else
                     '已排除代理源' if domain in excludes else
                     '仅顶级域后缀重叠' if '.' not in parent else '待核验')
            rows.append((domain, parent, name, state))
    lines = ['# 上游域名规则冲突审计', '',
             '扫描代理域名及其父域的中国列表重叠。重叠不等于误判；海外服务、地区版本及个人代理项需要保留。',
             '此报告反映下载时的上游文本和本地生成源，不代表当前 Shadowrocket 的全部实际命中。', '',
             f'中国规则 {len(china)} 条；重叠来源记录 {len(rows)} 条；唯一代理域名 {len({r[0] for r in rows})} 个。', '',
             '| 代理域名 | 中国列表匹配 | 来源 | 状态 |', '|---|---|---|---|']
    lines += ['| ' + ' | '.join(row) + ' |' for row in rows]
    lines += ['', '## 上游来源', ''] + [f'- {name}: {url}' for name, url in SOURCES.items()]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text('\n'.join(lines) + '\n')
    from collections import Counter
    print(dict(Counter(row[3] for row in rows)))
    print(f'Wrote {args.output}')


if __name__ == '__main__':
    main()
