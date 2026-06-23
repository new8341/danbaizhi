# LLM API Key — ACR 构建参数注入（安全流程）

> **原则**：Git 仓库只保留 `ARG` 空默认值；真实 Key **仅**填在 ACR 控制台「构建参数」中。  
> 出分后：**revoke Key** + **清空 ACR 构建参数**。

---

## 一、一次性准备（已完成 / 仓库侧）

各赛道 `submit/Dockerfile.<track>` 已使用：

```dockerfile
ARG BAXIANG_LLM_API_KEY=""
ENV BAXIANG_LLM_API_KEY=${BAXIANG_LLM_API_KEY}
```

本地参考模板：`submit/llm.env.example` → 复制为 `submit/llm.env`（**已 gitignore，勿提交**）。

---

## 二、ACR 控制台 — 为每个仓库填构建参数

登录 [ACR 控制台](https://cr.console.aliyun.com/) → 华东2（上海）→ 个人版实例 → **ai4s-lee**。

对每个仓库：**仓库管理 → 选择仓库 → 构建 → 编辑规则**（如 `release-v0.1-<track>`）。

### 1. baxiangfenzi

| 构建参数名 | 示例值 |
|------------|--------|
| `BAXIANG_LLM_API_KEY` | `sk-...`（一次性 Key） |
| `BAXIANG_LLM_BASE_URL` | `https://api.openai.com/v1` 或国内兼容地址 |
| `BAXIANG_LLM_MODEL` | `gpt-4o-mini` |

### 2. danbaizhi

| 构建参数名 | 示例值 |
|------------|--------|
| `DANBAIZHI_LLM_API_KEY` | `sk-...` |
| `DANBAIZHI_LLM_BASE_URL` | `https://api.openai.com/v1` |
| `DANBAIZHI_LLM_MODEL` | `gpt-4o-mini` |

### 3. drugclip

| 构建参数名 | 示例值 |
|------------|--------|
| `DRUGCLIP_LLM_API_KEY` | `sk-...` |
| `DRUGCLIP_LLM_BASE_URL` | `https://api.openai.com/v1` |
| `DRUGCLIP_LLM_MODEL` | `gpt-4o-mini` |

### 4. shenjingsuanzi（可选）

核心 PDE 推理不依赖 LLM；若复赛审核要求占位，可填：

| 构建参数名 | 说明 |
|------------|------|
| `SHENJING_LLM_API_KEY` | 可留空或填备用 Key |
| `SHENJING_LLM_BASE_URL` | 同上 |
| `SHENJING_LLM_MODEL` | 同上 |

### 其他构建设置

| 项 | 建议 |
|----|------|
| 海外机器构建 | **drugclip 开启**（GitHub fetch）；shenjingsuanzi 视 PyTorch 拉取情况 |
| 代码变更自动构建 | 开启 |
| Dockerfile | 根目录 `Dockerfile.<track>` |

保存规则后，可先点 **立即构建** 验证参数生效，再执行 `publish_track`。

---

## 三、发布（不含 Key）

```powershell
cd H:\Fusai
.\submit\publish_track.ps1 -Track baxiangfenzi
# 其他赛道同理，一次一个
```

此步骤只推 Git + 更新 `release-v0.1-<track>` tag，**不会**把 Key 写入 GitHub。

---

## 四、确认 ACR 构建成功

1. 构建列表状态 **成功**
2. 镜像版本出现 `.../ai4s-lee/<track>:0.1`

可选本地验证（需 `docker login` 个人版 ACR）：

```powershell
docker pull crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/baxiangfenzi:0.1
docker run --rm crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/baxiangfenzi:0.1 env | findstr BAXIANG_LLM
```

应看到非空的 `BAXIANG_LLM_API_KEY`（**勿截图外泄**）。

---

## 五、天池提交

镜像地址（含 tag）：

```text
crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/<track>:0.1
```

用户名/密码：ACR **访问凭证**（非阿里云登录密码）。

---

## 六、出分后立即清理

1. **API 平台**：撤销或轮换本次使用的 Key（OpenAI / 国内兼容平台）
2. **ACR 控制台**：删除该仓库构建规则中的 `*_LLM_API_KEY` 等参数（或整行清空）
3. **切勿**把用过的 Key 写回 Dockerfile 或 `git commit`

---

## 七、故障排查

| 现象 | 处理 |
|------|------|
| 构建成功但 `env` 里 Key 为空 | ACR 规则未填构建参数，或参数名与 `ARG` 不一致 |
| 构建失败 fetch GitHub | 开启 **海外机器构建** |
| 误将 Key commit 到 Git | 立即 revoke Key；`git filter` 或轮换；勿 force push 除非确认 |

---

## 八、相关文件

| 文件 | 作用 |
|------|------|
| `submit/Dockerfile.*` | `ARG` 占位（可提交） |
| `submit/llm.env.example` | 本地对照表 |
| `submit/llm.env` | 本地备忘（gitignore） |
| `submit/aliyun.env` | ACR 推送凭证（gitignore，与 LLM Key 无关） |
