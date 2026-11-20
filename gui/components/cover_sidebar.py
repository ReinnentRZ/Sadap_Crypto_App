"""Sidebar navigator for the public cover dashboard."""
from PyQt6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem

from PyQt6.QtCore import pyqtSignal


class CoverSidebar(QListWidget):
    """Compact mission-style navigation list."""

    page_selected = pyqtSignal(str)

    def __init__(self, items: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self._keys = [key for key, _ in items]

        for _, label in items:
            self.addItem(QListWidgetItem(label))

        self.setFixedWidth(210)
        self.setSpacing(2)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setStyleSheet(
            """
            QListWidget {
                background-color: #0F172A;
                border: none;
                border-radius: 8px;
                padding: 10px 6px;
                color: #CBD5E1;
                font-size: 13px;
                font-weight: 600;
            }
            QListWidget::item {
                padding: 11px 12px;
                border-radius: 6px;
                margin: 1px 2px;
            }
            QListWidget::item:hover {
                background-color: #1E293B;
                color: #E2E8F0;
            }
            QListWidget::item:selected {
                background-color: #0284C7;
                color: #FFFFFF;
                border-left: 3px solid #38BDF8;
            }
            """
        )

        self.setCurrentRow(0)
        self.currentRowChanged.connect(self._emit_selection)

    def _emit_selection(self, row: int) -> None:
        if 0 <= row < len(self._keys):
            self.page_selected.emit(self._keys[row])

    def select(self, key: str) -> None:
        """Programmatically highlight a page without emitting a duplicate signal."""
        if key not in self._keys:
            return
        target = self._keys.index(key)
        if self.currentRow() != target:
            self.blockSignals(True)
            self.setCurrentRow(target)
            self.blockSignals(False)
