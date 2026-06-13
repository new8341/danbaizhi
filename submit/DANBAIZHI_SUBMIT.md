# 任务 3 Danbaizhi — 提交文件与天池提交流程

## 一、赛方要求的 Docker 规范

| 项 | 要求 | 本仓库实现 |
|----|------|------------|
| 入口脚本 | `/app/run.sh` | `submit/run.sh` 复制为 `/app/run.sh` |
| 读数据 | `/saisdata/` | 评测挂载 `1.json`、`2.json`、`3.json` |
| 写结果 | `/saisresult/submission.zip` | `submit/tracks/danbaizhi.py` 打包后 mv |
| 截止时间 | 2026-06-29 14:00 | — |

## 二、本目录已准备的文件

| 文件 | 说明 |
|------|------|
| `submission.zip` | **评测期望的最终产物**（11 个 mmCIF + `agent.log`） |
| `output.zip` | 与 `Project/result/output.zip` 相同，便于对照 |
| `manifest.json` | 成员清单与镜像地址元数据 |

`submission.zip` 内文件（共 12 个）：

```text
1_conf1_pred.cif … 1_conf4_pred.cif   （题 1，4 构象）
2_conf1_pred.cif … 2_conf4_pred.cif   （题 2，4 构象）
3_conf1_pred.cif … 3_conf3_pred.cif   （题 3，3 构象）
agent.log
```

方案来源：`Project/`（线上参考分 **0.717129**），随机种子 **42**。

## 三、重新生成本地 submission.zip

在仓库根目录 `H:\Fusai`：

```powershell
py -3 submit/main.py --track danbaizhi `
  --saisdata documen/Danbaizhi `
  --saisresult submit/_local_saisresult `
  --work-dir H:\Fusai

Copy-Item submit\_local_saisresult\submission.zip submit\danbaizhi\submission.zip -Force
```

可选自检（与 golden 比对）：

```powershell
cd Project
py -3 code/main.py verify-repro
```

## 四、构建并推送 Docker 镜像

### 4.1 前置

1. 启动 **Docker Desktop**（本机需 Linux 引擎可用）。
2. 在 ACR 控制台创建私有仓库：`ai4s-lee/danbaizhi`。
3. 复制配置（可选）：

```powershell
Copy-Item submit\registry.env.example submit\registry.env
```

### 4.2 构建

```powershell
cd H:\Fusai
.\submit\build_all.ps1 -Tag 0.1 -Tracks danbaizhi
```

或：

```powershell
docker build -f submit/Dockerfile.danbaizhi `
  -t crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1 .
```

### 4.3 本地容器试跑（提交前必做）

```powershell
docker run --rm `
  -v H:\Fusai\documen\Danbaizhi:/saisdata:ro `
  -v H:\Fusai\submit\_local_saisresult:/saisresult `
  crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1
```

成功标志：控制台出现 `[OK] wrote /saisresult/submission.zip`，且 `submit\_local_saisresult\submission.zip` 已更新。

### 4.4 登录并推送

```powershell
docker login crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com
# 用户名：ACR 控制台显示的用户名
# 密码：仓库/实例设置的固定密码（非阿里云登录密码）

docker push crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1
```

或：

```powershell
.\submit\build_all.ps1 -Tag 0.1 -Tracks danbaizhi -Push
```

## 五、天池提交（任务 3 入口）

1. 打开大赛页面 → **任务 3（蛋白质构象系综）** → **提交结果** / Docker 镜像提交。
2. 填写：

| 字段 | 填写内容 |
|------|----------|
| 镜像地址 | `crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1` |
| 用户名 | ACR 用户名 |
| 密码 | ACR 固定密码 |

3. 提交后等待评测日志；在 **我的成绩** 查看分数与运行日志。
4. 复赛通常 **每天 1 次** 提交机会，失败也计次——务必先完成第四节容器试跑。

## 六、常见问题

| 现象 | 处理 |
|------|------|
| `docker API ... cannot find the file` | 启动 Docker Desktop 后重试 build/run |
| 评测找不到 submission | 确认输出文件名为 `submission.zip`（不是 `output.zip`） |
| 分数为 0 | 检查 zip 是否含 11 个 cif + agent.log；查看评测日志 |
| 想换版本 tag | 修改 `submit/registry.env` 中 `TAG`，重新 build + push + 天池填新 tag |

## 七、归档（仓库规则）

若本次提交可能改变线上分数或 zip 几何，在 **generate_submission 启动时刻** 归档：

```text
daima/YYYYMMDDHHMM/
  ├── 相关代码
  └── submission.zip / output.zip
```

当前本地产物也可复制到 `daima/<时刻>/` 备查。
