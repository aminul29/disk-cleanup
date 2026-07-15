from __future__ import annotations

from app.models import LicenseStatus


class MockLicenseService:
    def get_license_status(self) -> LicenseStatus:
        return LicenseStatus(
            plan_name="Free Plan",
            is_pro=False,
            enabled_features=["quick_scan", "safe_cleanup", "local_reports"],
        )

    def is_feature_enabled(self, feature_key: str) -> bool:
        return feature_key in {"quick_scan", "safe_cleanup", "local_reports"}

    def pricing_message(self) -> str:
        return "Purchases are not available in this release. No payment information is collected."
