from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.license_service import MockLicenseService
from app.ui.icons import icon


class PricingDialog(QDialog):
    """Honest, non-transactional plan preview for the pre-commerce release."""

    def __init__(
        self,
        license_service: MockLicenseService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.license_service = license_service
        self.setWindowTitle("DiskWise Plans")
        self.setModal(True)
        self.setMinimumSize(920, 610)
        self.resize(980, 650)

        title = QLabel("Choose the right level of cleanup")
        title.setObjectName("OnboardingTitle")
        description = QLabel(
            "Core scanning and Safe cleanup stay available on the Free plan. "
            "Pro plans are shown only as a roadmap preview."
        )
        description.setObjectName("SectionDescription")
        description.setWordWrap(True)

        notice = QLabel(self.license_service.pricing_message())
        notice.setObjectName("InfoPill")
        notice.setWordWrap(True)

        plans = QHBoxLayout()
        plans.setSpacing(14)
        plans.addWidget(
            self._plan_card(
                name="Free",
                status="Current plan",
                price="$0",
                cadence="No subscription",
                features=[
                    "Quick and Deep scans",
                    "Safe Recycle Bin cleanup",
                    "Large-file and duplicate review",
                    "Local cleanup reports",
                ],
                current=True,
            ),
            1,
        )
        plans.addWidget(
            self._plan_card(
                name="Pro Monthly",
                status="Planned",
                price="Not available",
                cadence="Future monthly plan",
                features=[
                    "Scheduled cleanup",
                    "Advanced duplicate actions",
                    "Expanded AI assistance",
                    "App-specific cleanup recipes",
                ],
            ),
            1,
        )
        plans.addWidget(
            self._plan_card(
                name="Pro Yearly",
                status="Planned",
                price="Not available",
                cadence="Future annual plan",
                features=[
                    "Everything planned for Pro",
                    "Business-ready reports",
                    "Priority feature access",
                    "No payment collected today",
                ],
            ),
            1,
        )

        close_button = QPushButton("Close")
        close_button.setProperty("class", "Secondary")
        close_button.setIcon(icon("x", "#4f7fe8"))
        close_button.clicked.connect(self.accept)

        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(notice)
        layout.addLayout(plans, 1)
        layout.addLayout(footer)

    def _plan_card(
        self,
        name: str,
        status: str,
        price: str,
        cadence: str,
        features: list[str],
        current: bool = False,
    ) -> QFrame:
        card = QFrame()
        card.setProperty("class", "PlanCardCurrent" if current else "PlanCard")

        heading = QHBoxLayout()
        plan_name = QLabel(name)
        plan_name.setObjectName("SectionTitle")
        badge = QLabel(status)
        badge.setProperty("class", "PlanBadgeCurrent" if current else "PlanBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.addWidget(plan_name)
        heading.addStretch()
        heading.addWidget(badge)

        price_label = QLabel(price)
        price_label.setProperty("class", "PlanPrice")
        cadence_label = QLabel(cadence)
        cadence_label.setObjectName("MutedText")

        feature_layout = QVBoxLayout()
        feature_layout.setSpacing(10)
        for feature in features:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            feature_icon = QLabel()
            feature_icon.setPixmap(icon("check", "#22a06b", 16).pixmap(16, 16))
            feature_label = QLabel(feature)
            feature_label.setWordWrap(True)
            row_layout.addWidget(feature_icon, alignment=Qt.AlignmentFlag.AlignTop)
            row_layout.addWidget(feature_label, 1)
            feature_layout.addWidget(row)

        action = QPushButton("Current Plan" if current else "Not Available Yet")
        action.setProperty("class", "Secondary")
        action.setEnabled(False)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addLayout(heading)
        layout.addWidget(price_label)
        layout.addWidget(cadence_label)
        layout.addSpacing(8)
        layout.addLayout(feature_layout)
        layout.addStretch()
        layout.addWidget(action)
        return card
