import json
import logging
from dataclasses import field
from pathlib import Path
from typing import Annotated, Literal, TypedDict

import pydantic
import typer
import yaml

import karawanko.wankoparse as wankoparse

logger = logging.getLogger(__name__)


artists: dict[str, int] = {}
medias: dict[str, int] = {}


class KaraInfo(TypedDict):
    title: str
    title_aliases: list[str]
    authors: list[str]
    artists: list[str]
    source_media: int
    song_order: int
    medias: list[int]
    audio_tags: list[str]
    video_tags: list[str]
    comment: str
    version: str

MTYPES = Literal["ANIME", "GAME", "LIVE", "CARTOON"]
media_type_map: dict[str, MTYPES] = {
    "anime": "ANIME",
    "game": "GAME",
    "live_action": "LIVE",
    "cartoon": "CARTOON",
}

audio_tag_map = {
    "INS": "INS",
    "LIVE": "LIVE",
    "COVER": "COVER",
    "IS": "IS",
}

anime_video_tag_map = {
    "AMV": "FANMADE",
    "NSFW": "NSFW",
    "SPOIL": "SPOILER",
}

known_unmapped_tags = "LONG", "FULL", "INST", "COURT", "PV", "REMIX"
known_unhandled_media_types = ("cartoon",)


class Media(pydantic.BaseModel):
    name: str
    mtype: MTYPES

    @classmethod
    def from_media_data(cls, media: wankoparse.MediaData):
        assert media["name"] is not None
        assert media["media_type"] is not None
        mtype = media_type_map[media["media_type"]]
        return cls(name=media["name"], mtype=mtype)


class KaraData(pydantic.BaseModel):
    title: str
    title_aliases: set[str] = field(default_factory=set)
    authors: list[str] = field(default_factory=list)
    artists: list[str] = field(default_factory=list)
    source_media: Media | None = None
    song_order: int = 0
    medias: list[int] = field(default_factory=list)
    audio_tags: list[str] = field(default_factory=list)
    video_tags: list[str] = field(default_factory=list)
    comment: str = ""
    version: str = ""


class WankoExport(pydantic.BaseModel):
    exported: dict[str, KaraData]


def anime_tag_map(tags: list[str], kara_data: KaraData):
    if "LONG" in tags:
        kara_data.version = "Long"
    if "FULL" in tags:
        kara_data.version = "Full"
    if "COURT" in tags:
        kara_data.version = "Short"

    for tag in tags:
        unmapped = True
        if tag.startswith("OP"):
            unmapped = False
            kara_data.song_order = int(tag[2:] or 0)
            kara_data.audio_tags.append("OP")
            if kara_data.version == "":
                kara_data.video_tags.append("OP")

        if tag.startswith("ED"):
            unmapped = False
            kara_data.song_order = int(tag[2:] or 0)
            kara_data.audio_tags.append("ED")
            if kara_data.version == "":
                kara_data.video_tags.append("ED")

        if tag in audio_tag_map:
            unmapped = False
            kara_data.audio_tags.append(audio_tag_map[tag])

        if tag in anime_video_tag_map:
            unmapped = False
            kara_data.video_tags.append(anime_video_tag_map[tag])

        if unmapped and tag not in known_unmapped_tags:
            raise RuntimeError(f"unmapped tag {tag}")


def wankoexport(dir: Annotated[Path, typer.Argument(file_okay=False, dir_okay=True)]):
    karas, pandora_box = wankoparse.parse_dir(dir)

    kara_export: dict[str, KaraData] = {}

    for kara_file, kara in karas.items():
        kara_data = KaraData(title=kara["title"])

        for artist in kara["artists"]:
            kara_data.artists.append(artist)

        media = kara["media"]
        if media is not None:
            kara_data.source_media = Media.from_media_data(media)

            if media["media_type"] in ("anime", "game", "live_action", "cartoon"):
                anime_tag_map(kara["tags"], kara_data)
            elif media["media_type"] in known_unhandled_media_types:
                pass
            else:
                raise RuntimeError(f"Unhandled media type {media["media_type"]}")

        kara_export[kara_file] = kara_data

    schema_url = "https://raw.githubusercontent.com/odrling/karawanko/master/wankoexport.schema.json"
    print(f"# yaml-language-server: $schema={schema_url}\n")

    export_data = WankoExport(exported=kara_export).model_dump()
    print(yaml.safe_dump(export_data))


def main():
    typer.run(wankoexport)


def json_schema():
    print(json.dumps(WankoExport.model_json_schema()))
