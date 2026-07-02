from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.models import CleanupItem, RiskLevel
from app.services import cleanup_service as cleanup_module
from app.services.cleanup_service import CleanupService
from app.utils.safety import is_safe_cleanup_path


class FakeReportService:
    def __init__(self) -> None:
        self.results = []

    def create_cleanup_report(self, result):
        self.results.append(result)
        return None


def make_item(path: Path, risk: RiskLevel = RiskLevel.SAFE, can_delete: bool = True) -> CleanupItem:
    return CleanupItem(
        id=path.name,
        file_name=path.name,
        file_path=str(path),
        extension=path.suffix,
        size_bytes=path.stat().st_size if path.exists() else 0,
        last_modified_at=datetime.now(),
        category="test",
        risk_level=risk,
        reason="test item",
        can_delete=can_delete,
        is_selected=True,
    )


def test_preview_keeps_only_selected_safe_deletable_items(tmp_path: Path) -> None:
    safe = tmp_path / "safe.tmp"
    review = tmp_path / "review.zip"
    protected = tmp_path / "protected.txt"
    safe.write_text("safe")
    review.write_text("review")
    protected.write_text("protected")

    service = CleanupService(FakeReportService(), safe_roots=[tmp_path], protected_roots=[])

    preview = service.preview_items(
        [
            make_item(safe, RiskLevel.SAFE, True),
            make_item(review, RiskLevel.REVIEW, False),
            make_item(protected, RiskLevel.PROTECTED, False),
        ]
    )

    assert [item.file_name for item in preview] == ["safe.tmp"]


def test_cleanup_deletes_only_safe_items_inside_safe_roots(monkeypatch, tmp_path: Path) -> None:
    safe_root = tmp_path / "cache"
    unsafe_root = tmp_path / "documents"
    safe_root.mkdir()
    unsafe_root.mkdir()
    safe_file = safe_root / "safe.tmp"
    unsafe_file = unsafe_root / "unsafe.tmp"
    review_file = safe_root / "review.zip"
    safe_file.write_text("safe")
    unsafe_file.write_text("unsafe")
    review_file.write_text("review")

    def fake_send2trash(path: str) -> None:
        Path(path).unlink()

    monkeypatch.setattr(cleanup_module, "send2trash", fake_send2trash)

    report_service = FakeReportService()
    service = CleanupService(report_service, safe_roots=[safe_root], protected_roots=[unsafe_root])

    result = service.cleanup_safe_items(
        "scan_test",
        [
            make_item(safe_file, RiskLevel.SAFE, True),
            make_item(unsafe_file, RiskLevel.SAFE, True),
            make_item(review_file, RiskLevel.REVIEW, False),
        ],
    )

    assert result.files_deleted == 1
    assert result.files_skipped == 2
    assert not safe_file.exists()
    assert unsafe_file.exists()
    assert review_file.exists()
    assert report_service.results


def test_protected_root_wins_even_when_nested_in_safe_root(tmp_path: Path) -> None:
    safe_root = tmp_path / "cache"
    protected_root = safe_root / "repo" / ".git"
    protected_root.mkdir(parents=True)
    file_path = protected_root / "config"
    file_path.write_text("secret")

    assert not is_safe_cleanup_path(
        file_path,
        safe_roots=[safe_root],
        protected_roots=[protected_root],
    )
