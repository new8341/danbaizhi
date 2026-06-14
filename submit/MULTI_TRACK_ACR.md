# 四赛道 ACR 多仓库 — 隔离与同步构建

同一 GitHub 仓 `new8341/danbaizhi`，四个 ACR 镜像仓库，**代码同步、运行隔离、构建可并行**。

---

## 一、隔离原则（互不影响）

```
┌─────────────────────────────────────────────────────────┐
│  GitHub monorepo (new8341/danbaizhi)                     │
├──────────────┬──────────────┬──────────────┬──────────────┤
│ Project/     │ (待建)       │ (待建)       │ documen/     │
│ 任务3 业务   │ DrugClip/    │ Baxiangfenzi/│ Shenjingsuanzi│
├──────────────┴──────────────┴──────────────┴──────────────┤
│  submit/          ← 共享入口（改这里须跑全赛道测试）        │
│    main.py · run.sh · pack_submission.py · tracks/*.py    │
└─────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
   ACR/danbaizhi   ACR/drugclip  ACR/baxiangfenzi ACR/shenjingsuanzi
   FUSAI_TRACK=    FUSAI_TRACK=  FUSAI_TRACK=     FUSAI_TRACK=
   danbaizhi       drugclip      baxiangfenzi     shenjingsuanzi
```

| 层级 | 隔离方式 |
|------|----------|
| **运行** | 每镜像固定 `ENV FUSAI_TRACK=...`，只跑对应 `tracks/*.py` |
| **数据** | 任务1 benchmark 在镜像内；任务2/3/4 读 `/saisdata` 挂载 |
| **输出** | 任务1/2 → `result.zip`；任务3/4 → `submission.zip` |
| **依赖** | 各 `Dockerfile.<track>` 独立基础镜像与 COPY 列表 |
| **构建** | 四个 ACR 仓库、四个 Dockerfile 路径，失败不阻塞其他仓库 |
| **业务迭代** | 只改 `Project/` 不影响任务1；只改 `tracks/drugclip.py` 不影响任务3 |

### 修改共享层时的安全网

改 `submit/main.py`、`pack_submission.py`、`run.sh` 前：

```powershell
cd H:\Fusai
py -3 -m pytest submit/tests/ -q
```

通过后再 `git push` + 触发四仓构建。

---

## 二、ACR 控制台：创建另外三个仓库

在 **华东2（上海）** 个人版实例下，命名空间 `ai4s-lee`，各创建 **私有** 仓库：

| 仓库名 | Dockerfile 路径 | 构建上下文 | 镜像 tag |
|--------|-------------------|------------|----------|
| `danbaizhi` | `Dockerfile` | `/` | `$version` |
| `drugclip` | `Dockerfile.drugclip` | `/` | `$version` |
| `baxiangfenzi` | `Dockerfile.baxiangfenzi` | `/` | `$version` |
| `shenjingsuanzi` | `Dockerfile.shenjingsuanzi` | `/` | `$version` |

> ACR 控制台「Dockerfile」框**只填文件名**（1–64 字符，字母/数字/`-`/`_`/`.`），**不要**写 `submit/...`。根目录的 `Dockerfile.*` 是 `submit/Dockerfile.*` 的构建别名，内容保持同步。

每个仓库统一设置：

- 代码源：**GitHub** → `new8341/danbaizhi`
- 构建规则：`tags:release-v$version`
- 代码变更自动构建：**开启**
- **海外机器构建：开启**（四个仓库均开启；国内节点拉 Docker Hub `python:3.10-slim` 会 `i/o timeout`）
- 不使用缓存：**关闭**

配置明细见 [`acr_repos.yaml`](acr_repos.yaml) 与 [`track_pins.json`](track_pins.json)。

### 分赛道独立回滚（推荐）

每个 ACR 仓库增加**第二条构建规则**（或替换旧统一 tag 规则）：

| 仓库 | Branch/Tag | Dockerfile | 镜像版本 |
|------|------------|------------|----------|
| danbaizhi | `release-v0.1-danbaizhi` | `Dockerfile` | `0.1` |
| drugclip | `release-v0.1-drugclip` | `Dockerfile.drugclip` | `0.1` |
| baxiangfenzi | `release-v0.1-baxiangfenzi` | `Dockerfile.baxiangfenzi` | `0.1` |
| shenjingsuanzi | `release-v0.1-shenjingsuanzi` | `Dockerfile.shenjingsuanzi` | `0.1` |

