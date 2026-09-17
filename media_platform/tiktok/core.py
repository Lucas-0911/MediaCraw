# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""TikTok Vietnam crawler — Douyin-shaped plugin for tiktok.com (locale vi-VN)."""
from __future__ import annotations

import asyncio
import os
import random
from asyncio import Task
from typing import Any, Dict, List, Optional

from playwright.async_api import BrowserContext, BrowserType, Page, Playwright, async_playwright

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import tiktok as tiktok_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import TikTokClient
from .exception import DataFetchError
from .help import parse_creator_info_from_url, parse_video_info_from_url
from .login import TikTokLogin


class TikTokCrawler(AbstractCrawler):
    context_page: Page
    tt_client: TikTokClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.index_url = getattr(config, "TIKTOK_INDEX_URL", "https://www.tiktok.com").rstrip("/")
        self.cookie_urls = [
            "https://tiktok.com",
            self.index_url,
            "https://www.tiktok.com",
        ]
        self.cdp_manager = None
        self.ip_proxy_pool = None

    def _lang(self) -> str:
        return getattr(config, "TIKTOK_LANG", "vi")

    async def _prepare_context_page(self) -> Page:
        """Reuse a real Chrome tab. Playwright new_page() is often RST by TikTok."""
        pages = [p for p in self.browser_context.pages if not p.is_closed()]
        tiktok_pages = [p for p in pages if "tiktok.com" in (p.url or "").lower()]
        http_pages = [
            p for p in pages
            if (p.url or "").startswith("http") and not (p.url or "").startswith("chrome")
        ]
        if tiktok_pages:
            page = tiktok_pages[0]
            utils.logger.info(f"[TikTokCrawler] Dùng tab TikTok đang mở: {page.url}")
            return page

        page = http_pages[0] if http_pages else (pages[0] if pages else await self.browser_context.new_page())
        lang = self._lang()
        candidates = [
            f"{self.index_url}/",
            f"{self.index_url}/?lang={lang}",
            f"{self.index_url}/foryou",
            f"{self.index_url}/explore",
        ]
        for url in candidates:
            try:
                utils.logger.info(f"[TikTokCrawler] Thử mở {url} từ tab {page.url}")
                await page.goto(url, wait_until="commit", timeout=45000)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=20000)
                except Exception:
                    pass
                utils.logger.info(f"[TikTokCrawler] Đã mở {page.url}")
                return page
            except Exception as exc:
                utils.logger.warning(f"[TikTokCrawler] Không mở được {url}: {exc}")

        utils.logger.warning(
            "[TikTokCrawler] Không vào được www.tiktok.com (ERR_CONNECTION_RESET, không phải sai domain). "
            "Hãy tự mở https://www.tiktok.com trên Chrome đang debug port 9222 rồi chạy lại."
        )
        return page

    async def start(self) -> None:
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            self.ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await self.ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            extra_headers = {"Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"}
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[TikTokCrawler] Khởi động trình duyệt chế độ CDP")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    None,
                    headless=config.CDP_HEADLESS,
                )
            else:
                utils.logger.info("[TikTokCrawler] Khởi động trình duyệt chế độ chuẩn")
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    playwright_proxy_format,
                    user_agent=None,
                    headless=config.HEADLESS,
                )
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

            # Do not set extra headers on an existing CDP Chrome context — it applies to every tab
            # and can trigger connection resets on tiktok.com.
            if not config.ENABLE_CDP_MODE:
                await self.browser_context.set_extra_http_headers(extra_headers)
            self.context_page = await self._prepare_context_page()

            self.tt_client = await self.create_tiktok_client(httpx_proxy_format)
            if not await self.tt_client.pong(browser_context=self.browser_context):
                login_obj = TikTokLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()
                await self.tt_client.update_cookies(
                    browser_context=self.browser_context,
                    urls=self.cookie_urls,
                )
            elif config.COOKIES:
                login_obj = TikTokLogin(
                    login_type="cookie",
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.login_by_cookies()
                await self.tt_client.update_cookies(
                    browser_context=self.browser_context,
                    urls=self.cookie_urls,
                )

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                await self.get_specified_awemes()
            elif config.CRAWLER_TYPE == "creator":
                await self.get_creators_and_videos()

            utils.logger.info("[TikTokCrawler.start] TikTok Crawler finished ...")

    async def search(self) -> None:
        utils.logger.info("[TikTokCrawler.search] Begin search tiktok keywords")
        keyword_source = (config.KEYWORDS or "").strip()
        if not keyword_source:
            utils.logger.error(
                "[TikTokCrawler.search] Không có keywords. Nhập keyword trên UI (Enter để thêm) hoặc --keywords"
            )
            return
        utils.logger.info(f"[TikTokCrawler.search] Using keywords: {keyword_source}")
        for keyword in keyword_source.split(","):
            keyword = keyword.strip()
            if not keyword:
                continue
            source_keyword_var.set(keyword)
            utils.logger.info(f"[TikTokCrawler.search] Current keyword: {keyword}")
            try:
                posts_res = await self.tt_client.search_info_by_keyword(keyword=keyword)
            except DataFetchError as exc:
                msg = str(exc)
                if "ERR_CONNECTION_RESET" in msg or "Connection reset" in msg:
                    utils.logger.error(
                        "[TikTokCrawler.search] Mạng đang chặn https://www.tiktok.com "
                        "(ERR_CONNECTION_RESET / SNI DPI). Không phải sai domain, không phải lỗi crawler. "
                        "Hãy đổi sang hotspot 4G rồi chạy lại. Keyword hiện tại: "
                        f"{keyword}"
                    )
                    return
                utils.logger.error(f"[TikTokCrawler.search] search tiktok keyword: {keyword} failed: {exc}")
                continue

            page_aweme_list: List[str] = []
            for aweme_info in posts_res.get("data") or []:
                aweme_id = aweme_info.get("aweme_id", "")
                if not aweme_id:
                    continue
                page_aweme_list.append(aweme_id)
                await tiktok_store.update_tiktok_aweme(aweme_item=aweme_info)
                await self.get_aweme_media(aweme_item=aweme_info)

            await self.batch_get_note_comments(page_aweme_list)
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
            utils.logger.info(f"[TikTokCrawler.search] keyword:{keyword}, aweme_list:{page_aweme_list}")

    async def get_specified_awemes(self):
        utils.logger.info("[TikTokCrawler.get_specified_awemes] Parsing video URLs...")
        targets: List[tuple] = []
        for video_url in config.TIKTOK_SPECIFIED_ID_LIST:
            try:
                video_info = parse_video_info_from_url(video_url)
                if video_info.url_type == "short":
                    utils.logger.info(f"[TikTokCrawler.get_specified_awemes] Resolving short link: {video_url}")
                    resolved_url = await self.tt_client.resolve_short_url(video_url)
                    if not resolved_url:
                        utils.logger.error(f"[TikTokCrawler.get_specified_awemes] Failed to resolve: {video_url}")
                        continue
                    video_info = parse_video_info_from_url(resolved_url)
                targets.append((video_info.aweme_id, video_info.unique_id))
                utils.logger.info(f"[TikTokCrawler.get_specified_awemes] Parsed aweme ID: {video_info.aweme_id}")
            except ValueError as e:
                utils.logger.error(f"[TikTokCrawler.get_specified_awemes] Failed to parse video URL: {e}")
                continue

        semaphore = asyncio.Semaphore(1)
        task_list = [
            self.get_aweme_detail(aweme_id=aweme_id, semaphore=semaphore, unique_id=unique_id)
            for aweme_id, unique_id in targets
        ]
        aweme_details = await asyncio.gather(*task_list)
        aweme_id_list = [aweme_id for aweme_id, _ in targets]
        for aweme_detail in aweme_details:
            if aweme_detail is not None:
                await tiktok_store.update_tiktok_aweme(aweme_item=aweme_detail)
                await self.get_aweme_media(aweme_item=aweme_detail)
        await self.batch_get_note_comments(aweme_id_list)

    async def get_aweme_detail(
        self, aweme_id: str, semaphore: asyncio.Semaphore, unique_id: str = ""
    ) -> Any:
        async with semaphore:
            try:
                result = await self.tt_client.get_video_by_id(aweme_id, unique_id=unique_id)
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[TikTokCrawler.get_aweme_detail] Get aweme detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(f"[TikTokCrawler.get_aweme_detail] missing detail aweme_id:{aweme_id}, err: {ex}")
                return None

    async def batch_get_note_comments(self, aweme_list: List[str]) -> None:
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info("[TikTokCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return
        task_list: List[Task] = []
        semaphore = asyncio.Semaphore(1)
        for aweme_id in aweme_list:
            task = asyncio.create_task(self.get_comments(aweme_id, semaphore), name=aweme_id)
            task_list.append(task)
        if task_list:
            await asyncio.wait(task_list)

    async def get_comments(self, aweme_id: str, semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            try:
                crawl_interval = config.CRAWLER_MAX_SLEEP_SEC
                await self.tt_client.get_aweme_all_comments(
                    aweme_id=aweme_id,
                    crawl_interval=crawl_interval,
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                    callback=tiktok_store.batch_update_tiktok_aweme_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
                )
                await asyncio.sleep(crawl_interval)
                utils.logger.info(f"[TikTokCrawler.get_comments] aweme_id: {aweme_id} comments done")
            except DataFetchError as e:
                utils.logger.error(f"[TikTokCrawler.get_comments] aweme_id: {aweme_id} failed: {e}")

    async def get_creators_and_videos(self) -> None:
        utils.logger.info("[TikTokCrawler.get_creators_and_videos] Begin get tiktok creators")
        for creator_url in config.TIKTOK_CREATOR_ID_LIST:
            try:
                creator_info_parsed = parse_creator_info_from_url(creator_url)
                unique_id = creator_info_parsed.unique_id
                utils.logger.info(f"[TikTokCrawler.get_creators_and_videos] uniqueId: {unique_id}")
            except ValueError as e:
                utils.logger.error(f"[TikTokCrawler.get_creators_and_videos] Failed to parse creator URL: {e}")
                continue

            await tiktok_store.save_creator(unique_id, creator={})
            all_video_list = await self.tt_client.get_user_aweme_posts(unique_id=unique_id)
            video_ids = []
            for video_item in all_video_list:
                video_ids.append(video_item.get("aweme_id"))
                await tiktok_store.update_tiktok_aweme(aweme_item=video_item)
                await self.get_aweme_media(aweme_item=video_item)
            await self.batch_get_note_comments(video_ids)

    async def create_tiktok_client(self, httpx_proxy: Optional[str]) -> TikTokClient:
        cookie_str, cookie_dict = await utils.convert_browser_context_cookies(
            self.browser_context,
            urls=self.cookie_urls,
        )
        return TikTokClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": await self.context_page.evaluate("() => navigator.userAgent"),
                "Cookie": cookie_str,
                "Origin": "https://www.tiktok.com",
                "Referer": "https://www.tiktok.com/",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
            proxy_ip_pool=self.ip_proxy_pool,
        )

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        locale_kwargs: Dict[str, Any] = {
            "locale": "vi-VN",
            "viewport": {"width": 1920, "height": 1080},
        }
        if user_agent:
            locale_kwargs["user_agent"] = user_agent
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)
            return await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,
                **locale_kwargs,
            )
        browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
        return await browser.new_context(**locale_kwargs)

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )
            await self.cdp_manager.add_stealth_script()
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[TikTokCrawler] CDP browser: {browser_info}")
            return browser_context
        except Exception as e:
            utils.logger.error(f"[TikTokCrawler] CDP failed, fallback to standard: {e}")
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self) -> None:
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[TikTokCrawler.close] Browser context closed ...")

    async def get_aweme_media(self, aweme_item: Dict):
        if not config.ENABLE_GET_MEIDAS:
            return
        video_download_url: str = tiktok_store._extract_video_download_url(aweme_item)
        if video_download_url:
            await self.get_aweme_video(aweme_item)

    async def get_aweme_video(self, aweme_item: Dict):
        if not config.ENABLE_GET_MEIDAS:
            return
        aweme_id = aweme_item.get("aweme_id")
        video_download_url: str = tiktok_store._extract_video_download_url(aweme_item)
        if not video_download_url:
            return
        content = await self.tt_client.get_aweme_media(video_download_url)
        await asyncio.sleep(random.random())
        if content is None:
            return
        await tiktok_store.update_tiktok_aweme_video(aweme_id, content, "video.mp4")
