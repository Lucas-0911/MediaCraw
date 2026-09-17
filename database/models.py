# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

# Privacy: do not persist identifiable creator fields (user id, IP location,
# avatar, profile URL, bio, gender). Extractors hash raw user ids to
# creator_hash and mask nicknames. Creator profile tables were removed.

from sqlalchemy import create_engine, Column, Integer, Text, String, BigInteger
from sqlalchemy.types import Float as _SqlFloat
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class BilibiliVideo(Base):
    __tablename__ = 'bilibili_video'
    id = Column(Integer, primary_key=True, comment='Primary key')
    video_id = Column(String(64), nullable=False, index=True, unique=True, comment='Video ID')
    video_url = Column(Text, nullable=False, comment='Video URL')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    nickname = Column(Text, comment='Masked nickname')
    liked_count = Column(Integer, comment='Like count')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
    video_type = Column(Text, comment='Video type')
    title = Column(Text, comment='Video title')
    desc = Column(Text, comment='Video description')
    create_time = Column(BigInteger, index=True, comment='Created timestamp')
    disliked_count = Column(Text, comment='Dislike count')
    video_play_count = Column(Text, comment='Play count')
    video_favorite_count = Column(Text, comment='Favorite count')
    video_share_count = Column(Text, comment='Share count')
    video_coin_count = Column(Text, comment='Coin count')
    video_danmaku = Column(Text, comment='Danmaku count')
    video_comment = Column(Text, comment='Comment count')
    video_cover_url = Column(Text, comment='Cover URL')
    source_keyword = Column(Text, default='', comment='Source keyword')

class BilibiliVideoComment(Base):
    __tablename__ = 'bilibili_video_comment'
    id = Column(Integer, primary_key=True, comment='Primary key')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    nickname = Column(Text, comment='Masked nickname')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
    comment_id = Column(String(128), index=True, comment='Comment ID')
    video_id = Column(String(64), index=True, comment='Video ID')
    content = Column(Text, comment='Comment content')
    create_time = Column(BigInteger, comment='Created timestamp')
    sub_comment_count = Column(Text, comment='Sub-comment count')
    parent_comment_id = Column(String(255), comment='Parent comment ID')
    like_count = Column(Text, default='0', comment='Like count')

class BilibiliUpDynamic(Base):
    __tablename__ = 'bilibili_up_dynamic'
    id = Column(Integer, primary_key=True, comment='Primary key')
    dynamic_id = Column(String(128), index=True, comment='Dynamic ID')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    user_name = Column(Text, comment='Masked user name')
    text = Column(Text, comment='Dynamic content')
    type = Column(Text, comment='Dynamic type')
    pub_ts = Column(BigInteger, comment='Publish timestamp')
    total_comments = Column(Integer, comment='Total comments')
    total_forwards = Column(Integer, comment='Total forwards')
    total_liked = Column(Integer, comment='Total likes')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')

class DouyinAweme(Base):
    __tablename__ = 'douyin_aweme'
    id = Column(Integer, primary_key=True, comment='Primary key')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    nickname = Column(Text, comment='Masked nickname')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
    aweme_id = Column(String(255), index=True, comment='Item ID')
    aweme_type = Column(Text, comment='Item type')
    title = Column(Text, comment='Item title')
    desc = Column(Text, comment='Item description')
    create_time = Column(BigInteger, index=True, comment='Created timestamp')
    liked_count = Column(Text, comment='Like count')
    comment_count = Column(Text, comment='Comment count')
    share_count = Column(Text, comment='Share count')
    collected_count = Column(Text, comment='Favorite count')
    aweme_url = Column(Text, comment='Item URL')
    cover_url = Column(Text, comment='Cover URL')
    video_download_url = Column(Text, comment='Video download URL')
    music_download_url = Column(Text, comment='Music download URL')
    note_download_url = Column(Text, comment='Note download URL')
    source_keyword = Column(Text, default='', comment='Source keyword')

class DouyinAwemeComment(Base):
    __tablename__ = 'douyin_aweme_comment'
    id = Column(Integer, primary_key=True, comment='Primary key')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    nickname = Column(Text, comment='Masked nickname')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
    comment_id = Column(String(255), index=True, comment='Comment ID')
    aweme_id = Column(String(255), index=True, comment='Item ID')
    content = Column(Text, comment='Comment content')
    create_time = Column(BigInteger, comment='Created timestamp')
    sub_comment_count = Column(Text, comment='Sub-comment count')
    parent_comment_id = Column(String(255), comment='Parent comment ID')
    like_count = Column(Text, default='0', comment='Like count')
    pictures = Column(Text, default='', comment='Images')

