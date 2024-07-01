import json
import logging
import subprocess
from pathlib import Path
from typing import Annotated, Literal, TypedDict

import pysubs2
import typer

logger = logging.getLogger(__name__)

File = Annotated[Path, typer.Argument(file_okay=True, dir_okay=False)]


def run(*args: str | Path):
    return subprocess.run(args, check=True, capture_output=True)


def find_ass(path: Path) -> Path:
    path_ass = path.with_suffix(".ass")
    if path_ass.exists():
        return path_ass
    path_ssa = path.with_suffix(".ssa")
    if path_ssa.exists():
        return path_ssa

    raise RuntimeError(f"ASS track not found for {path}")


def first_event(events: pysubs2.SSAFile):
    events.sort()
    for event in events:
        if not event.is_comment and "\\k" in event.text:
            return event

    raise RuntimeError(f"No event found in {events}")


class MKVTKTracks(TypedDict):
    codec: str
    id: int
    type: Literal["video", "audio", "subtitles"]


class MKVTKIdentify(TypedDict):
    tracks: list[MKVTKTracks]


def muxinst(orig: File, inst: File):
    orig_ass = find_ass(orig)
    inst_ass = find_ass(inst)

    orig_subs = pysubs2.load(str(orig_ass))
    inst_subs = pysubs2.load(str(inst_ass))

    orig_first_event = first_event(orig_subs)
    inst_first_event = first_event(inst_subs)
    logging.info(orig_first_event)
    logging.info(inst_first_event)

    orig_start = orig_first_event.start
    inst_start = inst_first_event.start

    inst_shift_ms = orig_start - inst_start

    logging.info(f"{orig}: instrumental track shift: {inst_shift_ms}")

    proc = run("mkvmerge", "-J", str(inst))
    inst_identify: MKVTKIdentify = json.loads(proc.stdout.decode())
    audio_tracks = [t for t in inst_identify["tracks"] if t["type"] == "audio"]
    if len(audio_tracks) > 1:
        raise RuntimeError(f"found two audio tracks in {inst}")

    track_id = audio_tracks[0]["id"]
    outfile = orig.with_suffix(".mka")
    run("mkvmerge", "-D", "-S", "--sync", f"{track_id}:{inst_shift_ms}", "-a", str(track_id), inst, "-o", outfile)
    logger.info(f"created {outfile}")

    inst.unlink()
    logger.warn(f"deleted {inst}")
    inst_ass.unlink()
    logger.warn(f"deleted {inst_ass}")


def main():
    typer.run(muxinst)
