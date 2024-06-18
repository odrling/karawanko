# wankoparse - parse karaoke filenames
# Copyright (C) 2024  odrling
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import gzip
import importlib.resources
import itertools
import json
import logging
import mimetypes
import re
import sys
from functools import cache
from pathlib import Path
from typing import Annotated, Iterable, TypedDict

import typer
from rich.console import Console
from rich.logging import RichHandler

console = Console(file=sys.stderr)

FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(console=console)],
)

logger = logging.getLogger(__name__)

musicparse = re.compile(r"(?P<artist>.*?) - (?P<tags>[^-]*)-(?P<title>.*?)(?P<details>\(.*\))?$")
mediaparse = re.compile(r"(?P<media>.*?) - (?P<tags>[^-]*)-(?P<title>.*?)(?P<details>\(.*\))?$")
detailsparse = re.compile(r"(?P<detailtag>\w+)\s*(?P<content>[^-)]+)|\s*\((?P<comment>[^)]*)\)")
cleanup_titles_expr = re.compile(r"\W")


# only run once
@cache
def init_mimes():
    mimetypes.add_type("sub/ass", ".ass")
    mimetypes.add_type("sub/ssa", ".ssa")
    # cursed video files
    mimetypes.add_type("video/vob", ".vob")
    mimetypes.add_type("video/ts", ".ts")


def cleanup_titles(val: str):
    return cleanup_titles_expr.sub("", val.lower())


@cache
def anime_titles() -> str:
    anime_titles_file = importlib.resources.files("karawanko").joinpath("anime-titles.dat.gz")
    with importlib.resources.as_file(anime_titles_file) as f:
        file_content = gzip.decompress(f.read_bytes()).decode()
        return cleanup_titles(file_content)


def parse_tags(tags: str):
    return tags.strip().upper().split(" ")


def parse_details(details: str | None):
    kara_details: list[tuple[str, str]] = []
    if details is None:
        return kara_details

    # skip the first parenthese or the regex won't work
    details = details.strip()
    assert details[0] == "("
    assert details[-1] == ")"
    details = details[1:]

    for m in detailsparse.finditer(details):
        res = m.groupdict()
        if res.get("comment") is not None:  # noqa: SIM108
            el = ("comment", res["comment"])
        else:
            el = (res["detailtag"], res["content"].strip())
        kara_details.append(el)

    return kara_details


def parse_artists(artist: str) -> list[str]:
    artists = (a.strip() for a in artist.split(",") if a)
    return list(itertools.chain.from_iterable(a.split(" feat. ") for a in artists))


class MediaData(TypedDict):
    name: str | None
    media_type: str | None


class KaraData(TypedDict):
    title: str
    media: MediaData | None
    artists: list[str]
    tags: list[str]
    details: list[tuple[str, str]]


allowed_tags = {
    "AMV",
    "INS",
    "IS",
    "PV",
    "LIVE",
    "NSFW",
    "COVER",
    "REMIX",
    "SPOIL",
    "INST",
    "LONG",
    "COURT",
    "SHORT",
}


def validate_tags(tags: Iterable[str]):
    for tag in tags:
        if tag.startswith("OP"):
            continue
        if tag.startswith("ED"):
            continue
        if tag not in allowed_tags:
            logger.warning(f"Unknown tag {tag}")
            return False

    return True


def parse_file(file: Path) -> KaraData | None:
    media_type = None
    parents_name = [p.name for p in file.parents]
    if "Anime" in parents_name:
        parser = mediaparse
        media_type = "anime"
    elif "Wmusic" in parents_name or "CJKmusic" in parents_name:
        parser = musicparse
    elif "Dessin animé" in parents_name:
        parser = mediaparse
        media_type = "cartoon"
    elif "Jeu" in parents_name:
        parser = mediaparse
        media_type = "game"
    elif "Live action" in parents_name:
        parser = mediaparse
        media_type = "live_action"
    elif "Nouveau" in parents_name:
        parser = mediaparse
        media_type = "magic"
    else:
        logger.warning(f"we don't know how to parse {file!r}")
        return None

    file_match = parser.match(file.stem)
    if file_match is None:
        logger.error(f"could not parse {file.stem!r}")
        return None

    file_match_dict = file_match.groupdict()
    tags = parse_tags(file_match_dict["tags"])
    if not validate_tags(tags):
        return None
    details = parse_details(file_match_dict.get("details"))
    artists = parse_artists(file_match_dict.get("artist", ""))

    media: MediaData | None
    if media_type is None:  # noqa: SIM108
        media = None
    elif media_type == "magic":
        value = file_match_dict["media"].strip()
        if tags[0] in ("PV", "LIVE", "AMV"):
            artists = parse_artists(value)
            media = None
        elif cleanup_titles(value) in anime_titles():
            media = {"name": value, "media_type": "anime"}
        else:
            # assume game
            media = {"name": value, "media_type": "game"}
    else:
        media = {"name": file_match_dict["media"].strip(), "media_type": media_type}

    title: str = file_match_dict["title"].strip()

    return {
        "title": title,
        "tags": tags,
        "media": media,
        "artists": artists,
        "details": details,
    }


def parse_dir(dir: Path) -> dict[str, KaraData]:
    init_mimes()
    file_data: dict[str, KaraData] = {}
    files = dir.rglob("**/*")
    for f in files:
        if f.is_dir():
            continue

        mtype, _ = mimetypes.guess_type(f)
        if mtype is None:
            logger.warning(f"unrecognized mime type {f}")
            continue

        mcategory, _ = mtype.split("/")

        if mcategory in ("sub", "font", "application", "image", "audio"):
            logger.debug("ignored file {f} {mtype=}")
            continue

        if mcategory != "video":
            logger.warning(f"unhandled file {f} {mtype=}")
            continue

        kara_data = parse_file(f)
        if kara_data is None:
            logger.warning(f"ignoring {f}")
            continue

        file_data[str(f)] = kara_data

    return file_data


def main_parse_dir(dir: Annotated[Path, typer.Argument(file_okay=False, dir_okay=True)]):
    print(json.dumps(parse_dir(dir)))


def main():
    typer.run(main_parse_dir)