class KuaishouVideo(Base):
    __tablename__ = 'kuaishou_video'
    id = Column(Integer, primary_key=True, comment='Primary key')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    nickname = Column(Text, comment='Masked nickname')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
    video_id = Column(String(255), index=True, comment='Video ID')
    video_type = Column(Text, comment='Video type')
    title = Column(Text, comment='Video title')
    desc = Column(Text, comment='Video description')
    create_time = Column(BigInteger, index=True, comment='Created timestamp')
    liked_count = Column(Text, comment='Like count')
    viewd_count = Column(Text, comment='View count')
    video_url = Column(Text, comment='Video URL')
    video_cover_url = Column(Text, comment='Cover URL')
    video_play_url = Column(Text, comment='Playback URL')
    source_keyword = Column(Text, default='', comment='Source keyword')

class KuaishouVideoComment(Base):
    __tablename__ = 'kuaishou_video_comment'
    id = Column(Integer, primary_key=True, comment='Primary key')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    nickname = Column(Text, comment='Masked nickname')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
    comment_id = Column(String(255), index=True, comment='Comment ID')
    video_id = Column(String(255), index=True, comment='Video ID')
    content = Column(Text, comment='Comment content')
    create_time = Column(BigInteger, comment='Created timestamp')
    sub_comment_count = Column(Text, comment='Sub-comment count')

class WeiboNote(Base):
    __tablename__ = 'weibo_note'
    id = Column(Integer, primary_key=True, comment='Primary key')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    nickname = Column(Text, comment='Masked nickname')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
    note_id = Column(String(64), index=True, comment='Note ID')
    content = Column(Text, comment='Note content')
    create_time = Column(BigInteger, index=True, comment='Created timestamp')
    create_date_time = Column(String(255), index=True, comment='Created datetime')
    liked_count = Column(Text, comment='Like count')
    comments_count = Column(Text, comment='Comment count')
    shared_count = Column(Text, comment='Share count')
    note_url = Column(Text, comment='Note URL')
    source_keyword = Column(Text, default='', comment='Source keyword')

class WeiboNoteComment(Base):
    __tablename__ = 'weibo_note_comment'
    id = Column(Integer, primary_key=True, comment='Primary key')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    nickname = Column(Text, comment='Masked nickname')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
    comment_id = Column(String(64), index=True, comment='Comment ID')
    note_id = Column(String(64), index=True, comment='Note ID')
    content = Column(Text, comment='Comment content')
    create_time = Column(BigInteger, comment='Created timestamp')
    create_date_time = Column(String(255), index=True, comment='Created datetime')
    comment_like_count = Column(Text, comment='Comment like count')
    sub_comment_count = Column(Text, comment='Sub-comment count')
    parent_comment_id = Column(String(255), comment='Parent comment ID')

class XhsNote(Base):
    __tablename__ = 'xhs_note'
    id = Column(Integer, primary_key=True, comment='Primary key')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    nickname = Column(Text, comment='Masked nickname')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
    note_id = Column(String(255), index=True, comment='Note ID')
    type = Column(Text, comment='Note type')
    title = Column(Text, comment='Note title')
    desc = Column(Text, comment='Note description')
    video_url = Column(Text, comment='Video URL')
    time = Column(BigInteger, index=True, comment='Timestamp')
    last_update_time = Column(BigInteger, comment='Last update timestamp')
    liked_count = Column(Text, comment='Like count')
    collected_count = Column(Text, comment='Favorite count')
    comment_count = Column(Text, comment='Comment count')
    share_count = Column(Text, comment='Share count')
    image_list = Column(Text, comment='Image list')
    tag_list = Column(Text, comment='Tag list')
    note_url = Column(Text, comment='Note URL')
    source_keyword = Column(Text, default='', comment='Source keyword')
    xsec_token = Column(Text, comment='Xsec Token')

class XhsNoteComment(Base):
    __tablename__ = 'xhs_note_comment'
    id = Column(Integer, primary_key=True, comment='Primary key')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    nickname = Column(Text, comment='Masked nickname')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
    comment_id = Column(String(255), index=True, comment='Comment ID')
    create_time = Column(BigInteger, index=True, comment='Created timestamp')
    note_id = Column(String(255), comment='Note ID')
    content = Column(Text, comment='Comment content')
    sub_comment_count = Column(Integer, comment='Sub-comment count')
    pictures = Column(Text, comment='Images')
    parent_comment_id = Column(String(255), comment='Parent comment ID')
    like_count = Column(Text, comment='Like count')

