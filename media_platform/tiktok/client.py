# -*- coding: utf-8 -*-
"""TikTok Vietnam / international (tiktok.com) client.

Public pages are scraped via Playwright (search XHR intercept + hydration JSON).
No Douyin a_bogus / signed API clone — those tokens do not apply to tiktok.com.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union
from urllib.parse import quote

import httpx
from playwright.async_api import BrowserContext, Page, Response

import config
from base.base_crawler import AbstractApiClient
from proxy.proxy_mixin import ProxyRefreshMixin
from tools import utils
from tools.httpx_util import make_async_client

from .exception import DataFetchError
from .help import collect_comments_from_json, collect_items_from_search_json, parse_universal_data

if TYPE_CHECKING:
    from proxy.proxy_ip_pool import ProxyIpPool


SEARCH_HINTS = ("/api/search/", "/api/post/item_list/", "/api/recommend/item_list/")
COMMENT_HINTS = ("/api/comment/list", "/api/comment/list/")


class TikTokClient(AbstractApiClient, ProxyRefreshMixin):
    def __init__(
        self,
        timeout=60,
        proxy=None,
        *,
        headers: Dict,
        playwright_page: Optional[Page],
        cookie_dict: Dict,
        proxy_ip_pool: Optional["ProxyIpPool"] = None,
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.headers = headers
        self._host = getattr(config, "TIKTOK_INDEX_URL", "https://www.tiktok.com").rstrip("/")
        self._lang = getattr(config, "TIKTOK_LANG", "vi")
        self.cookie_urls = [
            "https://tiktok.com",
            self._host,
            "https://www.tiktok.com",
        ]
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        self.init_proxy_pool(proxy_ip_pool)

    def _abs(self, path: str) -> str:
        path = path if path.startswith("/") else f"/{path}"
        sep = "&" if "?" in path else "?"
        return f"{self._host}{path}{sep}lang={self._lang}"

    async def _goto(self, page: Page, url: str) -> None:
        last_exc: Optional[Exception] = None
        for wait_until in ("commit", "domcontentloaded"):
            try:
                await page.goto(url, wait_until=wait_until, timeout=60000)
                return
            except Exception as exc:
                last_exc = exc
                utils.logger.warning(f"[TikTokClient._goto] {wait_until} {url} failed: {exc}")
        raise DataFetchError(str(last_exc) if last_exc else f"goto failed: {url}")

    async def request(self, method, url, **kwargs):
        async with make_async_client(proxy=self.proxy) as client:
            response = await client.request(
                method,
                url,
                headers=self.headers,
                timeout=self.timeout,
                follow_redirects=True,
                **kwargs,
            )
            return response

    async def update_cookies(self, browser_context: BrowserContext, urls: Optional[List[str]] = None):
        cookie_str, cookie_dict = await utils.convert_browser_context_cookies(
            browser_context,
            urls=urls or self.cookie_urls,
        )
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def pong(self, browser_context: BrowserContext) -> bool:
        """True if logged in, or guest crawl is allowed."""
        if getattr(config, "TIKTOK_ALLOW_GUEST", True):
            utils.logger.info("[TikTokClient.pong] Guest / public crawl enabled, skip login check")
            return True
        current_cookie = await browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        if cookie_dict.get("sessionid") or cookie_dict.get("sessionid_ss") or cookie_dict.get("sid_tt"):
            return True
        return False

    async def _dismiss_overlays(self, page: Optional[Page] = None) -> None:
        page = page or self.playwright_page
        if not page:
            return
        selectors = [
            '[data-e2e="cookie-banner-accept"]',
            'button:has-text("Accept all")',
            'button:has-text("Accept")',
            'button:has-text("Đồng ý")',
            'button:has-text("Tiếp tục với tư cách khách")',
            'button:has-text("Continue as guest")',
            'button:has-text("Skip")',
            '[data-e2e="modal-close-inner-button"]',
            'button[aria-label="Close"]',
        ]
        for selector in selectors:
            try:
                loc = page.locator(selector).first
                if await loc.count() and await loc.is_visible():
                    await loc.click(timeout=1500)
                    await asyncio.sleep(0.3)
            except Exception:
                continue

    async def _read_hydration(self, page: Optional[Page] = None) -> List[Dict[str, Any]]:
        page = page or self.playwright_page
        if not page:
            return []
        try:
            raw = await page.evaluate(
                """() => {
                    const u = document.querySelector('#__UNIVERSAL_DATA_FOR_REHYDRATION__');
                    if (u && u.textContent) return u.textContent;
                    const sigi = document.querySelector('#SIGI_STATE');
                    if (sigi && sigi.textContent) return sigi.textContent;
                    return null;
                }"""
            )
        except Exception as exc:
            utils.logger.warning(f"[TikTokClient._read_hydration] {exc}")
            return []
        return parse_universal_data(raw)

    def _merge_items(self, bucket: Dict[str, Dict[str, Any]], items: List[Dict[str, Any]]) -> None:
        for item in items:
            aweme_id = item.get("aweme_id")
            if aweme_id and aweme_id not in bucket:
                bucket[aweme_id] = item

    async def _attach_item_listener(self, page: Page, bucket: Dict[str, Dict[str, Any]]):
        async def on_response(response: Response):
            url = response.url or ""
            if not any(hint in url for hint in SEARCH_HINTS):
                return
            try:
                payload = await response.json()
            except Exception:
                return
            self._merge_items(bucket, collect_items_from_search_json(payload))

        page.on("response", on_response)
        return on_response

    async def _scroll_collect(
        self,
        page: Page,
        bucket: Dict[str, Dict[str, Any]],
        max_count: int,
        max_stall: int = 5,
    ) -> None:
        stall = 0
        last_len = len(bucket)
        while len(bucket) < max_count and stall < max_stall:
            await page.mouse.wheel(0, 2400)
            await asyncio.sleep(max(1.2, float(config.CRAWLER_MAX_SLEEP_SEC)))
            self._merge_items(bucket, await self._read_hydration(page))
            if len(bucket) == last_len:
                stall += 1
            else:
                stall = 0
                last_len = len(bucket)
            utils.logger.info(f"[TikTokClient._scroll_collect] collected={len(bucket)} stall={stall}")

    async def search_info_by_keyword(self, keyword: str, offset: int = 0) -> Dict[str, Any]:
        """Search public TikTok videos for a keyword (vi-VN locale)."""
        if not self.playwright_page:
            raise DataFetchError("Playwright page is not ready")

        page = self.playwright_page
        bucket: Dict[str, Dict[str, Any]] = {}
        listener = await self._attach_item_listener(page, bucket)
        search_url = self._abs(f"/search/video?q={quote(keyword)}")
        utils.logger.info(f"[TikTokClient.search_info_by_keyword] goto {search_url}")
        try:
            await self._goto(page, search_url)
            await self._dismiss_overlays(page)
            await asyncio.sleep(2)
            self._merge_items(bucket, await self._read_hydration(page))
            await self._scroll_collect(page, bucket, max_count=config.CRAWLER_MAX_NOTES_COUNT)
        except DataFetchError:
            raise
        except Exception as exc:
            raise DataFetchError(str(exc)) from exc
        finally:
            page.remove_listener("response", listener)

        items = list(bucket.values())
        if offset:
            items = items[offset:]
        return {"data": items, "keyword": keyword}

    async def get_video_by_id(self, aweme_id: str, unique_id: str = "") -> Optional[Dict[str, Any]]:
        if not self.playwright_page:
            raise DataFetchError("Playwright page is not ready")
        page = self.playwright_page
        bucket: Dict[str, Dict[str, Any]] = {}
        listener = await self._attach_item_listener(page, bucket)
        url = self._abs(f"/@{unique_id}/video/{aweme_id}" if unique_id else f"/video/{aweme_id}")
        try:
            await self._goto(page, url)
            await self._dismiss_overlays(page)
            await asyncio.sleep(1.5)
            self._merge_items(bucket, await self._read_hydration(page))
        except Exception as exc:
            page.remove_listener("response", listener)
            raise DataFetchError(str(exc)) from exc
        page.remove_listener("response", listener)
        if aweme_id in bucket:
            return bucket[aweme_id]
        if bucket:
            return next(iter(bucket.values()))
        return None

    async def get_user_aweme_posts(self, unique_id: str) -> List[Dict[str, Any]]:
        if not self.playwright_page:
            raise DataFetchError("Playwright page is not ready")
        page = self.playwright_page
        bucket: Dict[str, Dict[str, Any]] = {}
        listener = await self._attach_item_listener(page, bucket)
        url = self._abs(f"/@{unique_id.lstrip('@')}")
        try:
            await self._goto(page, url)
            await self._dismiss_overlays(page)
            await asyncio.sleep(2)
            self._merge_items(bucket, await self._read_hydration(page))
            await self._scroll_collect(page, bucket, max_count=config.CRAWLER_MAX_NOTES_COUNT)
        except Exception as exc:
            page.remove_listener("response", listener)
            raise DataFetchError(str(exc)) from exc
        page.remove_listener("response", listener)
        return list(bucket.values())

    async def get_aweme_all_comments(
        self,
        aweme_id: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        max_count: int = 20,
        unique_id: str = "",
        **_kwargs,
    ) -> List[Dict[str, Any]]:
        if not self.playwright_page:
            return []
        page = self.playwright_page
        comments: Dict[str, Dict[str, Any]] = {}

        async def on_response(response: Response):
            url = response.url or ""
            if not any(hint in url for hint in COMMENT_HINTS):
                return
            try:
                payload = await response.json()
            except Exception:
                return
            for row in collect_comments_from_json(payload, aweme_id):
                comments[row["cid"]] = row

        page.on("response", on_response)
        url = self._abs(f"/@{unique_id}/video/{aweme_id}" if unique_id else f"/video/{aweme_id}")
        try:
            await self._goto(page, url)
            await self._dismiss_overlays(page)
            for selector in (
                '[data-e2e="comment-icon"]',
                'p:has-text("Bình luận")',
                'p:has-text("Comments")',
            ):
                try:
                    loc = page.locator(selector).first
                    if await loc.count():
                        await loc.click(timeout=2000)
                        break
                except Exception:
                    continue
            stall = 0
            last_len = 0
            while len(comments) < max_count and stall < 4:
                await page.mouse.wheel(0, 1200)
                await asyncio.sleep(crawl_interval)
                if len(comments) == last_len:
                    stall += 1
                else:
                    stall = 0
                    last_len = len(comments)
        except Exception as exc:
            utils.logger.warning(f"[TikTokClient.get_aweme_all_comments] {aweme_id}: {exc}")
        finally:
            page.remove_listener("response", on_response)

        result = list(comments.values())[:max_count]
        if callback and result:
            await callback(aweme_id, result)
        return result

    async def get_aweme_media(self, url: str) -> Union[bytes, None]:
        if not url:
            return None
        async with make_async_client(proxy=self.proxy) as client:
            try:
                response = await client.request(
                    "GET",
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.content
            except httpx.HTTPError as exc:
                utils.logger.error(
                    f"[TikTokClient.get_aweme_media] {exc.__class__.__name__} for {getattr(exc, 'request', None)}"
                )
                return None

    async def resolve_short_url(self, short_url: str) -> str:
        if self.playwright_page:
            try:
                await self.playwright_page.goto(short_url, wait_until="domcontentloaded", timeout=30000)
                return self.playwright_page.url
            except Exception as exc:
                utils.logger.warning(f"[TikTokClient.resolve_short_url] playwright failed: {exc}")
        async with make_async_client(proxy=self.proxy, follow_redirects=True) as client:
            try:
                response = await client.get(short_url, timeout=15)
                return str(response.url)
            except Exception as e:
                utils.logger.error(f"[TikTokClient.resolve_short_url] Failed: {e}")
                return ""
