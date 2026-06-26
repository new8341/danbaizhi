# 资源索引

## 赛题数据（只读）

| 赛道 | 路径 |
|------|------|
| danbaizhi | `documen/Danbaizhi/`（1.json, 2.json, 3.json） |
| drugclip | `documen/DrugClip/` + 镜像内 `/app/benchmark` |
| baxiangfenzi | `documen/Baxiangfenzi/`（target*.pdb） |
| shenjingsuanzi | `documen/Shenjingsuanzi/`（problem1/2, 训练 48/49） |

## 本地开发数据

| 路径 | 说明 |
|------|------|
| `Project/processed_data/` | danbaizhi 序列先验、ColabFold 输出 |
| `Project/data/colabfold_xdg_cache/` | ColabFold 权重缓存（gitignore） |
| `submit/tests/fixtures/` | 迷你测试集 |
| `submit/_local_saisresult/` | 本地 docker/run 输出 |

## 云平台

| 资源 | 文档 |
|------|------|
| 阿里云 ACR | `submit/ACR_CLOUD_BUILD.md`, `submit/MULTI_TRACK_ACR.md` |
| OAuth 登录 | `submit/aliyun_oauth_login.ps1` |
| 镜像配置 | `submit/acr_repos.yaml`, `submit/registry.env.example` |

## 日志

| 类型 | 位置 |
|------|------|
| ColabFold A1 | `Project/processed_data/colabfold/_logs/` |
| Agent 提交日志 | zip 内 `agent.log` / `result.log` |
| ACR 构建 | 阿里云控制台 → 对应 repo → 构建记录 |

## 参考冠军代码（只读对照）

| 赛道 | 路径 |
|------|------|
| shenjingsuanzi | `shenjingsuanzi/daima/202605192309`（~57.69） |
| drugclip | `cundang/drugclip/`（ReDrugClip hybrid，~19.23） |