class TiebaNote(Base):
    __tablename__ = 'tieba_note'
    id = Column(Integer, primary_key=True, comment='Primary key')
    note_id = Column(String(644), index=True, comment='Note ID')
    title = Column(Text, comment='Note title')
    desc = Column(Text, comment='Note description')
    note_url = Column(Text, comment='Note URL')
    publish_time = Column(String(255), index=True, comment='Publish time')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    user_nickname = Column(Text, default='', comment='Masked nickname')
    tieba_id = Column(String(255), default='', comment='Tieba ID')
    tieba_name = Column(Text, comment='Tieba name')
    tieba_link = Column(Text, comment='Tieba URL')
    total_replay_num = Column(Integer, default=0, comment='Total replies')
    total_replay_page = Column(Integer, default=0, comment='Total reply pages')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
    source_keyword = Column(Text, default='', comment='Source keyword')

class TiebaComment(Base):
    __tablename__ = 'tieba_comment'
    id = Column(Integer, primary_key=True, comment='Primary key')
    comment_id = Column(String(255), index=True, comment='Comment ID')
    parent_comment_id = Column(String(255), default='', comment='Parent comment ID')
    content = Column(Text, comment='Comment content')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    user_nickname = Column(Text, default='', comment='Masked nickname')
    tieba_id = Column(String(255), default='', comment='Tieba ID')
    tieba_name = Column(Text, comment='Tieba name')
    tieba_link = Column(Text, comment='Tieba URL')
    publish_time = Column(String(255), index=True, comment='Publish time')
    sub_comment_count = Column(Integer, default=0, comment='Sub-comment count')
    note_id = Column(String(255), index=True, comment='Note ID')
    note_url = Column(Text, comment='Note URL')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')

class ZhihuContent(Base):
    __tablename__ = 'zhihu_content'
    id = Column(Integer, primary_key=True, comment='Primary key')
    content_id = Column(String(64), index=True, comment='Content ID')
    content_type = Column(Text, comment='Content type')
    content_text = Column(Text, comment='Content text')
    content_url = Column(Text, comment='Content URL')
    question_id = Column(String(255), comment='Question ID')
    title = Column(Text, comment='Title')
    desc = Column(Text, comment='Description')
    created_time = Column(String(32), index=True, comment='Created time')
    updated_time = Column(Text, comment='Updated time')
    voteup_count = Column(Integer, default=0, comment='Upvote count')
    comment_count = Column(Integer, default=0, comment='Comment count')
    source_keyword = Column(Text, comment='Source keyword')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    user_nickname = Column(Text, comment='Masked nickname')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')

class TiktokAweme(Base):
    __tablename__ = 'tiktok_aweme'
    id = Column(Integer, primary_key=True, comment='Primary key')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    nickname = Column(Text, comment='Masked nickname')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
    aweme_id = Column(String(255), index=True, comment='Item ID')
    aweme_type = Column(Text, comment='Item type')
    title = Column(Text, comment='Item title')
    desc = Column(Text, comment='Item description')
    create_time = Column(BigInteger, index=True, comment='Created timestamp')
    liked_count = Column(Text, comment='Like count')
    comment_count = Column(Text, comment='Comment count')
    share_count = Column(Text, comment='Share count')
    collected_count = Column(Text, comment='Favorite count')
    aweme_url = Column(Text, comment='Item URL')
    cover_url = Column(Text, comment='Cover URL')
    video_download_url = Column(Text, comment='Video download URL')
    music_download_url = Column(Text, comment='Music download URL')
    note_download_url = Column(Text, comment='Note download URL')
    source_keyword = Column(Text, default='', comment='Source keyword')

class TiktokAwemeComment(Base):
    __tablename__ = 'tiktok_aweme_comment'
    id = Column(Integer, primary_key=True, comment='Primary key')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    nickname = Column(Text, comment='Masked nickname')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
    comment_id = Column(String(255), index=True, comment='Comment ID')
    aweme_id = Column(String(255), index=True, comment='Item ID')
    content = Column(Text, comment='Comment content')
    create_time = Column(BigInteger, comment='Created timestamp')
    sub_comment_count = Column(Text, comment='Sub-comment count')
    parent_comment_id = Column(String(255), comment='Parent comment ID')
    like_count = Column(Text, default='0', comment='Like count')
    pictures = Column(Text, default='', comment='Images')

