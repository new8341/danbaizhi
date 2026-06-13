#!/usr/bin/env python
"""逐成员比对两个赛题 output.zip。

由 python code/main.py verify-repro 调用。
仅比对正式成员（N_conf*_pred.cif 与 agent.log）；忽略调试附加文件。
通过 main.py 调用时，路径应相对 Project 根目录。
"""
from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path

# 赛题要求的 zip 内文件名（正则）；其余条目仅报告，不参与判分
_SUBMISSION_NAME = re.compile(r"^(\d+_conf\d+_pred\.cif|agent\.log)$")


def zip_index(path: Path) -> dict[str, dict]:
    """为每个 zip 成员建立索引：大小、CRC32、解压后字节的 SHA256。"""
    out: dict[str, dict] = {}
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            data = z.read(info.filename)
            out[info.filename] = {
                "size": info.file_size,
                "crc": info.CRC,
                "sha256": hashlib.sha256(data).hexdigest(),
            }
    return out


def main() -> int:
    # 位置参数：先 golden zip，再复现得到的 zip
    g = Path(sys.argv[1])
    p = Path(sys.argv[2])
    gi, pi = zip_index(g), zip_index(p)

    # 仅保留赛题要求的文件参与比对
    g_sub = {k: v for k, v in gi.items() if _SUBMISSION_NAME.match(k)}
    p_sub = {k: v for k, v in pi.items() if _SUBMISSION_NAME.match(k)}
    g_extra = sorted(set(gi) - set(g_sub))
    p_extra = sorted(set(pi) - set(p_sub))
    all_names = sorted(set(g_sub) | set(p_sub))

    # 外层 zip 大小/哈希仅供参考；通过/失败以成员 SHA256 为准
    print(f"guidang: {g} ({g.stat().st_size} bytes)")
    print(f"project: {p} ({p.stat().st_size} bytes)")
    print(f"guidang SHA256 (outer zip): {hashlib.sha256(g.read_bytes()).hexdigest()}")
    print(f"project SHA256 (outer zip): {hashlib.sha256(p.read_bytes()).hexdigest()}")
    print()
    if g_extra:
        print("Extra in guidang (ignored for pass/fail):", g_extra)
    if p_extra:
        print("Extra in project (ignored for pass/fail):", p_extra)

    # 仅出现在一侧的成员
    only_g = set(g_sub) - set(p_sub)
    only_p = set(p_sub) - set(g_sub)
    if only_g:
        print("Missing in project:", sorted(only_g))
    if only_p:
        print("Missing in guidang:", sorted(only_p))
    print()

    # 对两侧都存在的成员比较 SHA256
    same = diff = 0
    for name in all_names:
        if name not in g_sub or name not in p_sub:
            continue
        if g_sub[name]["sha256"] == p_sub[name]["sha256"]:
            same += 1
        else:
            diff += 1
            print(f"DIFFER: {name}")
            print(f"  guidang  size={g_sub[name]['size']:>8}  sha256={g_sub[name]['sha256']}")
            print(f"  project  size={p_sub[name]['size']:>8}  sha256={p_sub[name]['sha256']}")
    print()
    print(
        f"Summary: {same} identical submission members, {diff} different, "
        f"{len(all_names)} required entries"
    )
    return 0 if diff == 0 and not only_g and not only_p else 1


if __name__ == "__main__":
    raise SystemExit(main())
