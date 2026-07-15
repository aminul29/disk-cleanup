from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from app.services.license_service import MockLicenseService
from app.ui.pricing_dialog import PricingDialog


def test_pricing_dialog_is_an_honest_non_transactional_placeholder() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = PricingDialog(MockLicenseService())

    labels = {label.text() for label in dialog.findChildren(QLabel)}
    assert {"Free", "Pro Monthly", "Pro Yearly"}.issubset(labels)
    assert "Purchases are not available in this release. No payment information is collected." in labels

    purchase_buttons = [
        button
        for button in dialog.findChildren(QPushButton)
        if button.text() in {"Current Plan", "Not Available Yet"}
    ]
    assert len(purchase_buttons) == 3
    assert all(not button.isEnabled() for button in purchase_buttons)

    dialog.deleteLater()
    app.processEvents()