当前各赛道 pin 见 `submit/track_pins.json`。回滚**单个赛道**：

```powershell
.\submit\restore_track.ps1 -List
.\submit\restore_track.ps1 -Track danbaizhi -Node 3f000c1 -RetagAcr
.\submit\restore_track.ps1 -Track baxiangfenzi -Node e491c22 -FilesOnly   # 只恢复该赛道源码
.\submit\publish_track.ps1 -Track baxiangfenzi          # 单赛道发布（改 pin + 只打该 tag）
.\submit\trigger_acr_build.ps1 -Tracks danbaizhi -SkipPushMain   # 显式多赛道重建
```

**请删除 ACR 上旧的统一规则 `release-v0.1`**，避免四仓被同一 tag 联动重建。

---

## 三、发布与构建（单赛道互不影响）

`git push main` **不会**自动更新四仓镜像。只有移动某赛道的 **pin + tag** 才重建该仓。

### 只改一个赛道（标准流程）

```powershell
git commit -m "feat(baxiangfenzi): ..."
.\submit\publish_track.ps1 -Track baxiangfenzi
```

其他三赛道 `track_pins.json` 与 ACR 镜像 **不变**。

### 显式重建多个赛道

```powershell
.\submit\trigger_acr_build.ps1 -Tracks danbaizhi,drugclip -SkipPushMain
```

**必须带 `-Tracks`**（无默认全量）。

### 天池提交（不变）

仍使用 `.../ai4s-lee/<repo>:0.1`、原用户名/密码、原输出文件名（`submission.zip` / `result.zip`）。

### 任务1 前置条件

DrugClip 须先把官方 **benchmark.zip** 解压到：

```text
documen/DrugClip/benchmark/manifest.jsonl
documen/DrugClip/benchmark/tasks/...
```

未放置时，仅 **drugclip** 仓库构建失败，其余三仓仍成功。

---

## 四、镜像地址（天池各任务分别提交）

```text
.../ai4s-lee/danbaizhi:0.1
.../ai4s-lee/drugclip:0.1
.../ai4s-lee/baxiangfenzi:0.1
.../ai4s-lee/shenjingsuanzi:0.1
```

用户名 `gengfu369`，密码为 ACR 固定密码。

---

## 五、本地验证（提交前）

```powershell
py -3 -m pytest submit/tests/ -q

py -3 submit/main.py --track danbaizhi --saisdata documen/Danbaizhi --saisresult submit/_local_saisresult --work-dir H:\Fusai
py -3 submit/main.py --track baxiangfenzi --saisdata documen/Baxiangfenzi --saisresult submit/_local_saisresult --work-dir H:\Fusai
# drugclip / shenjingsuanzi 见 agent/tracks/*.md
```

有 Docker Desktop 时按赛道构建（使用独立 ignorefile 减小上下文）：

```powershell
.\submit\build_all.ps1 -Tracks danbaizhi,baxiangfenzi -DryRun
```

---

## 六、版本与迭代建议

| 策略 | 做法 |
|------|------|
| **统一版本** | 四仓共用 tag `0.1` / `release-v0.1`，便于对照 |
| **单赛道热修** | `.\submit\publish_track.ps1 -Track <赛道>` → 只打 `release-v0.1-<赛道>` tag，仅该仓触发构建 |
| **仅重建一仓** | ACR 该仓库页 **立即构建**，或 `.\submit\trigger_acr_build.ps1 -Tracks <赛道>` |
| **提分优先级** | 任务3 已可用 → 任务2 打通 baseline → 任务1/4 并行 Agent 开发 |

---

## 七、目录规划（业务代码扩展）

| 赛道 | 建议新增目录 | 不得放入镜像 |
|------|--------------|--------------|
| 任务1 | `DrugClip/code/` + benchmark 在 `documen/DrugClip/benchmark/` | 测试集答案 |
| 任务2 | `Baxiangfenzi/code/` | 预置分子/路线库 |
| 任务3 | `Project/`（已有） | — |
| 任务4 | `Shenjingsuanzi/agent_code/` → 复制到 `/app/agent_code/` | 过大训练数据 |

各赛道 Dockerfile 只 `COPY` 本赛道需要的目录，避免交叉污染。
