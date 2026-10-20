# -*- coding: utf-8 -*-

#
# 下载并解析最新版本的 GFWList
# 对于混合性质的网站，尽量走代理（忽略了所有的@@指令）
#
# 仅使用官方 GFWList。第三方检测名单仅供 audit_domain_conflicts.py 审计，
# 不参与正式分流，避免国内域名的历史/异常检测覆盖中国直连规则。
#


import time
import requests
import re
import base64
import argparse
from pathlib import Path


unhandle_rules = []

# ruleType for raw or base64
def get_rule(rules_url, ruleType='raw'):
    success = False
    try_times = 0
    r = None
    while try_times < 5 and not success:
        r = requests.get(rules_url)
        if r.status_code != 200:
            time.sleep(1)
            try_times = try_times + 1
        else:
            success = True
            break

    if not success:
        raise Exception('error in request %s\n\treturn code: %d' % (rules_url, r.status_code) )

    if ruleType == 'base64':
        rule = base64.b64decode(r.text) \
                .decode("utf-8") \
                .replace('\\n', '\n')
    else:
        rule = r.text

    return rule


def clear_format(rule):
    rules = []

    rule = rule.split('\n')
    for row in rule:
        row = row.strip()

        # 注释 直接跳过
        if row == '' or row.startswith('!') or row.startswith('@@') or row.startswith('[AutoProxy'):
            continue

        # 清除前缀
        row = re.sub(r'^\|?https?://', '', row)
        row = re.sub(r'^\|\|', '', row)
        row = row.lstrip('.*')

        # 清除后缀
        row = row.rstrip('/^*')

        rules.append(row)

    return rules


def filtrate_rules(rules, excludes=[]):
    ret = []

    for rule in rules:
        rule0 = rule

        # only hostname
        if '/' in rule:
            split_ret = rule.split('/')
            rule = split_ret[0]

        if not re.match(r'^[\w.-]+$', rule):
            unhandle_rules.append(rule0)
            continue

        if rule in excludes:
            continue

        ret.append(rule)

    ret = list( set(ret) )
    ret.sort()

    return ret

def getURLs(url):
    r = requests.get(url)
    return r.text.split("\n")[:-1]

OFFICIAL_URL = 'https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt'


def main():
    parser = argparse.ArgumentParser(description='Generate proxy domains from official GFWList only')
    parser.add_argument('--source-file', type=Path, help='Saved official base64 GFWList for reproducible builds')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    rule = (base64.b64decode(args.source_file.read_bytes()).decode('utf-8')
            if args.source_file else get_rule(OFFICIAL_URL, ruleType='base64'))
    excludes = [line.strip() for line in (root / 'manual_gfwlist_excludes.txt').read_text().splitlines()
                if line.strip() and not line.lstrip().startswith('#')]
    rules = sorted(set(filtrate_rules(clear_format(rule), excludes)))
    if len(rules) < 1000:
        raise RuntimeError('Refusing to publish an incomplete official GFWList')
    output = root / 'resultant'
    output.mkdir(exist_ok=True)
    (output / 'gfw.list').write_text('\n'.join(rules) + '\n')
    (output / 'gfw_unhandle.log').write_text('\n'.join(unhandle_rules))
    print(f'Official GFWList: {len(rules)} domains; third-party detected domains excluded')


if __name__ == '__main__':
    main()
