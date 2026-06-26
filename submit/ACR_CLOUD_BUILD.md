# 阿里云 ACR 个人版 — 免费云端构建（无需本机 Docker）

ACR **个人版**在公测限额内**免费**托管镜像，并支持从 **GitHub 代码源**在云端执行 `docker build`，本机**不必安装/启动 Docker Desktop**。

参考：[ACR 个人版创建仓库并构建镜像](https://help.aliyun.com/zh/acr/user-guide/create-a-repository-and-build-images) · [绑定 GitHub 代码源](https://www.alibabacloud.com/help/zh/acr/user-guide/bind-a-source-code-hosting-platform-1)

---

## 一、前提

| 项 | 你的现状 |
|----|----------|
| GitHub 仓库 | https://github.com/new8341/danbaizhi（代码已推送） |
| ACR 实例 | `crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com` |
| 命名空间 | `ai4s-lee` |
| 仓库名 | `danbaizhi` |
| 镜像 tag | `0.1`（可自定） |

---

## 二、控制台操作（一次性）

### 1. 打开 ACR 个人版

1. 登录 [容器镜像服务控制台](https://cr.console.aliyun.com/)
2. 地域选 **华东 2（上海）**（与 `cn-shanghai` 实例一致）
3. 进入你的 **个人版实例**

### 2. 绑定 GitHub

1. 左侧 **仓库管理 → 代码源**
2. **GitHub** 一列点击 **绑定账号**
3. 在 GitHub 授权页点击 **Authorize**（需 GitHub 账号 `new8341`）

文档：[绑定源代码托管平台](https://www.alibabacloud.com/help/zh/acr/user-guide/bind-a-source-code-hosting-platform-1)

### 3. 创建/配置镜像仓库 `danbaizhi`

若仓库已存在，进入仓库 → **构建** 修改规则即可。

**新建时**（仓库管理 → 创建镜像仓库）：

| 配置项 | 填写 |
|--------|------|
| 命名空间 | `ai4s-lee` |
| 仓库名称 | `danbaizhi` |
| 仓库类型 | **私有** |
| 代码源 | **GitHub** → `new8341/danbaizhi` |
| 分支 | `main` |
| Dockerfile 路径 | `submit/Dockerfile.danbaizhi` |
| Dockerfile 所在目录（构建上下文） | **`/`**（仓库根目录） |
| 镜像版本标签 | `0.1` 或 `${branch}-${short_commit}` |
| 代码变更自动构建 | 可选开启（push 后自动 build） |
| **海外机器构建** | **关闭**（基础镜像是上海 `tcc-public`，用国内构建更快） |

### 4. 立即构建

1. 仓库详情 → **构建** → **构建规则** → **立即构建**
2. 等待状态 **成功**（首次约 5–15 分钟，取决于 `Project/` 体积）
3. **镜像版本** 中应出现：`.../ai4s-lee/danbaizhi:0.1`

---

## 三、构建完成后：天池提交

镜像地址（与本地 `registry.env` 一致）：

```text
crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1
```

天池 **任务 3** → **提交结果**（Docker）：

| 字段 | 值 |
|------|-----|
| 镜像地址 | 上列完整路径（含 tag） |
| 用户名 | ACR 控制台 **访问凭证** 中的用户名 |
| 密码 | 仓库/实例 **固定密码**（非阿里云登录密码） |

固定密码设置：个人版实例 → **访问凭证** → 设置/重置。

---

## 四、代码更新后重新构建

```powershell
cd H:\Fusai
git add -A
git commit -m "feat: ..."
git push origin main
```

若已开启「代码变更自动构建」，push 后 ACR 会自动 build；否则在控制台 **立即构建**。

---

## 五、云端构建 vs 本机 Docker

| 方式 | 适用 |
|------|------|
| **ACR 云端构建（推荐）** | 本机无 Docker / 网络差 / 只想 push 到 ACR |
| 本机 `docker build` + `push` | 需本地试跑容器时（见 `publish_danbaizhi.ps1`） |

本地验证 submission 仍可在 Windows 直接跑（无需 Docker）：

```powershell
py -3 submit/main.py --track danbaizhi --saisdata documen/Danbaizhi --saisresult submit/_local_saisresult --work-dir H:\Fusai
```

---

## 六、构建失败排查

| 现象 | 处理 |
|------|------|
| 拉取基础镜像失败 | 确认 Dockerfile 使用 `registry.cn-shanghai.aliyuncs.com/tcc-public/python:3` |
| `COPY Project/` 失败 | 构建上下文必须是仓库根 `/`，不是 `submit/` |
| GitHub 未绑定 | 代码源页重新授权 GitHub |
| 构建超时 | 查看构建日志；`.dockerignore` 已排除无关大目录 |
| 天池拉取失败 | 检查镜像 tag 是否存在；固定密码是否正确 |
