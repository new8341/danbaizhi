"""Tests for submit/pack_submission.py."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from submit.pack_submission import emit_error, error_payload, pack_directory


def test_pack_directory_success(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "a.txt").write_text("hello", encoding="utf-8")
    out = tmp_path / "submission.zip"
    pack_directory(staging, out)
    assert out.is_file()
    with zipfile.ZipFile(out) as zf:
        assert zf.namelist() == ["a.txt"]


def test_pack_directory_failure_missing_dir(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    out = tmp_path / "submission.zip"
    with pytest.raises(SystemExit) as exc:
        emit_error("PACK_STAGING_MISSING", "missing staging")
    assert exc.value.code == 1


def test_error_payload_shape() -> None:
    payload = error_payload("TEST_CODE", "msg", "req-1")
    assert payload["success"] is False
    assert payload["error"]["code"] == "TEST_CODE"
    assert payload["error"]["requestId"] == "req-1"
