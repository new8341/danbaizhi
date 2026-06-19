#!/usr/bin/env python3
"""Regenerate STATUS/SCOREBOARD.md from cundang, guidang, and track_pins."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKS = ("danbaizhi", "drugclip", "baxiangfenzi", "shenjingsuanzi")

CHAMPION_REF = {
    "danbaizhi": "0.717+ (MSA prior)",
    "drugclip": "~19.23 (ReDrugClip hybrid)",
    "baxiangfenzi": "TBD",
    "shenjingsuanzi": "~57.69 (pdeburgers ref)",
}


def _read_best(track: str) -> dict | None:
    p = ROOT / "cundang" / track / "best.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _latest_guidang(track: str) -> dict | None:
    best_stamp = ""
    best_meta: dict | None = None
    guidang = ROOT / "guidang"
    if not guidang.is_dir():
        return None
    for stamp_dir in guidang.iterdir():
        if not stamp_dir.is_dir() or not re.fullmatch(r"\d{12}", stamp_dir.name):
            continue
        meta_path = stamp_dir / track / "score_meta.json"
        if not meta_path.is_file():
            continue
        if stamp_dir.name >= best_stamp:
            best_stamp = stamp_dir.name
            best_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            best_meta["_stamp"] = stamp_dir.name
    return best_meta


def _read_pins() -> dict:
    p = ROOT / "submit" / "track_pins.json"
    if not p.is_file():
        return {}
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    return data.get("tracks", {})


def _fmt_score(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.6f}"


def generate() -> str:
    pins = _read_pins()
    rows: list[str] = []
    for track in TRACKS:
        best = _read_best(track)
        recent = _latest_guidang(track)
        pin = pins.get(track, {})
        cundang_s = _fmt_score(float(best["score"]) if best else None)
        cundang_c = best.get("git_commit", "—") if best else "—"
        if recent:
            guidang_s = _fmt_score(float(recent.get("score", 0)))
            guidang_note = recent.get("note", "")[:40]
            guidang_cell = f"{guidang_s} ({recent.get('_stamp', '')}) {guidang_note}".strip()
        else:
            guidang_cell = "—"
        pin_cell = pin.get("commit", "—")
        champ = CHAMPION_REF.get(track, "—")
        rows.append(
            f"| {track} | {cundang_s} ({cundang_c}) | {guidang_cell} | `{pin_cell}` | {champ} |"
        )

    header = """# 分数榜

> **自动生成** — 运行 `py -3 scripts/generate_scoreboard.py` 或 `.\\scripts\\daily_sync.ps1`

<!-- AUTO-GENERATED: do not edit below this line manually -->

| 赛道 | 仓库 best (cundang) | 最近归档 (guidang) | 已发布 pin | 冠军参考 |
|------|---------------------|--------------------|------------|----------|
"""
    footer = """
<!-- END AUTO-GENERATED -->

## 说明

- **cundang**：本仓库该赛道历史最高分（`cundang/<track>/best.json`）
- **guidang 最近**：时间戳最大的一条 `guidang/*/score_meta.json`
- **pin**：`submit/track_pins.json` 中 commit
- **冠军参考**：外部或初赛后已知 SOTA（非自动更新）

"""
    body = "\n".join(rows)
    return header + body + footer


def main() -> int:
    out = ROOT / "STATUS" / "SCOREBOARD.md"
    text = generate()
    out.write_text(text, encoding="utf-8")
    print(f"updated -> {out} ({datetime.now().isoformat(timespec='seconds')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
