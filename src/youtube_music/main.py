import json
import time
from typing import Any

import schedule
from ytmusicapi import YTMusic

ytmusic = YTMusic("oauth.json")
PLAYLIST_ID: str = "PLaQdlWuYHujCV-TY97OG-21kzVAEW31vY"


def load_artist_order(json_file: str = "artist_order.json") -> list[str]:
    """アーティスト順をJSONから読み込む"""
    with open(json_file, "r", encoding="utf-8") as f:  # noqa: UP015
        data: dict[str, list[str]] = json.load(f)
    return data["artist_order"]


def sort_playlist_by_artist() -> None:
    """プレイリストをアーティスト順に並び替える"""
    artist_order = load_artist_order()
    playlist = ytmusic.get_playlist(PLAYLIST_ID)
    tracks = playlist["tracks"]

    def get_artist_order(track: dict[str, Any]) -> int:
        artist: str = track["artists"][0]["name"]
        return artist_order.index(artist) if artist in artist_order else len(artist_order)

    sorted_tracks = sorted(tracks, key=get_artist_order)
    track_ids: list[str] = [track["videoId"] for track in sorted_tracks]
    ytmusic.edit_playlist(PLAYLIST_ID, moveItemIds=track_ids)


def schedule_task() -> None:
    """タスクをスケジュールする"""
    schedule.every().day.at("10:00").do(sort_playlist_by_artist)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    sort_playlist_by_artist()
    schedule_task()
