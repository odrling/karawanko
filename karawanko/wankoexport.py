import json
import logging
from pathlib import Path
from typing import Annotated, Literal

import pydantic
import typer
import yaml

import karawanko.wankoparse as wankoparse

logger = logging.getLogger(__name__)


artists: dict[str, int] = {}
medias: dict[str, int] = {}


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

video_tag_map = {
    "AMV": ["FANMADE", "MV"],
    "PV": ["MV"],
    "NSFW": ["NSFW"],
    "SPOIL": ["SPOILER"],
    "LIVE": ["CONCERT"],  # most likely
    "REMIX": ["REMIX"],
}

known_unmapped_tags = "LONG", "FULL", "INST", "COURT", "SHORT"
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
    title_aliases: list[str] = pydantic.Field(default_factory=list)
    authors: list[str] = pydantic.Field(default_factory=list)
    artists: list[str] = pydantic.Field(default_factory=list)
    source_media: Media | None = None
    song_order: int = 0
    medias: list[Media] = pydantic.Field(default_factory=list)
    audio_tags: list[str] = pydantic.Field(default_factory=list)
    video_tags: list[str] = pydantic.Field(default_factory=list)
    comment: str = ""
    version: str = ""
    language: str = ""


class WankoExport(pydantic.BaseModel):
    exported: dict[str, KaraData]
    pandora_box: dict[str, KaraData]


def tag_map(tags: list[str], kara_data: KaraData):
    if "LONG" in tags:
        kara_data.version = "Long"
    if "FULL" in tags:
        kara_data.version = "Full"
    if "COURT" in tags or "SHORT" in tags:
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

        if tag in video_tag_map:
            unmapped = False
            kara_data.video_tags.extend(video_tag_map[tag])

        if unmapped and tag not in known_unmapped_tags:
            raise RuntimeError(f"unmapped tag {tag}")


def details_map(details: list[wankoparse.Details], kara: KaraData):
    for detail in details:
        kind, value = detail
        if kind == "comment":
            kara.comment += value
            continue

        if kind in ("OARTIST", "ARTIST"):
            kara.artists.append(value)
            continue

        if kind == "AMV":
            assert "FANMADE" in kara.video_tags, f"{details=}: FANMADE not in {kara.video_tags=}"
            assert "MV" in kara.video_tags, f"{details=}: MV not in {kara.video_tags=}"
            mtype = "ANIME" if wankoparse.is_anime(value) else "GAME"
            kara.medias.append(Media(name=value, mtype=mtype))
            continue

        if kind == "VERS":
            kara.version += f"{value} "
            continue

        if kind == "EP":
            kara.version += f"Episode {value} "
            continue

        if kind == "VIDEO":
            kara.comment += f"source video: {value}\n"
            continue

        if kind.startswith("OP") or kind.startswith("ED"):
            if len(kind) > 2:
                kara.song_order = int(kind[2:])
            kara.audio_tags.append(kind[:2])
            mtype = "ANIME" if wankoparse.is_anime(value) else "GAME"
            kara.source_media = Media(name=value, mtype=mtype)
            continue

        if kind == "INS":
            kara.audio_tags.append("INS")
            mtype = "ANIME" if wankoparse.is_anime(value) else "GAME"
            kara.source_media = Media(name=value, mtype=mtype)
            continue

        if kind == "VTITLE":
            kara.title_aliases.append(value)
            continue

        raise RuntimeError(f"failed to map detail: {detail}")

    kara.comment.strip()


def wankoexport(dir: Annotated[Path, typer.Argument(file_okay=False, dir_okay=True)]):
    karas = wankoparse.parse_dir(dir)

    kara_export: dict[str, KaraData] = {}
    pandora_box_data: dict[str, KaraData] = {}

    for kara_file, kara in karas.items():
        if kara is None:
            pandora_box_data[kara_file] = KaraData(title=Path(kara_file).stem)
            continue

        kara_data = KaraData(title=kara["title"], language=kara["language"])

        for artist in kara["artists"]:
            kara_data.artists.append(artist)

        media = kara["media"]
        if media is not None:
            kara_data.source_media = Media.from_media_data(media)

        try:
            tag_map(kara["tags"], kara_data)
            details_map(kara["details"], kara_data)

            if kara["pandora_box"]:
                pandora_box_data[kara_file] = kara_data
            else:
                kara_export[kara_file] = kara_data
        except Exception as e:
            raise RuntimeError(f"failed to export {kara_file}: {e}") from e

    schema_url = "https://raw.githubusercontent.com/odrling/karawanko/master/wankoexport.schema.json"
    print(f"# yaml-language-server: $schema={schema_url}\n")

    export_data = WankoExport(exported=kara_export, pandora_box=pandora_box_data).model_dump()
    print(yaml.safe_dump(export_data))


def main():
    typer.run(wankoexport)


def json_schema():
    print(json.dumps(WankoExport.model_json_schema()))
