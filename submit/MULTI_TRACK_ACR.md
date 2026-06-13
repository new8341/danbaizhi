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
| `danbaizhi` | `Dockerfile`（根目录） | `/` | `$version` |
| `drugclip` | `submit/Dockerfile.drugclip` | `/` | `$version` |
| `baxiangfenzi` | `submit/Dockerfile.baxiangfenzi` | `/` | `$version` |
| `shenjingsuanzi` | `submit/Dockerfile.shenjingsuanzi` | `/` | `$version` |

每个仓库统一设置：

- 代码源：**GitHub** → `new8341/danbaizhi`
- 构建规则：`tags:release-v$version`
- 代码变更自动构建：**开启**
- **海外机器构建：关闭**
- 不使用缓存：**关闭**

配置明细见 [`acr_repos.yaml`](acr_repos.yaml)。

---

## 三、同步触发四仓构建

```powershell
cd H:\Fusai
git add -A
git commit -m "feat: ..."
git push origin main

# 一次 tag 触发四个 ACR 仓库并行构建
.\submit\trigger_acr_build.ps1 -Version 0.1
```

推送 `release-v0.1` 后，四个仓库若规则相同，会**各自**拉同一 commit、用**各自 Dockerfile** 构建，互不影响。

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
| **单赛道热修** | 只改该赛道业务代码 + push + 重新 `trigger_acr_build.ps1`；其他赛道镜像内容不变但会重建（可接受） |
| **仅重建一仓** | 在 ACR 该仓库页点 **立即构建**（不必等 tag） |
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
