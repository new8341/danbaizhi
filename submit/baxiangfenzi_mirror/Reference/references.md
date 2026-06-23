# Baxiangfenzi — 参考文献与外部依赖

## 核心方法

- AutoDock Vina：分子对接打分
- RDKit：分子构建、BRICS 片段逆合成枚举
- 口袋盒估计：由靶点 PDB 自动推导 docking box

## 数据

- 赛题靶点：评测时挂载 `/saisdata/37/target*.pdb`（B 榜替换文件，路径不变）
- **禁止**在镜像中打包测试集答案或固定结果表

## 外部服务

- LLM（可选）：用于分子设计与路线反思，配置见 `/app/Code/README.md`
