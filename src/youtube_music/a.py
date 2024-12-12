import json

from ytmusicapi import YTMusic

ytmusic = YTMusic("browser.json")
playlist = ytmusic.get_playlist("PLfujCgMH_oyD8p3kQC7f1_ZiFPj8J1I7N")
print(json.dumps(playlist.get("tracks", [{}]), indent=2))
