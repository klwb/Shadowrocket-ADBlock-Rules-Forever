# 自定义规则维护指引（klwb fork）

这个 fork 会自动完成下面的流程：

1. 合并 `Johnshall/build` 的最新源码；
2. 在构建时临时叠加 `factory/custom_*.txt` 中的个人规则；
3. 生成新的 `.conf` 文件并强推到 `release` 分支；
4. 通过本仓库的 Raw 地址提供订阅。

上游文件与个人规则彼此分离，因此上游修改 `manual_*.txt` 时，不需要用
`-X ours` 强行保留旧文件，也不容易漏掉上游的新规则。

## 分支约定

| 分支 | 用途 | 是否会被自动覆盖 |
|---|---|---|
| `build` | 上游源码、工作流和个人规则，只在这里维护 | 不会；会自动合并上游 |
| `release` | Shadowrocket 最终订阅产物 | 会；每次构建都会重建 |

不要手工编辑 `release` 分支。

## 添加个人规则

规则文件每行填写一个裸域名或 IP/CIDR，不要填写
`DOMAIN-SUFFIX,...,Proxy` 等前缀。

| 目的 | 文件 |
|---|---|
| 走代理 | `factory/custom_proxy.txt` |
| 直连 | `factory/custom_direct.txt` |
| 拒绝/去广告 | `factory/custom_reject.txt` |
| 补充 GFWList | `factory/custom_gfwlist.txt` |
| 排除 GFWList 误判 | `factory/custom_gfwlist_excludes.txt` |
| 绕过 macOS/Shadowrocket 系统 HTTP 代理 | `factory/custom_skip_proxy.txt` |

当前已创建 `custom_proxy.txt` 和 `custom_skip_proxy.txt`。需要其他普通规则
类型时，直接创建对应文件即可，构建包装脚本会自动识别非空文件。

### 官方 Tailscale 与 `custom_skip_proxy.txt`

`custom_skip_proxy.txt` 中的项目会在构建期间去重并追加到
`factory/template/sr_head.txt` 的 `[General] / skip-proxy`，随后进入所有使用
该公共头部的生成配置。当前用于官方 Tailscale 客户端的内容为：

```text
100.64.0.0/10
tail6828f5.ts.net
*.tail6828f5.ts.net
```

这会让 macOS/Chrome 不把对应连接交给 Shadowrocket 的系统 HTTP 代理，
而是直接交给官方 Tailscale 客户端和 MagicDNS 处理。它与
`DOMAIN-SUFFIX,...,DIRECT` 等普通分流规则用途不同：后者只有在请求已经进入
Shadowrocket 后才生效，不能解决系统 HTTP 代理先拦截私有域名的问题。

此机制不会启用 Shadowrocket 内置 Tailscale 模块，也不需要 Tailscale
auth key 或“始终使用 DERP”。模板 `bypass-tun` 中原有的
`100.64.0.0/10` 保持不变。

提交并推送 `build` 分支后，GitHub Actions 会立即构建；此外每天
23:00 UTC（北京时间次日 07:00，实际启动可能延迟）也会自动构建。

## 本地验证

```bash
git switch build
./factory/build_with_custom_rules.sh
```

脚本只会临时把个人规则叠加到 `manual_*.txt` 和 `template/sr_head.txt`，
结束或失败时都会恢复上游文件；生成的 `.conf` 文件会保留，方便检查。

## 手动触发

打开 GitHub 仓库的 **Actions → Release Shadowrocket Rules → Run workflow**。
工作流可以从 `build` 或 `release` 分支手动运行，但它始终读取最新的
`build` 分支并发布到 `release`。

## 推荐订阅地址

```text
https://raw.githubusercontent.com/klwb/Shadowrocket-ADBlock-Rules-Forever/release/sr_top500_banlist_ad.conf
```

其他配置只需替换最后的文件名。个人代理规则会进入使用
`manual_proxy` 的 7 种配置，不会进入语义上不使用代理域名列表的
`sr_ad_only.conf`、`sr_direct_banad.conf`、`sr_proxy_banad.conf`
和回国配置。

## 工作流的安全策略

- 上游有普通更新时自动合并并保存回 `build`；
- 上游发生真实合并冲突时立即失败，等待人工处理，不会静默丢规则；
- 推送 `build` 失败时立即失败，不再使用 `|| true` 掩盖错误；
- 同一时间只允许一个发布任务，避免两个定时/手动任务互相强推；
- 下载懒人规则失败时停止发布，避免提交空文件；
- 每次构建都会重新生成二维码，二维码和文档都指向本仓库 Raw 地址；
- 每次发布都会把 `build` 中的最新版工作流复制到 `release`，保证默认
  分支上的定时任务持续更新。

## 排错

- 工作流无法推送：在仓库 **Settings → Actions → General** 中确认
  Workflow permissions 允许读写；工作流也已显式声明 `contents: write`。
- 规则没有出现在配置中：确认修改的是 `factory/custom_*.txt`，并检查该
  配置是否使用相应类型的手工规则。
- 定时任务没有准点开始：GitHub 的 schedule 可能排队延迟，这是正常现象。
- Raw 地址短时间还是旧内容：GitHub Raw 有短暂缓存，稍后重新下载即可。
