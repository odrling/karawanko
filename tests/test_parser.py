import unittest
from pathlib import Path

from karawanko.wankoparse import Details, KaraData, parse_file

file_tests: list[tuple[str, KaraData | None]] = [
    (
        "Wmusic/Electric Light Orchestra - AMV - Twilight (AMV Daicon Opening Animations).mp4",
        {
            "title": "Twilight",
            "tags": ["AMV"],
            "media": None,
            "details": [Details("AMV", "Daicon Opening Animations")],
            "artists": ["Electric Light Orchestra"],
            "language": "",
            "pandora_box": False,
        },
    ),
    (
        "Nouveau/Xenoblade Chronicles - ED SPOIL - Beyond the sky (VERS Japanese - VIDEO Ending).mp4",
        {
            "title": "Beyond the sky",
            "tags": ["ED", "SPOIL"],
            "media": {"name": "Xenoblade Chronicles", "media_type": "game"},
            "artists": [],
            "details": [Details("VERS", "Japanese"), Details("VIDEO", "Ending")],
            "language": "",
            "pandora_box": True,
        },
    ),
    (
        "CJKmusic/GUMI, IA, Luka Megurine - PV - Ifuudoudou.mp4",
        {
            "title": "Ifuudoudou",
            "tags": ["PV"],
            "media": None,
            "artists": ["GUMI", "IA", "Luka Megurine"],
            "details": [],
            "language": "",
            "pandora_box": False,
        },
    ),
    (
        "CJKmusic/Camellia, U.Z. INU feat. Houshou Marine - PV NSFW - I’m Your Treasure Box ＊Anata wa Marine Senchou Otakarabako Kara Mitsuketa..mp4",  # noqa: E501
        {
            "title": "I’m Your Treasure Box ＊Anata wa Marine Senchou Otakarabako Kara Mitsuketa.",
            "tags": ["PV", "NSFW"],
            "media": None,
            "artists": ["Camellia", "U.Z. INU", "Houshou Marine"],
            "details": [],
            "language": "",
            "pandora_box": False,
        },
    ),
    (
        "base/Mugen/CJKmusic/Arai Yumi - PV - Hikoukigumo (AMV Kaze Tachinu - AMV Le Vent se lève).mp4",
        {
            "title": "Hikoukigumo",
            "tags": ["PV"],
            "media": None,
            "artists": ["Arai Yumi"],
            "details": [Details("AMV", "Kaze Tachinu"), Details("AMV", "Le Vent se lève")],
            "language": "",
            "pandora_box": False,
        },
    ),
    (
        "Anime/Yamada-kun to 7-nin no Majo (TV) - OP - Kuchizuke Diamond.mkv",
        {
            "title": "Kuchizuke Diamond",
            "tags": ["OP"],
            "media": {"name": "Yamada-kun to 7-nin no Majo (TV)", "media_type": "anime"},
            "artists": [],
            "details": [],
            "language": "",
            "pandora_box": False,
        },
    ),
    (
        "Nouveau/Mili - PV - world.execute(me);.mkv",
        {
            "title": "world.execute(me);",
            "artists": ["Mili"],
            "media": None,
            "tags": ["PV"],
            "details": [],
            "language": "",
            "pandora_box": True,
        },
    ),
    (
        "Nouveau/BIRDIE WING Golf Girls' Story - OP - Venus Line.mp4",
        {
            "title": "Venus Line",
            "artists": [],
            "media": {"name": "BIRDIE WING Golf Girls' Story", "media_type": "anime"},
            "tags": ["OP"],
            "details": [],
            "language": "",
            "pandora_box": True,
        },
    ),
    (
        "base/Japan7/Nouveau/Aqours - LIVE - Kimi no Hitomi o Meguru Bouken (VIDEO Love Live! Sunshine!! Aqours 5th LoveLive! ～Next SPARKLING!!～ Day 1).mp4",  # noqa: E501
        {
            "title": "Kimi no Hitomi o Meguru Bouken",
            "tags": ["LIVE"],
            "artists": ["Aqours"],
            "media": None,
            "details": [Details("VIDEO", "Love Live! Sunshine!! Aqours 5th LoveLive! ～Next SPARKLING!!～ Day 1")],
            "language": "",
            "pandora_box": True,
        },
    ),
    (
        "base/Japan7/Nouveau/Aimer, Lilas Ikuta, milet - PV LIVE - Omokage.mkv",
        {
            "title": "Omokage",
            "tags": ["PV", "LIVE"],
            "artists": ["Aimer", "Lilas Ikuta", "milet"],
            "media": None,
            "details": [],
            "language": "",
            "pandora_box": True,
        },
    ),
    ("Cardcaptor Sakura ~ Clear Card-hen Prologue - Sakura to Futatsu no Kuma - ED - Yakusoku no Sora.mkv", None),
    (
        "base/Japan7/CJKmusic/(G)I-DLE - PV - HANN(Alone).mp4",
        {
            "title": "HANN(Alone)",
            "tags": ["PV"],
            "artists": ["(G)I-DLE"],
            "media": None,
            "details": [],
            "language": "",
            "pandora_box": False,
        },
    ),
    (
        "CJKmusic/Yousei Teikoku - AMV - Tamakui (INS Ga-Rei Zero - AMV Project Zero).mkv",
        {
            "title": "Tamakui",
            "tags": ["AMV"],
            "artists": ["Yousei Teikoku"],
            "media": None,
            "details": [Details("INS", "Ga-Rei Zero"), Details("AMV", "Project Zero")],
            "language": "",
            "pandora_box": False,
        },
    ),
    (
        "base/Japan7/Dessin animé/Chevaliers du Zodiaque (les) - OP2 - FR - L'Aventure est sur ton chemin.avi",
        {
            "title": "L'Aventure est sur ton chemin",
            "tags": ["OP2"],
            "artists": [],
            "media": {"name": "Chevaliers du Zodiaque (les)", "media_type": "cartoon"},
            "details": [],
            "language": "FR",
            "pandora_box": True,
        },
    ),
    (
        "base/Japan7/Dessin animé/Galaxy Express 999 - OP - FR.avi",
        {
            "title": "Galaxy Express 999",
            "tags": ["OP"],
            "artists": [],
            "media": {"name": "Galaxy Express 999", "media_type": "cartoon"},
            "details": [],
            "language": "FR",
            "pandora_box": True,
        },
    ),
    (
        "base/Japan7/Nouveau/Boku no Hero Academia 4th Season - ED2 - Shout Baby.mkv",
        {
            "title": "Shout Baby",
            "tags": ["ED2"],
            "artists": [],
            "media": {"name": "Boku no Hero Academia 4th Season", "media_type": "anime"},
            "details": [],
            "language": "",
            "pandora_box": True,
        }
    )
]


class ParserTestCase(unittest.TestCase):
    def test_parse(self):
        for filepath, expected in file_tests:
            file = Path(filepath)
            with self.subTest(file=file, expected=expected):
                parsed = parse_file(file)
                self.assertEqual(parsed, expected)


if __name__ == "__main__":
    unittest.main()
