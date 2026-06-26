# GitHub 与阿里云 ACR 配置指南

本仓库有两条**独立**提交链路，需分别配置：

| 链路 | 作用 | 目标 |
|------|------|------|
| **GitHub** | 源码、`submission.zip` 样例、审核材料 | https://github.com/new8341/danbaizhi |
| **阿里云 ACR + 天池** | Docker 镜像评测、复赛打分 | `.../ai4s-lee/danbaizhi:0.1` |

---

## 一、GitHub（推送代码）

### 1.1 当前仓库远程

已配置：

```text
origin  https://github.com/new8341/danbaizhi.git
```

### 1.2 创建 Personal Access Token（推荐 HTTPS）

1. 登录 GitHub → **Settings** → **Developer settings** → **Personal access tokens**
2. 选择 **Fine-grained tokens** 或 **Tokens (classic)**
3. 权限至少包含：**Contents: Read and write**
4. 生成后**复制 token**（只显示一次）

Classic token 备选权限：`repo`（私有库）或 `public_repo`（公开库）。

### 1.3 本机 Git 身份（仅本仓库，不改全局）

在 `H:\Fusai` 执行（把邮箱换成你的 GitHub 邮箱）：

```powershell
cd H:\Fusai
git config user.name "new8341"
git config user.email "你的GitHub邮箱@example.com"
```

### 1.4 首次 push / 更新 push

```powershell
cd H:\Fusai
git add -A
git status
git commit -m "feat: 描述改动"
git push origin main
```

提示输入密码时：

- **Username**：`new8341`
- **Password**：填 **PAT token**（不是 GitHub 登录密码）

Windows 建议安装 [Git Credential Manager](https://github.com/git-ecosystem/git-credential-manager)，首次输入后会记住 token。

### 1.5 SSH 方式（推荐：国内 HTTPS 443 不通时）

若 `git push` 报错 `Failed to connect to github.com port 443`，但本机可连 `ssh.github.com:443`，请用 SSH：

**① 已为本机生成密钥**（若不存在会自动创建）：

```powershell
# 查看公钥（复制整行）
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

**② GitHub 添加公钥**：  
GitHub → **Settings** → **SSH and GPG keys** → **New SSH key** → 粘贴公钥 → Save

**③ SSH 配置**（`~/.ssh/config`，已写入）：

```text
Host github.com
  HostName ssh.github.com
  Port 443
  User git
  IdentityFile ~/.ssh/id_ed25519
```

**④ 仓库 remote 改为 SSH**（本仓库已执行）：

```text
origin  git@github.com:new8341/danbaizhi.git
```

**⑤ 验证并推送**：

```powershell
ssh -T git@github.com
# 成功应看到：Hi new8341! You've successfully authenticated...

cd H:\Fusai
git push origin main
```

### 1.6 HTTPS + 代理（备选）

若使用 Clash 等本地代理（常见 `127.0.0.1:7890`）：

```powershell
git config --local http.https://github.com.proxy http://127.0.0.1:7890
git config --local https.https://github.com.proxy http://127.0.0.1:7890
git remote set-url origin https://github.com/new8341/danbaizhi.git
git push origin main
```

### 1.7 常见 GitHub 错误

| 错误 | 处理 |
|------|------|
| `Failed to connect to github.com port 443` | 改用 **SSH over 443**（§1.5）或配置 **HTTP 代理**（§1.6） |
| `Authentication failed` | HTTPS 时使用 PAT 代替账号密码 |
| `Permission denied (publickey)` | 将 `id_ed25519.pub` 添加到 GitHub SSH keys |
| `Author identity unknown` | 执行上文 1.3 `git config user.name/email` |
| push 很慢 | 大文件用 Git LFS；本仓库约 70MB，正常 |

---

## 二、阿里云 ACR（推送 Docker 镜像）

### 2.1 控制台准备

1. 打开 [容器镜像服务 ACR](https://cr.console.aliyun.com/)
2. 确认**个人版实例**已开通（地址含 `crpi-...personal.cr.aliyuncs.com`）
3. **命名空间**：`ai4s-lee`（已用）
4. **仓库**：创建 `danbaizhi`，类型 **私有**
5. 在仓库/实例设置 **固定密码**（用于 `docker login`，记住它）

你的 Registry 公网地址：

```text
crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com
```

### 2.2 本机 registry 配置

```powershell
cd H:\Fusai
Copy-Item submit\registry.env.example submit\registry.env
# 按需编辑 submit\registry.env 中的 TAG
```

`submit/registry.env` 已在 `.gitignore`，**勿提交密码**。

### 2.3 Docker Desktop

1. 安装并**启动** Docker Desktop（Linux 引擎）
2. 验证：`docker version`

### 2.4 登录 ACR

```powershell
docker login crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com
```

- **Username**：ACR 控制台「访问凭证」里的用户名（常为阿里云账号全名或显示名）
- **Password**：**固定密码**（不是阿里云登录密码）

### 2.5 构建并推送

```powershell
cd H:\Fusai

docker build -f submit/Dockerfile.danbaizhi `
  -t crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1 .

# 本地试跑
docker run --rm `
  -v H:\Fusai\documen\Danbaizhi:/saisdata:ro `
  -v H:\Fusai\submit\_local_saisresult:/saisresult `
  crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1

docker push crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1
```

或一键：

```powershell
.\submit\build_all.ps1 -Tag 0.1 -Tracks danbaizhi -Push
```

### 2.6 天池提交页填写

进入 **任务 3** → **提交结果**（Docker）：

| 字段 | 值 |
|------|-----|
| 镜像地址 | `crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1` |
| 用户名 | 与 `docker login` 相同 |
| 密码 | ACR 固定密码 |

### 2.7 常见 ACR 错误

| 错误 | 处理 |
|------|------|
| `denied: requested access denied` | 重新 `docker login`；检查命名空间/仓库名 |
| `manifest unknown` | 先 `docker push` 再在天池填 tag |
| build 连不上 Docker | 启动 Docker Desktop |
| 评测 0 分 | 看天池日志；确认 `/saisresult/submission.zip` 已生成 |

---

## 三、推荐工作流（改代码后）

```powershell
# 1. 本地验证
py -3 submit/main.py --track danbaizhi --saisdata documen/Danbaizhi --saisresult submit/_local_saisresult --work-dir H:\Fusai

# 2. 推 GitHub
git add -A && git commit -m "feat: ..." && git push origin main

# 3. 推 ACR（改 TAG 或复用 0.1 覆盖）
.\submit\build_all.ps1 -Tag 0.1 -Tracks danbaizhi -Push

# 4. 天池 Docker 提交（每天次数有限，先 docker run 试跑）
```

---

## 四、安全清单

- 勿提交：`submit/registry.env`、PAT、ACR 密码、API Key
- 天池提交后可在 ACR **重置固定密码**
- GitHub token 泄露后立即 **Revoke** 并换新
