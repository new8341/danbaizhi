from __future__ import annotations

from submit.tracks.base import TrackRunner
from submit.tracks.baxiangfenzi import BaxiangfenziRunner
from submit.tracks.danbaizhi import DanbaizhiRunner
from submit.tracks.drugclip import DrugclipRunner
from submit.tracks.shenjingsuanzi import ShenjingsuanziRunner

_RUNNERS: dict[str, type[TrackRunner]] = {
    "danbaizhi": DanbaizhiRunner,
    "drugclip": DrugclipRunner,
    "baxiangfenzi": BaxiangfenziRunner,
    "shenjingsuanzi": ShenjingsuanziRunner,
}


def get_runner(track: str) -> TrackRunner:
    key = track.strip().lower()
    if key not in _RUNNERS:
        from submit.pack_submission import emit_error

        emit_error(
            "TRACK_UNKNOWN",
            f"Unknown track {track!r}; supported: {', '.join(sorted(_RUNNERS))}",
        )
    return _RUNNERS[key]()
