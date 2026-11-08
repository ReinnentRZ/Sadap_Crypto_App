"""
Sadap GroundStation - PasswordLineEdit Component
Reusable QLineEdit widget with an embedded show/hide password action toggle.
Features vector-rendered Eye Open (show) and Eye Closed (hide) icons.
"""
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtGui import QAction, QIcon, QPixmap, QPainter, QPen, QColor, QPainterPath
from PyQt6.QtCore import Qt, QPointF


def create_eye_icon(open_eye: bool = True, size: int = 22) -> QPixmap:
    """
    Render vector-sharp Eye Open or Eye Closed icon on transparent QPixmap.
    - open_eye=True: Mata Terbuka (Open eye with colored iris)
    - open_eye=False: Mata Tertutup (Closed eyelid with lashes)
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    scale = size / 24.0
    painter.scale(scale, scale)

    if open_eye:
        # Mata Terbuka (Open Eye)
        path = QPainterPath()
        path.moveTo(2.5, 12)
        path.quadTo(12, 4.5, 21.5, 12)
        path.quadTo(12, 19.5, 2.5, 12)
        pen_outline = QPen(QColor("#64748B"), 1.8)
        pen_outline.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen_outline.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen_outline)
        painter.drawPath(path)

        # Iris / Pupil
        painter.setBrush(QColor("#0284C7"))  # Sky Blue accent
        painter.setPen(QPen(QColor("#0369A1"), 1.4))
        painter.drawEllipse(QPointF(12, 12), 3.3, 3.3)

        # Light Glint
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(13.2, 10.7), 1.0, 1.0)
    else:
        # Mata Tertutup (Closed Eyelid with Lashes)
        pen = QPen(QColor("#64748B"), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # Eyelid arc
        path = QPainterPath()
        path.moveTo(3.0, 11.5)
        path.quadTo(12, 17.5, 21.0, 11.5)
        painter.drawPath(path)

        # Lashes radiating down
        painter.drawLine(QPointF(5.0, 13.0), QPointF(3.5, 17.0))
        painter.drawLine(QPointF(8.5, 15.0), QPointF(8.0, 19.5))
        painter.drawLine(QPointF(12.0, 16.0), QPointF(12.0, 20.8))
        painter.drawLine(QPointF(15.5, 15.0), QPointF(16.0, 19.5))
        painter.drawLine(QPointF(19.0, 13.0), QPointF(20.5, 17.0))

    painter.end()
    return pix


class PasswordLineEdit(QLineEdit):
    """
    A modern password input line edit with an integrated show/hide password toggle.
    Displays Mata Tertutup when password is masked, and Mata Terbuka when password is revealed.
    """

    def __init__(self, parent=None, placeholder: str = ""):
        super().__init__(parent)
        if placeholder:
            self.setPlaceholderText(placeholder)

        self.setEchoMode(QLineEdit.EchoMode.Password)
        self._is_password_visible = False

        # Pre-render icons
        self._icon_closed = QIcon(create_eye_icon(open_eye=False))
        self._icon_open = QIcon(create_eye_icon(open_eye=True))

        # Trailing action inside QLineEdit
        self.toggle_action = QAction(self)
        self.toggle_action.setIcon(self._icon_closed)
        self.toggle_action.setToolTip("Tampilkan password (Show)")
        self.toggle_action.triggered.connect(self.toggle_password_visibility)
        self.addAction(self.toggle_action, QLineEdit.ActionPosition.TrailingPosition)

    def toggle_password_visibility(self):
        """Toggle between EchoMode.Password (closed eye) and EchoMode.Normal (open eye)."""
        if self._is_password_visible:
            self.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_action.setIcon(self._icon_closed)
            self.toggle_action.setToolTip("Tampilkan password (Show)")
            self._is_password_visible = False
        else:
            self.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_action.setIcon(self._icon_open)
            self.toggle_action.setToolTip("Sembunyikan password (Hide)")
            self._is_password_visible = True
