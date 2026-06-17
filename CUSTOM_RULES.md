# 自定义规则维护指引（klwb fork）

这份 fork 在每天 23:00 UTC（北京时间次日 7:00）自动：
1. 拉取上游 `Johnshall/build` 的最新源码并合并进本仓库 `build` 分支（保留我的自定义规则）
2. 构建出新的 `.conf` 文件，强推到 `release` 分支
3. Shadowrocket 订阅 `release` 分支的 raw URL 即可拿到「上游规则 + 我的规则」

## 分支约定

| 分支 | 作用 | 是否会被覆盖 |
|---|---|---|
| `build` | 源代码 + 我的自定义规则（**只在这里改**） | 否（每天合入上游，但保留我的改动） |
| `release` | 生成的 `.conf` 产物 | 是（每天 orphan 强推重建） |

**只编辑 `build` 分支。** 改 `release` 分支没用，会被下次工作流覆盖。

## 常见操作

### 加一个走代理的域名

编辑 `build` 分支的 [factory/manual_proxy.txt](factory/manual_proxy.txt)，在文末追加裸域名（不要带 `DOMAIN-SUFFIX,...,PROXY` 前缀，脚本会自动加）：

```
# 自定义 - 某分类
example.com
api.example.net
```

提交并 push 到 build 分支，工作流会自动跑（push 到 build 是触发条件之一）。

### 加一个直连（不走代理）的域名

编辑 `factory/manual_direct.txt`，格式同上。

### 加一个屏蔽（reject）的域名

编辑 `factory/manual_reject.txt`，格式同上。

### 把 GFW 黑名单里某个域名排除

编辑 `factory/manual_gfwlist_excludes.txt`。

### 立刻触发一次构建（不想等定时）

GitHub → Actions → 选 "Release Shadowrocket Rules" → 右上 "Run workflow" → 选 release 分支 → Run。

### 手动从上游拉最新源码（一般不用，工作流会自动做）

```bash
git fetch upstream build
git checkout build
git merge upstream/build -X ours
git push origin build
```

## 工作流原理（在 release 分支的 .github/workflows/release.yml）

```yaml
1. checkout build 分支（fetch-depth: 0，需要完整历史才能 merge）
2. checkout release 分支
3. Sync upstream build：
   - git fetch upstream build
   - git merge upstream/build -X ours
     ├─ 上游新增的规则无冲突 → 合并进来
     └─ 上游和我都改了同一行 → 保留我的版本
   - git push origin build（把合并结果保存回 build 分支）
4. pip install requirements.txt
5. 跑 factory/auto_build.sh 生成 .conf
6. 把 *.conf, figure/, LICENSE, readme.md 拷贝到 release/
7. 拉最新 lazy.conf / lazy_group.conf
8. release 分支用 orphan 方式强推（无历史，全量覆盖）
```

注意：`.github/workflows/release.yml` 这个文件本身在 release 分支，每天 orphan 重建时不会被删，因为 release 目录是从原 release 分支 checkout 出来的，`cp` 命令只覆盖 `.conf` 等指定文件，`.github/` 保持原样。

## 订阅 URL

把 Shadowrocket 里的订阅地址改成（按你原本订阅的文件名）：

```
https://raw.githubusercontent.com/klwb/Shadowrocket-ADBlock-Rules-Forever/release/<文件名>.conf
```

常用文件名见仓库根目录（`sr_top500_banlist_ad.conf`、`sr_ad_only.conf` 等）。

## 排错

- **工作流没跑** → 检查 Settings → Actions 是否开启
- **工作流失败在 push 阶段** → Settings → Actions → General → Workflow permissions 选 "Read and write permissions"
- **我的规则没出现在 .conf 里** → 检查是否写在了 `build` 分支的 `factory/manual_*.txt` 里（而不是 release 分支或者根目录）
- **想恢复某条改动** → `git log factory/manual_proxy.txt` 查历史，`git revert <commit>` 回滚
