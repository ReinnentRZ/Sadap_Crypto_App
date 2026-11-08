"""
AeroSat GroundStation - Tab 4: Encrypted Database Vault
Displays and manages records stored with transparent AES-256 field-level encryption.
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QHeaderView,
    QMessageBox,
    QInputDialog,
)
from PyQt6.QtCore import Qt
import datetime

from core.database.db_manager import get_vault_db
from core.utils.logger import get_logger

logger = get_logger("TabDBVault")


class TabDatabaseVault(QWidget):
    """GUI tab for exploring encrypted SQLite database."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_vault_db()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header Info Banner
        top_bar = QHBoxLayout()
        header_label = QLabel("🛡️ Local Encrypted Vault (SQLite with AES-256-GCM Field-Level Encryption)")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #0284C7;")
        top_bar.addWidget(header_label)

        top_bar.addStretch()
        self.btn_refresh = QPushButton("🔄 Refresh Vault")
        self.btn_refresh.clicked.connect(self.refresh_all_tables)
        top_bar.addWidget(self.btn_refresh)

        self.btn_add_memo = QPushButton("➕ New Classified Memo")
        self.btn_add_memo.clicked.connect(self._add_memo_dialog)
        top_bar.addWidget(self.btn_add_memo)
        layout.addLayout(top_bar)

        # Sub Tab Widget
        self.sub_tabs = QTabWidget()

        # 1. Memos Table
        self.memos_table = QTableWidget()
        self.memos_table.setColumnCount(5)
        self.memos_table.setHorizontalHeaderLabels(["ID", "Title", "Decrypted Content", "Author", "Created Date"])
        self.memos_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.sub_tabs.addTab(self.memos_table, "📝 Classified Memos")

        # 2. Files Catalog Table
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(["ID", "Decrypted Filename", "Disk Path", "Size", "SHA-256 Fingerprint"])
        self.files_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.sub_tabs.addTab(self.files_table, "📁 Encrypted Files Catalog")

        # 3. Stego Records Table
        self.stego_table = QTableWidget()
        self.stego_table.setColumnCount(5)
        self.stego_table.setHorizontalHeaderLabels(["ID", "Image Path", "Secret Preview", "Payload Size", "PSNR Metric"])
        self.stego_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.sub_tabs.addTab(self.stego_table, "🛰️ Stego Records")

        # 4. Audit Logs Table
        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(5)
        self.audit_table.setHorizontalHeaderLabels(["ID", "Event Type", "Decrypted Event Details", "Operator", "Timestamp"])
        self.audit_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.sub_tabs.addTab(self.audit_table, "🛡️ Security Audit Logs")

        layout.addWidget(self.sub_tabs)

        # Action bar
        act_bar = QHBoxLayout()
        self.btn_delete_memo = QPushButton("🗑️ Delete Selected Memo")
        self.btn_delete_memo.setObjectName("secondaryBtn")
        self.btn_delete_memo.clicked.connect(self._delete_selected_memo)
        act_bar.addWidget(self.btn_delete_memo)

        act_bar.addStretch()
        self.status_lbl = QLabel("Vault loaded. All sensitive fields decrypted transparently.")
        self.status_lbl.setStyleSheet("color: #64748B; font-weight: 600; font-size: 11px;")
        act_bar.addWidget(self.status_lbl)
        layout.addLayout(act_bar)

        self.refresh_all_tables()

    def refresh_all_tables(self):
        """Reload all data from database."""
        self._load_memos()
        self._load_files()
        self._load_stego()
        self._load_audit()

    def _load_memos(self):
        memos = self.db.list_memos()
        self.memos_table.setRowCount(len(memos))
        for row, m in enumerate(memos):
            self.memos_table.setItem(row, 0, QTableWidgetItem(str(m["id"])))
            self.memos_table.setItem(row, 1, QTableWidgetItem(m["title"]))
            self.memos_table.setItem(row, 2, QTableWidgetItem(m["content"]))
            self.memos_table.setItem(row, 3, QTableWidgetItem(m["author"]))
            dt = datetime.datetime.fromtimestamp(m["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
            self.memos_table.setItem(row, 4, QTableWidgetItem(dt))

    def _load_files(self):
        files = self.db.list_file_records()
        self.files_table.setRowCount(len(files))
        for row, f in enumerate(files):
            self.files_table.setItem(row, 0, QTableWidgetItem(str(f["id"])))
            self.files_table.setItem(row, 1, QTableWidgetItem(f["original_filename"]))
            self.files_table.setItem(row, 2, QTableWidgetItem(f["file_path"]))
            self.files_table.setItem(row, 3, QTableWidgetItem(f"{f['file_size']/1024:.1f} KB"))
            self.files_table.setItem(row, 4, QTableWidgetItem(f["file_sha256"]))

    def _load_stego(self):
        records = self.db.list_stego_records()
        self.stego_table.setRowCount(len(records))
        for row, s in enumerate(records):
            self.stego_table.setItem(row, 0, QTableWidgetItem(str(s["id"])))
            self.stego_table.setItem(row, 1, QTableWidgetItem(s["image_path"]))
            self.stego_table.setItem(row, 2, QTableWidgetItem(s["secret_preview"]))
            self.stego_table.setItem(row, 3, QTableWidgetItem(f"{s['payload_size']} B"))
            self.stego_table.setItem(row, 4, QTableWidgetItem(f"{s['psnr_db']:.2f} dB"))

    def _load_audit(self):
        logs = self.db.list_audit_logs(limit=50)
        self.audit_table.setRowCount(len(logs))
        for row, a in enumerate(logs):
            self.audit_table.setItem(row, 0, QTableWidgetItem(str(a["id"])))
            self.audit_table.setItem(row, 1, QTableWidgetItem(a["event_type"]))
            self.audit_table.setItem(row, 2, QTableWidgetItem(a["details"]))
            self.audit_table.setItem(row, 3, QTableWidgetItem(a["operator"]))
            dt = datetime.datetime.fromtimestamp(a["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            self.audit_table.setItem(row, 4, QTableWidgetItem(dt))

    def _add_memo_dialog(self):
        title, ok1 = QInputDialog.getText(self, "New Classified Memo", "Memo Title:")
        if not ok1 or not title.strip():
            return
        content, ok2 = QInputDialog.getMultiLineText(self, "New Classified Memo", "Secret Content:")
        if not ok2 or not content.strip():
            return

        self.db.add_memo(title.strip(), content.strip(), author="OPERATOR-ALPHA")
        self.refresh_all_tables()
        QMessageBox.information(self, "Success", "Memo added and encrypted into SQLite database.")

    def _delete_selected_memo(self):
        selected = self.memos_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Warning", "Please select a memo row to delete.")
            return

        memo_id_item = self.memos_table.item(selected, 0)
        if memo_id_item:
            memo_id = int(memo_id_item.text())
            confirm = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Permanently delete classified memo #{memo_id}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self.db.delete_memo(memo_id)
                self.refresh_all_tables()