class TrendProduct(Base):
    __tablename__ = 'trend_product'
    id = Column(Integer, primary_key=True, comment='Primary key')
    product_key = Column(String(255), nullable=False, unique=True, index=True, comment='SP key')
    product_id = Column(String(255), index=True, comment='Product cart product_id')
    name = Column(Text, comment='Tên sản phẩm')
    identity_type = Column(String(64), comment='xiaohuangche/hashtag/llm')
    industry = Column(Text, comment='Keyword ngành')
    confidence = Column(Integer, default=0, comment='Confidence 0-5')
    heat_now = Column(_SqlFloat, default=0, comment='HeatNow')
    heat_delta = Column(_SqlFloat, default=0, comment='HeatDelta')
    label = Column(String(64), default='QUAN SAT', comment='Nhãn')
    gates_json = Column(Text, default='{}', comment='Cổng AND')
    last_alert_ts = Column(BigInteger, default=0, comment='Lần alert gần nhất')
    updated_ts = Column(BigInteger, comment='Cập nhật')


class TrendSnapshot(Base):
    __tablename__ = 'trend_snapshot'
    id = Column(Integer, primary_key=True, comment='Primary key')
    product_key = Column(String(255), index=True, comment='SP key')
    ts = Column(BigInteger, index=True, comment='Thời điểm snapshot')
    play_velocity = Column(_SqlFloat, comment='play/h')
    eng_velocity = Column(_SqlFloat, comment='eng/h')
    mention_n = Column(Integer, comment='Số video')
    spread = Column(Integer, comment='Số creator')
    intent_n = Column(Integer, comment='Comment mua')
    intent_wilson = Column(_SqlFloat, comment='Wilson intent')
    heat_now = Column(_SqlFloat, comment='HeatNow')
    search_cn = Column(String(32), comment='Google Trends CN')


class TrendVideo(Base):
    __tablename__ = 'trend_video'
    id = Column(Integer, primary_key=True, comment='Primary key')
    aweme_id = Column(String(255), index=True, comment='Video ID')
    platform = Column(String(32), index=True, comment='dy/tiktok')
    product_key = Column(String(255), index=True, comment='SP key')
    creator_hash = Column(String(64), comment='Creator hash')
    play_count = Column(Integer, default=0, comment='Play')
    like_count = Column(Integer, default=0, comment='Like')
    comment_count = Column(Integer, default=0, comment='Comment')
    share_count = Column(Integer, default=0, comment='Share')
    create_time = Column(BigInteger, comment='Thời điểm đăng')
    url = Column(Text, comment='URL video')
    download_url = Column(Text, comment='URL mp4')
    desc = Column(Text, comment='Mô tả')
    source_keyword = Column(Text, comment='Keyword')
    last_play_count = Column(Integer, default=0, comment='Play snapshot trước')
    local_media_path = Column(Text, comment='File mp4 local')
    updated_ts = Column(BigInteger, comment='Cập nhật')


class TrendAlert(Base):
    __tablename__ = 'trend_alert'
    id = Column(Integer, primary_key=True, comment='Primary key')
    product_key = Column(String(255), index=True, comment='SP key')
    ts = Column(BigInteger, comment='Thời điểm')
    confidence = Column(Integer, comment='Confidence')
    payload_json = Column(Text, comment='Nội dung Telegram')


class ZhihuComment(Base):
    __tablename__ = 'zhihu_comment'
    id = Column(Integer, primary_key=True, comment='Primary key')
    comment_id = Column(String(64), index=True, comment='Comment ID')
    parent_comment_id = Column(String(64), comment='Parent comment ID')
    content = Column(Text, comment='Comment content')
    publish_time = Column(String(32), index=True, comment='Publish time')
    sub_comment_count = Column(Integer, default=0, comment='Sub-comment count')
    like_count = Column(Integer, default=0, comment='Like count')
    dislike_count = Column(Integer, default=0, comment='Dislike count')
    content_id = Column(String(64), index=True, comment='Content ID')
    content_type = Column(Text, comment='Content type')
    creator_hash = Column(String(64), index=True, comment='Anonymized creator hash')
    user_nickname = Column(Text, comment='Masked nickname')
    add_ts = Column(BigInteger, comment='Created timestamp')
    last_modify_ts = Column(BigInteger, comment='Last modified timestamp')
