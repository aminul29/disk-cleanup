from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.services.settings_service import SettingsService
from app.ui.icons import icon
from app.ui.widgets import SegmentedControl, risk_badge


class OnboardingDialog(QDialog):
    """A short, skippable introduction to DiskWise safety and scan modes."""

    def __init__(self, settings_service: SettingsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings_service = settings_service
        self.start_scan_requested = False
        self.setWindowTitle("Welcome to DiskWise AI")
        self.setModal(True)
        self.setMinimumSize(760, 540)
        self.resize(820, 580)

        self.pages = QStackedWidget()
        self.mode_control = SegmentedControl(
            ["Quick", "Deep"], self.settings_service.get_scan_mode()
        )
        self.mode_control.value_changed.connect(self.settings_service.set_scan_mode)

        self.pages.addWidget(
            self._page(
                "sparkles",
                "Welcome to DiskWise AI",
                "Find reclaimable space with clear safety rules and a local-first workflow.",
                [
                    ("scan-search", "Scan", "Inspect supported cleanup locations on this PC."),
                    ("list-checks", "Review", "See every result before cleanup starts."),
                    ("shield-check", "Clean safely", "Only selected Safe items can be removed."),
                ],
            )
        )
        self.pages.addWidget(
            self._page(
                "lock-keyhole",
                "Your files stay private",
                "Scanning and cleanup run locally. DiskWise never uploads file names, paths, or contents.",
                [
                    ("hard-drive", "Local scanning", "File discovery stays on this Windows device."),
                    ("database", "Local history", "Scan and cleanup summaries are saved in SQLite."),
                    ("brain", "Privacy-safe AI", "Optional AI receives aggregate category totals only."),
                ],
            )
        )
        self.pages.addWidget(self._risk_page())
        self.pages.addWidget(self._scan_mode_page())

        self.step_label = QLabel()
        self.step_label.setObjectName("MutedText")
        self.skip_button = QPushButton("Skip")
        self.skip_button.setProperty("class", "Secondary")
        self.back_button = QPushButton("Back")
        self.back_button.setProperty("class", "Secondary")
        self.next_button = QPushButton("Next")
        self.skip_button.clicked.connect(self._skip)
        self.back_button.clicked.connect(self._back)
        self.next_button.clicked.connect(self._next)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.addWidget(self.step_label)
        footer.addStretch()
        footer.addWidget(self.skip_button)
        footer.addWidget(self.back_button)
        footer.addWidget(self.next_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(18)
        layout.addWidget(self.pages, 1)
        layout.addLayout(footer)
        self._sync_controls()

    def _page(
        self,
        icon_name: str,
        title_text: str,
        description_text: str,
        rows: list[tuple[str, str, str]],
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)

        hero_icon = QLabel()
        hero_icon.setPixmap(icon(icon_name, "#2f6df6", 42).pixmap(42, 42))
        title = QLabel(title_text)
        title.setObjectName("OnboardingTitle")
        description = QLabel(description_text)
        description.setObjectName("SectionDescription")
        description.setWordWrap(True)

        layout.addWidget(hero_icon)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(10)
        for row_icon, row_title, row_description in rows:
            layout.addWidget(self._feature_row(row_icon, row_title, row_description))
        layout.addStretch()
        return page

    def _feature_row(self, icon_name: str, title_text: str, description_text: str) -> QFrame:
        row = QFrame()
        row.setProperty("class", "OnboardingRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        row_icon = QLabel()
        row_icon.setPixmap(icon(icon_name, "#2f6df6", 24).pixmap(24, 24))
        text = QWidget()
        text_layout = QVBoxLayout(text)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)
        title = QLabel(title_text)
        title.setObjectName("FeatureTitle")
        description = QLabel(description_text)
        description.setObjectName("MutedText")
        description.setWordWrap(True)
        text_layout.addWidget(title)
        text_layout.addWidget(description)

        layout.addWidget(row_icon, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(text, 1)
        return row

    def _risk_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)

        hero_icon = QLabel()
        hero_icon.setPixmap(icon("shield-check", "#2f6df6", 42).pixmap(42, 42))
        title = QLabel("Safety comes before space")
        title.setObjectName("OnboardingTitle")
        description = QLabel("Every finding has one of three deterministic risk levels.")
        description.setObjectName("SectionDescription")
        layout.addWidget(hero_icon)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(8)

        risks = [
            ("Safe", "Selected by default and eligible for Recycle Bin cleanup."),
            ("Review", "Shown for your decision and never cleaned automatically."),
            ("Protected", "Cannot be selected or deleted by DiskWise."),
        ]
        for risk, detail in risks:
            row = QFrame()
            row.setProperty("class", "OnboardingRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(16, 16, 16, 16)
            row_layout.setSpacing(16)
            badge = risk_badge(risk)
            badge.setFixedWidth(92)
            label = QLabel(detail)
            label.setObjectName("MutedText")
            label.setWordWrap(True)
            row_layout.addWidget(badge)
            row_layout.addWidget(label, 1)
            layout.addWidget(row)
        layout.addStretch()
        return page

    def _scan_mode_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)

        hero_icon = QLabel()
        hero_icon.setPixmap(icon("scan-search", "#2f6df6", 42).pixmap(42, 42))
        title = QLabel("Choose your first scan")
        title.setObjectName("OnboardingTitle")
        description = QLabel(
            "Quick focuses on cache and temporary files. Deep also reviews Downloads, large files, and duplicates."
        )
        description.setObjectName("SectionDescription")
        description.setWordWrap(True)
        layout.addWidget(hero_icon)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(12)
        layout.addWidget(self.mode_control, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(
            self._feature_row(
                "zap", "Quick scan", "The best first run for routine cleanup and fast results."
            )
        )
        layout.addWidget(
            self._feature_row(
                "search", "Deep scan", "A broader review that can take longer and never auto-selects personal files."
            )
        )
        layout.addStretch()
        return page

    def _back(self) -> None:
        self.pages.setCurrentIndex(max(0, self.pages.currentIndex() - 1))
        self._sync_controls()

    def _next(self) -> None:
        if self.pages.currentIndex() < self.pages.count() - 1:
            self.pages.setCurrentIndex(self.pages.currentIndex() + 1)
            self._sync_controls()
            return
        self.start_scan_requested = True
        self._finish()

    def _skip(self) -> None:
        self._finish()

    def _finish(self) -> None:
        self.settings_service.set_scan_mode(self.mode_control.value())
        self.settings_service.set_onboarding_completed(True)
        self.accept()

    def _sync_controls(self) -> None:
        index = self.pages.currentIndex()
        self.step_label.setText(f"{index + 1} of {self.pages.count()}")
        self.back_button.setVisible(index > 0)
        self.skip_button.setVisible(index < self.pages.count() - 1)
        self.next_button.setText("Start Scan" if index == self.pages.count() - 1 else "Next")
        self.next_button.setIcon(
            icon("scan-search" if index == self.pages.count() - 1 else "arrow-right", "#ffffff")
        )
