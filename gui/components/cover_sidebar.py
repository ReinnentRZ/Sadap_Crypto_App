"""Sidebar navigator for the public cover dashboard."""
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class CoverSidebar(QFrame):
    """Modern light sidebar with brand header and navigation list."""

    page_selected = pyqtSignal(str)

    def __init__(self, items: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self._keys = [key for key, _ in items]
        self.setObjectName("sidebarFrame")
        self.setFixedWidth(248)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(12)

        # Brand/header
        brand = QWidget()
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(8, 4, 8, 8)
        brand_layout.setSpacing(2)

        badge = QLabel("SG")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(36, 36)
        badge.setStyleSheet(
            "background-color: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; "
            "border-radius: 10px; font-size: 13px; font-weight: 700;"
        )
        title = QLabel("Sadap GroundStation")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #1E293B;")
        subtitle = QLabel("Observation Console")
        subtitle.setStyleSheet("font-size: 11px; color: #64748B;")

        header_row = QWidget()
        header_row_layout = QVBoxLayout(header_row)
        header_row_layout.setContentsMargins(0, 0, 0, 0)
        header_row_layout.setSpacing(0)

        # icon + text inline
        from PyQt6.QtWidgets import QHBoxLayout
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(10)
        top.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        text_col.addWidget(title)
        text_col.addWidget(subtitle)
        top.addLayout(text_col, 1)
        brand_layout.addLayout(top)
        layout.addWidget(brand)

        nav_label = QLabel("NAVIGATION")
        nav_label.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px; padding: 4px 8px;"
        )
        layout.addWidget(nav_label)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("sidebarNav")
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget.setSpacing(2)
        self.list_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        for _, label in items:
            item = QListWidgetItem(label)
            self.list_widget.addItem(item)

        self.list_widget.setCurrentRow(0)
        self.list_widget.currentRowChanged.connect(self._emit_selection)
        layout.addWidget(self.list_widget, 1)

        # Footer
        footer = QLabel("v2.4 · Authorized Access")
        footer.setAlignment(Qt.AlignmentFlag.AlignLeft)
        footer.setStyleSheet("font-size: 11px; color: #94A3B8; padding: 8px 8px 2px 8px;")
        layout.addWidget(footer)

    def _emit_selection(self, row: int) -> None:
        if 0 <= row < len(self._keys):
            self.page_selected.emit(self._keys[row])

    def select(self, key: str) -> None:
        """Programmatically highlight a page without emitting a duplicate signal."""
        if key not in self._keys:
            return
        target = self._keys.index(key)
        if self.list_widget.currentRow() != target:
            self.list_widget.blockSignals(True)
            self.list_widget.setCurrentRow(target)
            self.list_widget.blockSignals(False)

    # Compatibility helpers for code that may expect QListWidget-like behavior
    def setCurrentRow(self, row: int) -> None:
        self.list_widget.setCurrentRow(row)

    def currentRow(self) -> int:
        return self.list_widget.currentRow()
