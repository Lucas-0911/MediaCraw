# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Maps structured AgentResponse values to safe Telegram presentation DTOs."""
from __future__ import annotations

from agent.core.contracts import AgentResponse, AgentResponseStatus, ToolResultStatus

from .contracts import TelegramMessageResponse


class TelegramResponseMapper:
    def map(self, response: AgentResponse) -> TelegramMessageResponse:
        if response.error == "conversation_busy":
            return TelegramMessageResponse(
                text="Hệ thống đang xử lý tin nhắn trước đó, vui lòng thử lại.",
                error="conversation_busy",
            )
        if response.status == AgentResponseStatus.TIMEOUT:
            return TelegramMessageResponse(text="Xin lỗi, yêu cầu đã hết thời gian xử lý.", error="timeout")
        if response.status == AgentResponseStatus.ERROR:
            return TelegramMessageResponse(
                text="Xin lỗi, hiện tại hệ thống không thể xử lý yêu cầu này.", error="internal_error"
            )

        latest = response.tool_results[-1] if response.tool_results else None
        if latest and latest.status == ToolResultStatus.DENIED:
            if latest.error_code in ("database_command_denied", "unsafe_operation"):
                return TelegramMessageResponse(
                    text="Agent chỉ được gọi hàm nghiệp vụ đã đăng ký, không được truy cập hay chạy lệnh database.",
                    error=latest.error_code,
                )
            return TelegramMessageResponse(
                text="Bạn không có quyền thực hiện yêu cầu này.", error="permission_denied"
            )
        if latest and latest.status in (ToolResultStatus.ERROR, ToolResultStatus.TIMEOUT):
            return TelegramMessageResponse(
                text="Xin lỗi, hiện tại hệ thống không thể xử lý yêu cầu này.", error="tool_failed"
            )
        if latest and latest.tool_name == "search_crawl_results":
            records = latest.data.get("records") or []
            if not records:
                return TelegramMessageResponse(
                    text="Không tìm thấy dữ liệu phù hợp trong dữ liệu hiện có.",
                    data={"count": 0},
                )
            lines = [f"Tìm thấy {len(records)} video phù hợp:"]
            for index, record in enumerate(records, start=1):
                title = record.get("title") or "Không có tiêu đề"
                lines.extend([f"", f"{index}. {title}"])
                if record.get("content"):
                    lines.append(f"   {str(record['content'])[:180]}")
                if record.get("url"):
                    lines.append(f"   {record['url']}")
            return TelegramMessageResponse(text="\n".join(lines), data=latest.data)
        if latest and latest.tool_name == "crawl_platform" and latest.job_id:
            return TelegramMessageResponse(
                text=f"Đã tạo job crawl #{latest.job_id}.\nMình sẽ theo dõi tiến trình.",
                data=latest.data,
                job_id=latest.job_id,
            )
        return TelegramMessageResponse(
            text=response.answer,
            data=response.data,
            job_id=response.job_id,
            requires_confirmation=response.requires_confirmation,
            error=response.error,
        )
