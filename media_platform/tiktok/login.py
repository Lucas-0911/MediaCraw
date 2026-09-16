# -*- coding: utf-8 -*-
"""Optional TikTok login. Guest/public crawl is the default for Vietnam testing."""
from __future__ import annotations

import asyncio
import functools
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import RetryError, retry, retry_if_result, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractLogin
from tools import utils


class TikTokLogin(AbstractLogin):
    def __init__(
        self,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        login_phone: Optional[str] = "",
        cookie_str: Optional[str] = "",
    ):
        config.LOGIN_TYPE = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str

    async def begin(self):
        if getattr(config, "TIKTOK_ALLOW_GUEST", True) and config.LOGIN_TYPE not in ("cookie", "qrcode"):
            utils.logger.info("[TikTokLogin.begin] Guest mode, skip login")
            return

        if config.LOGIN_TYPE == "qrcode":
            if getattr(config, "TIKTOK_ALLOW_GUEST", True):
                utils.logger.info("[TikTokLogin.begin] Guest mode is on — skip QR. Set TIKTOK_ALLOW_GUEST=False to force login.")
                return
            await self.login_by_qrcode()
        elif config.LOGIN_TYPE == "phone":
            await self.login_by_mobile()
        elif config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError("[TikTokLogin.begin] Invalid login type (qrcode | phone | cookie)")

        utils.logger.info("[TikTokLogin.begin] login finished then check login state ...")
        try:
            await self.check_login_state()
        except RetryError:
            if getattr(config, "TIKTOK_ALLOW_GUEST", True):
                utils.logger.info("[TikTokLogin.begin] login not confirmed, continue as guest")
                return
            utils.logger.info("[TikTokLogin.begin] login failed please confirm ...")
            sys.exit()
        await asyncio.sleep(3)

    @retry(stop=stop_after_attempt(90), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self):
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        if cookie_dict.get("sessionid") or cookie_dict.get("sessionid_ss") or cookie_dict.get("sid_tt"):
            return True
        return False

    async def login_by_qrcode(self):
        utils.logger.info("[TikTokLogin.login_by_qrcode] Begin login tiktok by qrcode...")
        for selector in (
            '[data-e2e="top-login-button"]',
            'button:has-text("Log in")',
            'button:has-text("Đăng nhập")',
        ):
            try:
                loc = self.context_page.locator(selector).first
                if await loc.count():
                    await loc.click(timeout=3000)
                    break
            except Exception:
                continue
        await asyncio.sleep(2)
        qrcode_img_selector = 'img[alt*="QR"], canvas, [data-e2e="qr-code"] img'
        base64_qrcode_img = await utils.find_login_qrcode(self.context_page, selector=qrcode_img_selector)
        if not base64_qrcode_img:
            utils.logger.info("[TikTokLogin.login_by_qrcode] QR not found — continue without login if guest is allowed")
            return
        partial_show_qrcode = functools.partial(utils.show_qrcode, base64_qrcode_img)
        asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)
        await asyncio.sleep(2)

    async def login_by_mobile(self):
        utils.logger.info("[TikTokLogin.login_by_mobile] Phone login is not automated. Use guest or cookie.")
        if getattr(config, "TIKTOK_ALLOW_GUEST", True):
            return
        sys.exit()

    async def login_by_cookies(self):
        utils.logger.info("[TikTokLogin.login_by_cookies] Begin login tiktok by cookie ...")
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies(
                [
                    {
                        "name": key,
                        "value": value,
                        "domain": ".tiktok.com",
                        "path": "/",
                    }
                ]
            )
