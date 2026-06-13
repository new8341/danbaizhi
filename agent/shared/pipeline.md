# Agent 四阶段闭环（大赛统一要求）

各赛道 Agent 应能在**零人工干预**下完成：

```text
文献/赛题理解 → 瓶颈诊断与假设 → 代码演进与工具调用 → 干实验验证与迭代
```

## 推荐单次迭代流程

1. 读取 `documen/<赛道>/readme.md` 与挂载数据  
2. 运行 baseline（或复现官方 inference）并记录指标  
3. 提出**一条**可验证假设（避免一次改太多）  
4. 修改**该赛道**业务代码（不碰 `documen/`）  
5. 本地生成提交 zip 并做格式/弱评测  
6. 更优则 build 镜像 → push → 天池提交；并视情况归档 `daima/`  

## 与 submit 层的关系

- **submit/**：只负责「读 saisdata → 调 Agent/业务代码 → 打 zip → 写 saisresult」  
- **agent/tracks + 各赛道代码目录**：负责科学逻辑与日志内容  

不要把四赛道算法堆进 `submit/main.py`；通过 `TrackRunner.run()` 调用各赛道入口即可。
