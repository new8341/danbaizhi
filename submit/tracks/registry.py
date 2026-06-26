from __future__ import annotations

import importlib

from submit.tracks.base import TrackRunner

# Lazy import: each track image only installs its own dependencies.
_RUNNER_SPECS: dict[str, tuple[str, str]] = {
    "danbaizhi": ("submit.tracks.danbaizhi", "DanbaizhiRunner"),
    "drugclip": ("submit.tracks.drugclip", "DrugclipRunner"),
    "baxiangfenzi": ("submit.tracks.baxiangfenzi", "BaxiangfenziRunner"),
    "shenjingsuanzi": ("submit.tracks.shenjingsuanzi", "ShenjingsuanziRunner"),
}


def get_runner(track: str) -> TrackRunner:
    key = track.strip().lower()
    if key not in _RUNNER_SPECS:
        from submit.pack_submission import emit_error

        emit_error(
            "TRACK_UNKNOWN",
            f"Unknown track {track!r}; supported: {', '.join(sorted(_RUNNER_SPECS))}",
        )
    module_name, class_name = _RUNNER_SPECS[key]
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls()
