import json
import logging
import time
import traceback
from pathlib import Path
from typing import Any, Optional

import schedule
from ytmusicapi import YTMusic
from ytmusicapi.exceptions import YTMusicServerError

# ロガーの設定
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class PlaylistSorter:
    def __init__(self, oauth_file: str = "oauth.json", playlist_id: Optional[str] = None) -> None:
        self.oauth_file = oauth_file
        self.playlist_id = playlist_id
        self.ytmusic: Optional[YTMusic] = None

    def initialize(self) -> bool:
        """YouTube Music APIの初期化とバリデーション"""
        try:
            # oauth.jsonファイルの存在確認
            if not Path(self.oauth_file).exists():
                logger.error(f"認証ファイルが見つかりません: {self.oauth_file!s}")
                return False

            # YouTube Music APIクライアントの初期化
            self.ytmusic = YTMusic(self.oauth_file)
            logger.debug("YTMusic インスタンスを作成しました")

            # プレイリストIDの検証
            if not self.playlist_id:
                logger.error("プレイリストIDが設定されていません")
                return False

            # プレイリストの存在確認
            try:
                if self.ytmusic is not None:
                    playlist = self.ytmusic.get_playlist(self.playlist_id)
                    logger.debug(f"プレイリスト情報を取得しました: {playlist.get('title', 'Unknown')!s}")
                logger.info("初期化成功: YouTube Music APIに接続しました")
                return True
            except YTMusicServerError as e:
                logger.error(f"無効なプレイリストID: {self.playlist_id!s}")
                logger.error(f"エラー詳細: {e!s}")
                return False

        except Exception as e:
            logger.error(f"初期化中にエラーが発生しました: {e!s}")
            logger.error(f"トレースバック:\n{traceback.format_exc()}")
            return False

    def load_artist_order(self, json_file: str = "artist_order.json") -> list[str]:
        """アーティスト順をJSONから読み込む"""
        try:
            if not Path(json_file).exists():
                logger.error(f"アーティスト順ファイルが見つかりません: {json_file!s}")
                return []

            with open(json_file, encoding="utf-8") as f:
                data: dict[str, list[str]] = json.load(f)

            artist_order = data.get("artist_order", [])
            if not artist_order:
                logger.warning("アーティスト順が空です")
            else:
                logger.debug(f"アーティスト順を読み込みました: {len(artist_order)} アーティスト")
            return artist_order

        except json.JSONDecodeError:
            logger.error(f"JSONファイルの形式が不正です: {json_file!s}")
            return []
        except Exception as e:
            logger.error(f"アーティスト順の読み込み中にエラーが発生しました: {e!s}")
            logger.error(f"トレースバック:\n{traceback.format_exc()}")
            return []

    def get_artist_name(self, track: dict[str, Any]) -> str:
        """トラックからアーティスト名を取得する"""
        try:
            return track["artists"][0]["name"]
        except (KeyError, IndexError):
            logger.warning(f"トラックのアーティスト情報が不正です: {track.get('title', 'Unknown')!s}")
            return "Unknown Artist"

    def sort_playlist_by_artist(self) -> bool:
        """プレイリストをアーティスト順に並び替える"""
        if self.ytmusic is None:
            logger.error("YouTube Music APIが初期化されていません")
            return False

        try:
            # アーティスト順の読み込み
            artist_order = self.load_artist_order()
            if not artist_order:
                return False

            # プレイリストの取得
            playlist = self.ytmusic.get_playlist(self.playlist_id)
            if not playlist.get("tracks"):
                logger.warning("プレイリストが空です")
                return False

            tracks = playlist["tracks"]
            logger.debug(f"プレイリストから {len(tracks)} トラックを取得しました")

            # 設定されたアーティスト順とそれ以外で分類
            prioritized_tracks: list[tuple[int, str, dict]] = []  # (index, artist_name, track)
            other_tracks: list[tuple[str, dict]] = []  # (artist_name, track)

            for track in tracks:
                artist = self.get_artist_name(track)
                if artist in artist_order:
                    prioritized_tracks.append((artist_order.index(artist), artist, track))
                else:
                    other_tracks.append((artist, track))

            # それぞれをソート
            prioritized_tracks.sort(
                key=lambda x: (x[0], x[1])
            )  # インデックス順、同じインデックスの場合はアーティスト名でソート
            other_tracks.sort(key=lambda x: x[0])  # アーティスト名でソート

            # ソートされたトラックリストを作成
            sorted_tracks = [track for _, _, track in prioritized_tracks]
            sorted_tracks.extend(track for _, track in other_tracks)

            # プレイリストの更新
            try:
                # すべてのトラックの削除
                for track in tracks:
                    # setVideoIdがない場合はplaylistItemIdを使用
                    item_id = track.get("playlistItemId", track.get("setVideoId"))
                    if item_id:
                        self.ytmusic.remove_playlist_items(self.playlist_id, [item_id])
                        time.sleep(0.5)  # APIレート制限を避けるための遅延
                    else:
                        logger.warning(f"トラック削除をスキップ: ID不明 - {track.get('title', 'Unknown')}")

                # ソートされたトラックの追加
                for track in sorted_tracks:
                    video_id = track.get("videoId")
                    if video_id:
                        self.ytmusic.add_playlist_items(self.playlist_id, [video_id])
                        time.sleep(0.5)  # APIレート制限を避けるための遅延
                    else:
                        logger.warning(
                            f"トラック追加をスキップ: videoId不明 - {track.get('title', 'Unknown')}"
                        )

                logger.info("プレイリストの並び替えが完了しました")
                return True

            except Exception as e:
                logger.error(f"プレイリストの更新中にエラーが発生しました: {e!s}")
                return False

        except Exception as e:
            logger.error(f"プレイリストの並び替え中にエラーが発生しました: {e!s}")
            logger.error(f"トレースバック:\n{traceback.format_exc()}")
            return False


def main() -> None:
    """メイン関数"""
    # プレイリストIDの設定
    PLAYLIST_ID = "PLaQdlWuYHujCV-TY97OG-21kzVAEW31vY"

    # PlaylistSorterの初期化
    sorter = PlaylistSorter(playlist_id=PLAYLIST_ID, oauth_file="browser.json")

    if not sorter.initialize():
        logger.error("初期化に失敗しました。プログラムを終了します。")
        return

    # 初回実行
    sorter.sort_playlist_by_artist()

    # スケジュール設定 - インスタンスメソッドを正しく参照
    schedule.every().day.at("10:00").do(sorter.sort_playlist_by_artist)

    logger.info("スケジューラーを開始しました")
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("プログラムを終了します")
            break
        except Exception as e:
            logger.error(f"予期せぬエラーが発生しました: {e!s}")
            logger.error(f"トレースバック:\n{traceback.format_exc()}")
            time.sleep(60)  # エラー時は1分待機してから再試行


if __name__ == "__main__":
    main()
