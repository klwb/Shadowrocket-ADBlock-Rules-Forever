# PassWall 风格 Shadowrocket 规则：学习案例

## 目标

PassWall 可以直接读取 V2Ray/Xray 的 `geosite.dat`、`geoip.dat`，Shadowrocket
不能直接读取这两种二进制文件。因此这里不复制二进制文件，而是在每天发布时，
把相同体系里的公开数据源转换成 Shadowrocket 原生文本规则。

最终产物为 `sr_passwall_like.conf`，不包含广告拦截，以降低验证码、登录和风控
资源被误杀的概率。

## 数据源

| 用途 | 数据源 | 转换结果 |
|---|---|---|
| 中国域名 | `felixonmars/dnsmasq-china-list` 的 `accelerated-domains.china.conf` | `DOMAIN-SUFFIX,…,DIRECT` |
| Apple 中国 CDN | 同仓库的 `apple.china.conf` | `DOMAIN-SUFFIX,…,DIRECT` |
| 中国 IPv4 | `gaoyifan/china-operator-ip` 的 `china.txt` | `IP-CIDR,…,DIRECT,no-resolve` |
| 中国 IPv6 | 同仓库的 `china6.txt` | `IP-CIDR6,…,DIRECT,no-resolve` |
| 应代理域名 | 官方 GFWList 及个人代理列表 | `DOMAIN-SUFFIX,…,PROXY` 等 |

`Loyalsoldier/v2ray-rules-dat` 的 `geosite:cn` / `geoip:cn` 也整合了上述
felixonmars 和 gaoyifan 数据。本案例直接读取上游文本，是为了避免先解析
`dat` 二进制文件，同时让转换过程容易阅读和审计。

## 为什么规则顺序重要

Shadowrocket 从上向下匹配，先命中的规则生效。本配置的顺序是：

1. `manual_direct`：个人直连规则，模拟 PassWall 中最高优先级的“直连列表”；
2. `manual_proxy + gfwlist`：确定需要代理的域名；
3. 中国域名：国内服务及中国 CDN 直连；
4. 中国 IPv4/IPv6：域名规则没命中时按目标 IP 兜底；
5. `GEOIP,CN,DIRECT`：用 Shadowrocket 内置库再补一次；
6. `FINAL,PROXY`：未知目标代理。

最后一条是它与黑名单配置最重要的区别。验证码、登录和风控服务经常新增域名；
如果使用 `FINAL,DIRECT`，新域名可能在 GFWList 更新前直连失败。

## 转换脚本

脚本是 [`factory/passwall_like.py`](factory/passwall_like.py)，核心分为三步：

1. 下载源文件，并对网络错误自动重试；
2. 严格解析 dnsmasq 域名和 IPv4/IPv6 CIDR，遇到上游格式变化立即报错；
3. 去重、排序后写入 `factory/resultant/passwall_*.list`。

脚本还设置了合理的最小规则数量。如果上游返回错误页面、截断文件或突然改变
格式，构建会直接失败，不会把残缺规则发布到 `release` 分支。

单独运行和查看中间产物：

```bash
python3 -m pip install -r requirements.txt -r requirements-custom.txt
python3 factory/passwall_like.py
wc -l factory/resultant/passwall_*.list
python3 -m unittest factory.test_passwall_like
```

生成完整配置：

```bash
./factory/build_with_custom_rules.sh
```

`build_with_custom_rules.sh` 会临时合并 `factory/custom_*.txt` 中的个人规则，
构建结束后恢复上游文件。生成的 `sr_passwall_like.conf` 会保留个人 Tailscale
`skip-proxy` 和 RustDesk `bypass-tun` 设置。

## 添加个人直连规则

创建 `factory/custom_direct.txt`，每行填写一个裸域名或 IP/CIDR，例如：

```text
example.cn
192.0.2.10/32
```

不要写 `DOMAIN-SUFFIX`、`DIRECT` 等字段，构建脚本会自动转换。提交到 `build`
分支后，GitHub Actions 会重建并发布到 `release` 分支。

## IPv6 说明

配置保留了中国 IPv6 规则，但公共头部默认设置 `ipv6 = false`，避免用户在节点
或本地网络没有正确配置 IPv6 时发生泄漏或连接异常。确认节点支持 IPv6 后，
可以在 Shadowrocket 配置中自行开启。

## 排错方法

在 Shadowrocket 的“数据/日志”中查看失败请求：

- 命中 `DIRECT` 但打不开：把该域名加入 `custom_proxy.txt`；
- 命中 `PROXY` 仍打不开：检查节点地区、节点 IP 风控和 DNS；
- 命中 `REJECT`：说明使用了带广告过滤的其他配置，本配置本身没有拒绝规则；
- 完全看不到请求：检查浏览器安全 DNS、系统代理旁路或其他 VPN 是否抢占流量。
## 来源链修复（2026-10-20）

正式生成仅下载官方 GFWList，停止合并 `Johnshall/cn-blocked-domain` 的检测结果。
后者只由 `factory/audit_domain_conflicts.py` 下载供审计，不参与生成与发布。
个人代理规则仍高于中国列表，不改变富途、长桥等显式代理设置。
官方列表与中国列表之间仍可能存在有意或可疑重叠，不能批量交换优先级；审计后逐域处理。

复查上游冲突：

```bash
python3 factory/audit_domain_conflicts.py --output /tmp/shadowrocket-rule-audit.md
python3 -m unittest factory.test_passwall_like factory.test_gfwlist
```

如已通过正常下载流程准备好 `factory/resultant` 内的所有来源，可仅重建一份配置：

```bash
./factory/build_with_custom_rules.sh --from-local-sources --only sr_passwall_like
```

此命令不会刷新来源，日常更新仍使用上文完整构建命令。当前电脑启用的修复版
命名为 `sr_passwall_official.conf`，原配置保留供回退；自动发布产物仍叫 `sr_passwall_like.conf`。

`www.douyin.com` 可能出现在 GFW 代理列表，并先于中国域名直连列表命中。
本地维护 `douyin.com` 的最高优先级直连项，并从 GFW 列表排除
`www.douyin.com`。基础 manual 文件与 custom 文件均保留此修复，分别覆盖普通构建和自定义构建。

更新配置后，在 Shadowrocket「配置 → 测试规则」输入 `www.douyin.com`，
结果应为 `DIRECT`；同时确认 `v3-dy-o.zjcdn.com` 为 `DIRECT`。
已建立的视频连接可通过退出并重新打开抖音来重建。
