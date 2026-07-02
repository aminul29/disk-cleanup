from __future__ import annotations

import json
from datetime import datetime

from app.models import CleanupCategory, CleanupItem, RiskLevel, ScanResult
from app.services.ai_advisor_service import build_privacy_safe_scan_request, parse_ai_recommendation


def test_ai_request_uses_aggregate_data_without_file_names_or_paths() -> None:
    now = datetime.now()
    scan = ScanResult(
        scan_id="scan_test",
        started_at=now,
        completed_at=now,
        duration_seconds=1.0,
        total_files_scanned=1,
        total_bytes_scanned=100,
        safe_bytes=100,
        review_bytes=0,
        protected_bytes=0,
        categories=[
            CleanupCategory(
                id="user_temp",
                name="User Temporary Files",
                description="Temporary files from user temp.",
                risk_level=RiskLevel.SAFE,
                total_bytes=100,
                file_count=1,
                items=[
                    CleanupItem(
                        id="secret",
                        file_name="private-name.tmp",
                        file_path="C:/Users/USER/Documents/private-name.tmp",
                        extension=".tmp",
                        size_bytes=100,
                        last_modified_at=now,
                        category="user_temp",
                        risk_level=RiskLevel.SAFE,
                        reason="temp",
                        can_delete=True,
                        is_selected=True,
                    )
                ],
                is_selected_by_default=True,
            )
        ],
        large_files=[],
        duplicate_groups=[],
        errors=[],
    )

    request = build_privacy_safe_scan_request(scan)
    payload = json.dumps(request.model_dump())

    assert "private-name.tmp" not in payload
    assert "C:/Users/USER/Documents" not in payload
    assert "User Temporary Files" in payload
    assert request.safe_bytes == 100


def test_parse_ai_recommendation_accepts_json_content() -> None:
    recommendation = parse_ai_recommendation(
        '{"summary":"Clean safe items first.","recommended_next_steps":["Preview cleanup"],'
        '"safe_cleanup_plan":["Clean browser cache"],'
        '"warnings":["Do not delete unknown installers"],'
        '"confidence":"High",'
        '"safety_notes":["Do not auto-delete review files"],"review_priorities":["Downloads"]}'
    )

    assert recommendation.summary == "Clean safe items first."
    assert recommendation.safe_cleanup_plan == ["Clean browser cache"]
    assert recommendation.recommended_next_steps == ["Preview cleanup"]
    assert recommendation.warnings == ["Do not delete unknown installers"]
    assert recommendation.safety_notes == ["Do not auto-delete review files"]
    assert recommendation.review_priorities == ["Downloads"]
    assert recommendation.confidence == "High"
