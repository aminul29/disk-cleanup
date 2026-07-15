from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

from app.constants import APP_NAME
from app.models import AiCategorySummary, AiRecommendation, AiScanSummaryRequest, RiskLevel, ScanResult
from app.services.settings_service import SettingsService
from app.utils.formatting import format_bytes

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


class AiAdvisorService:
    def __init__(self, settings_service: SettingsService) -> None:
        self.settings_service = settings_service
        self.logger = logging.getLogger(__name__)

    def generate_scan_summary(self, result: ScanResult) -> str:
        request = build_privacy_safe_scan_request(result)
        if request.safe_bytes == 0 and request.review_bytes == 0:
            return "DiskWise did not find obvious cleanup space in the scanned areas."
        return (
            f"DiskWise found {format_bytes(request.safe_bytes)} safe to clean and "
            f"{format_bytes(request.review_bytes)} that should be reviewed before deletion."
        )

    def generate_recommendations(self, result: ScanResult) -> AiRecommendation:
        if not self.settings_service.ai_summary_enabled():
            return AiRecommendation(
                summary="AI advice is disabled in Settings.",
                recommended_next_steps=["Enable AI advice in Settings to analyze aggregate scan data."],
                safety_notes=["Local scanning and cleanup remain available."],
            )
        return self._generate_for_provider(result)

    def _generate_for_provider(self, result: ScanResult) -> AiRecommendation:
        provider = self.settings_service.get_ai_provider()
        if provider == "OpenRouter":
            if self.settings_service.privacy_mode_enabled():
                return AiRecommendation(
                    summary="Strict local mode is enabled, so no data was sent to OpenRouter.",
                    recommended_next_steps=[
                        "Turn off Strict local mode in Settings to use privacy-safe aggregate AI advice."
                    ],
                    safety_notes=["Local scanning and deterministic cleanup rules remain available."],
                    confidence="High",
                )
            return self._generate_openrouter_recommendations(result)
        return self._generate_mock_recommendations(result)

    def test_connection(self) -> AiRecommendation:
        sample = sample_scan_result()
        return self._generate_for_provider(sample)

    def _generate_mock_recommendations(self, result: ScanResult) -> AiRecommendation:
        request = build_privacy_safe_scan_request(result)
        largest_safe = max(
            (category for category in request.categories if category.risk_level == RiskLevel.SAFE.value),
            key=lambda category: category.total_bytes,
            default=None,
        )
        review_categories = [
            category.name
            for category in request.categories
            if category.risk_level == RiskLevel.REVIEW.value and category.total_bytes > 0
        ]
        steps = ["Clean selected Safe items first after previewing the cleanup plan."]
        if largest_safe:
            steps.append(f"Start with {largest_safe.name}; it has the most safe reclaimable space.")
        if review_categories:
            steps.append("Review large downloads and duplicate candidates manually before deleting anything.")
        return AiRecommendation(
            summary=(
                f"Safe cleanup: {format_bytes(request.safe_bytes)}. "
                f"Manual review: {format_bytes(request.review_bytes)}. "
                "No personal file names or paths were used."
            ),
            safe_cleanup_plan=steps[:2],
            recommended_next_steps=steps,
            safety_notes=[
                "Review and Protected items are not eligible for automatic cleanup.",
                "DiskWise keeps deterministic cleanup rules in control.",
            ],
            review_priorities=review_categories[:5],
            warnings=["Do not delete Review items unless you personally recognize them."],
            confidence="High" if request.safe_bytes > 0 else "Medium",
        )

    def _generate_openrouter_recommendations(self, result: ScanResult) -> AiRecommendation:
        api_key = self.settings_service.get_openrouter_api_key() or os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            return AiRecommendation(
                summary="OpenRouter is selected, but no API key is configured.",
                recommended_next_steps=["Add an OpenRouter API key in Settings or set OPENROUTER_API_KEY."],
                safety_notes=["DiskWise will continue using deterministic local safety rules."],
            )

        request_model = build_privacy_safe_scan_request(result)
        model = self.settings_service.get_openrouter_model()
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are DiskWise AI, a careful Windows disk cleanup advisor. "
                        "You must be proactive and useful, but you cannot authorize deletion. "
                        "Never suggest deleting Review or Protected items automatically. "
                        "Use only the aggregate data provided. Do not claim performance boosts. "
                        "Return concise JSON with keys: summary, safe_cleanup_plan, "
                        "review_priorities, warnings, safety_notes, recommended_next_steps, confidence. "
                        "confidence must be High, Medium, or Low."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(request_model.model_dump(), separators=(",", ":")),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 700,
        }
        http_request = urllib.request.Request(
            OPENROUTER_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/aminul29/disk-cleanup",
                "X-OpenRouter-Title": APP_NAME,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=45) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            self.logger.warning("OpenRouter HTTP error: %s", exc)
            return AiRecommendation(
                summary=f"OpenRouter returned an error: HTTP {exc.code}.",
                recommended_next_steps=["Check your API key, model name, and OpenRouter account limits."],
                safety_notes=["No cleanup action was changed."],
            )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            self.logger.warning("OpenRouter request failed: %s", exc)
            return AiRecommendation(
                summary="OpenRouter is unavailable right now.",
                recommended_next_steps=["Check your internet connection or switch AI provider to Mock."],
                safety_notes=["No cleanup action was changed."],
            )

        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        return parse_ai_recommendation(content)


