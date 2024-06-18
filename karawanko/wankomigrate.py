import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Literal, TypedDict

import requests
import typer

import karawanko.wankoparse as wankoparse

logger = logging.getLogger(__name__)


artists: dict[str, int] = {}
medias: dict[str, int] = {}


class KaraberusClient:
    def __init__(self, server: str, token: str):
        self.server = server
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def endpoint(self, path: str):
        return f"{self.server}{path}"

    def create_artist(self, name: str):
        endpoint = self.endpoint("/api/tags/artist")
        body = {"name": name, "additional_names": []}

        if name not in artists:
            with self.session.post(endpoint, json=body) as resp:
                data = resp.json()
                try:
                    artists[name] = data["artist"]["ID"]
                except KeyError:
                    logger.info(f"POST {endpoint} got: {data}")
                    artists[name] = self.find_artist(name)

        return artists[name]

    def find_artist(self, name: str):
        endpoint = self.endpoint("/api/tags/artist")

        if name not in artists:
            with self.session.get(endpoint, params={"name": name}) as resp:
                data = resp.json()
                artists[name] = data["artist"]["ID"]

        return artists[name]

    def create_media(self, name: str, media_type: str):
        endpoint = self.endpoint("/api/tags/media")
        karaberus_media_type = media_type_map[media_type]
        body = {
            "name": name,
            "media_type": karaberus_media_type,
            "additional_names": [],
        }

        if name not in medias:
            with self.session.post(endpoint, json=body) as resp:
                data = resp.json()
                try:
                    medias[name] = data["media"]["ID"]
                except KeyError:
                    logger.info(f"POST {endpoint} got: {data}")
                    medias[name] = self.find_media(name, karaberus_media_type)

        return medias[name]

    def find_media(self, name: str, media_type: str):
        endpoint = self.endpoint("/api/tags/media")

        if name not in medias:
            with self.session.get(endpoint, params={"name": name}) as resp:
                data = resp.json()
                medias[name] = data["media"]["ID"]

        return medias[name]


class KaraInfo(TypedDict):
    title: str
    title_aliases: list[str]
    authors: list[int]
    artists: list[int]
    source_media: int
    song_order: int
    medias: list[int]
    audio_tags: list[str]
    video_tags: list[str]
    comment: str
    version: str


media_type_map = {
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
known_unhandled_media_types = "cartoon",


@dataclass
class KaraData:
    title: str = ""
    title_aliases: set[str] = field(default_factory=set)
    authors: set[int] = field(default_factory=set)
    artists: set[int] = field(default_factory=set)
    source_media: int = 0
    song_order: int = 0
    medias: set[int] = field(default_factory=set)
    audio_tags: set[str] = field(default_factory=set)
    video_tags: set[str] = field(default_factory=set)
    comment: str = ""
    version: str = ""


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
            kara_data.audio_tags.add("OP")
            if kara_data.version == "":
                kara_data.video_tags.add("OP")

        if tag.startswith("ED"):
            unmapped = False
            kara_data.song_order = int(tag[2:] or 0)
            kara_data.audio_tags.add("ED")
            if kara_data.version == "":
                kara_data.video_tags.add("ED")

        if tag in audio_tag_map:
            unmapped = False
            kara_data.audio_tags.add(audio_tag_map[tag])

        if tag in anime_video_tag_map:
            unmapped = False
            kara_data.video_tags.add(anime_video_tag_map[tag])

        if unmapped and tag not in known_unmapped_tags:
            raise RuntimeError(f"unmapped tag {tag}")


def wankomigrate(dir: Annotated[Path, typer.Argument(file_okay=False, dir_okay=True)], server: str, token: str):
    karas = wankoparse.parse_dir(dir)

    client = KaraberusClient(server, token)

    for kara_file, kara in karas.items():
        kara_data = KaraData()
        kara_data.title = kara["title"]

        for artist in kara["artists"]:
            kara_data.artists.add(client.create_artist(artist))

        media = kara["media"]
        if media is not None:
            assert media["name"] is not None
            assert media["media_type"] is not None
            kara_data.source_media = client.create_media(media["name"], media["media_type"])

            if media["media_type"] in ("anime", "game", "live_action"):
                anime_tag_map(kara["tags"], kara_data)
            elif media["media_type"] in known_unhandled_media_types:
                pass
            else:
                raise RuntimeError(f"Unhandled media type {media["media_type"]}")


def main():
    typer.run(wankomigrate)
