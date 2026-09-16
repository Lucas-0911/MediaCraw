# -*- coding: utf-8 -*-
from media_platform.tiktok.help import (
    collect_comments_from_json,
    collect_items_from_search_json,
    normalize_tiktok_item,
    parse_creator_info_from_url,
    parse_universal_data,
    parse_video_info_from_url,
)


def test_parse_video_url_full():
    info = parse_video_info_from_url(
        "https://www.tiktok.com/@demo_user/video/7123456789012345678?lang=vi-VN"
    )
    assert info.aweme_id == "7123456789012345678"
    assert info.unique_id == "demo_user"
    assert info.url_type == "normal"


def test_parse_video_url_numeric():
    info = parse_video_info_from_url("7123456789012345678")
    assert info.aweme_id == "7123456789012345678"
    assert info.url_type == "id"


def test_parse_video_url_short():
    info = parse_video_info_from_url("https://vt.tiktok.com/ZSabcdef/")
    assert info.url_type == "short"


def test_parse_creator_url_and_handle():
    from_url = parse_creator_info_from_url("https://www.tiktok.com/@amthuc_vn")
    assert from_url.unique_id == "amthuc_vn"
    from_handle = parse_creator_info_from_url("@amthuc_vn")
    assert from_handle.unique_id == "amthuc_vn"


def test_normalize_tiktok_item():
    item = {
        "id": "111",
        "desc": "Phở Hà Nội",
        "createTime": 1700000000,
        "author": {"id": "99", "uniqueId": "pho_hn", "nickname": "Phở Hà Nội Official"},
        "stats": {"diggCount": 10, "commentCount": 2, "shareCount": 1, "collectCount": 3, "playCount": 100},
        "video": {"playAddr": "http://cdn/v.mp4", "cover": "http://cdn/c.jpg"},
    }
    out = normalize_tiktok_item(item)
    assert out["aweme_id"] == "111"
    assert out["desc"] == "Phở Hà Nội"
    assert out["author"]["uid"] == "99"
    assert out["statistics"]["digg_count"] == 10
    assert out["video"]["play_addr"]["url_list"] == ["http://cdn/v.mp4"]
    assert out["video"]["cover"] == "http://cdn/c.jpg"


def test_collect_items_from_search_json():
    payload = {
        "data": [
            {
                "item": {
                    "id": "222",
                    "desc": "Bún bò",
                    "author": {"id": "1", "uniqueId": "hue", "nickname": "Huế"},
                    "stats": {"diggCount": 1},
                    "video": {"playAddr": "http://x/a.mp4"},
                }
            }
        ]
    }
    items = collect_items_from_search_json(payload)
    assert len(items) == 1
    assert items[0]["aweme_id"] == "222"


def test_parse_universal_data_item_module():
    raw = '{"ItemModule":{"111":{"id":"111","desc":"x","author":{"id":"1","uniqueId":"u","nickname":"N"},"video":{"cover":"c"}}}}'
    items = parse_universal_data(raw)
    assert any(i["aweme_id"] == "111" for i in items)


def test_collect_comments_from_json():
    payload = {
        "comments": [
            {
                "cid": "c1",
                "text": "ngon quá",
                "create_time": 1,
                "digg_count": 4,
                "user": {"uid": "u1", "nickname": "An"},
            }
        ]
    }
    comments = collect_comments_from_json(payload, "111")
    assert comments[0]["cid"] == "c1"
    assert comments[0]["aweme_id"] == "111"
    assert comments[0]["text"] == "ngon quá"