def build_privacy_safe_scan_request(result: ScanResult) -> AiScanSummaryRequest:
    return AiScanSummaryRequest(
        total_files_scanned=result.total_files_scanned,
        total_bytes_scanned=result.total_bytes_scanned,
        safe_bytes=result.safe_bytes,
        review_bytes=result.review_bytes,
        protected_bytes=result.protected_bytes,
        large_file_count=len(result.large_files),
        duplicate_group_count=len(result.duplicate_groups),
        error_count=len(result.errors),
        categories=[
            AiCategorySummary(
                name=category.name,
                risk_level=category.risk_level.value,
                total_bytes=category.total_bytes,
                file_count=category.file_count,
                selected_by_default=category.is_selected_by_default,
                reason=category.description,
            )
            for category in result.categories
        ],
    )


def parse_ai_recommendation(content: str) -> AiRecommendation:
    try:
        start = content.find("{")
        end = content.rfind("}")
        payload = json.loads(content[start : end + 1] if start >= 0 and end >= 0 else content)
        return AiRecommendation(
            summary=str(payload.get("summary", "")).strip() or "AI analysis completed.",
            safe_cleanup_plan=[str(item) for item in payload.get("safe_cleanup_plan", [])],
            recommended_next_steps=[str(item) for item in payload.get("recommended_next_steps", [])],
            safety_notes=[str(item) for item in payload.get("safety_notes", [])],
            review_priorities=[str(item) for item in payload.get("review_priorities", [])],
            warnings=[str(item) for item in payload.get("warnings", [])],
            confidence=str(payload.get("confidence", "Medium")),
        )
    except (json.JSONDecodeError, AttributeError):
        return AiRecommendation(
            summary=content.strip() or "AI analysis completed.",
            recommended_next_steps=[],
            safety_notes=["DiskWise cleanup safety rules remain unchanged."],
            review_priorities=[],
        )


def sample_scan_result() -> ScanResult:
    from datetime import datetime

    from app.models import CleanupCategory

    now = datetime.now()
    return ScanResult(
        scan_id="openrouter_test",
        started_at=now,
        completed_at=now,
        duration_seconds=1.0,
        total_files_scanned=120,
        total_bytes_scanned=2_000_000_000,
        safe_bytes=500_000_000,
        review_bytes=1_500_000_000,
        protected_bytes=0,
        categories=[
            CleanupCategory(
                id="browser_cache",
                name="Browser Cache",
                description="Accessible browser cache files.",
                risk_level=RiskLevel.SAFE,
                total_bytes=500_000_000,
                file_count=100,
                items=[],
                is_selected_by_default=True,
            ),
            CleanupCategory(
                id="old_downloads",
                name="Old Downloads",
                description="Large downloads requiring manual review.",
                risk_level=RiskLevel.REVIEW,
                total_bytes=1_500_000_000,
                file_count=20,
                items=[],
                is_selected_by_default=False,
            ),
        ],
        large_files=[],
        duplicate_groups=[],
        errors=[],
    )
