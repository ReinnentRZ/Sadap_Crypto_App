"""
AeroSat GroundStation - Tab 5: Blockchain Ledger Explorer
Visualizes immutable blocks, Proof of Work mining, and audit chain verification.
"""
import json
import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QTextEdit,
    QHeaderView,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt

from core.blockchain.chain import get_blockchain
from core.blockchain.asset_tracker import AssetTracker
from core.utils.logger import get_logger

logger = get_logger("TabBlockchain")


class TabBlockchainView(QWidget):
    """GUI tab for viewing blocks, mining, and auditing chain integrity."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.blockchain = get_blockchain()
        self.tracker = AssetTracker(self.blockchain)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Top Metric Banner & Controls
        top_bar = QHBoxLayout()

        self.metric_label = QLabel(f"⛓️ Blocks: {len(self.blockchain.chain)} | PoW Target: '000' (Difficulty {self.blockchain.difficulty})")
        self.metric_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #0284C7;")
        top_bar.addWidget(self.metric_label)

        top_bar.addStretch()

        self.btn_audit_chain = QPushButton("🛡️ Audit Chain Integrity")
        self.btn_audit_chain.setStyleSheet("background-color: #059669;")
        self.btn_audit_chain.clicked.connect(self._audit_chain)
        top_bar.addWidget(self.btn_audit_chain)

        self.btn_notarize_file = QPushButton("📜 Notarize File...")
        self.btn_notarize_file.setObjectName("secondaryBtn")
        self.btn_notarize_file.clicked.connect(self._notarize_file_dialog)
        top_bar.addWidget(self.btn_notarize_file)

        self.btn_mine = QPushButton("⛏️ Mine Heartbeat Block")
        self.btn_mine.clicked.connect(self._mine_new_block)
        top_bar.addWidget(self.btn_mine)

        layout.addLayout(top_bar)

        # Blocks Table
        self.blocks_table = QTableWidget()
        self.blocks_table.setColumnCount(6)
        self.blocks_table.setHorizontalHeaderLabels([
            "Index", "Timestamp", "Nonce", "Previous Hash", "Block Hash (SHA-256)", "Transactions"
        ])
        self.blocks_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.blocks_table.itemSelectionChanged.connect(self._on_block_selected)
        layout.addWidget(self.blocks_table, stretch=2)

        # Block Inspector Detail Panel
        inspector_group = QGroupBox("Selected Block Payload Inspector")
        insp_layout = QVBoxLayout(inspector_group)
        self.block_detail_view = QTextEdit()
        self.block_detail_view.setReadOnly(True)
        self.block_detail_view.setPlaceholderText("Click any block above to inspect its transaction data and cryptographic signatures...")
        self.block_detail_view.setMaximumHeight(130)
        insp_layout.addWidget(self.block_detail_view)
        layout.addWidget(inspector_group, stretch=1)

        self.refresh_blocks_view()

    def refresh_blocks_view(self):
        """Populate table with all blocks in chain."""
        chain = self.blockchain.chain
        self.metric_label.setText(
            f"⛓️ Blocks: {len(chain)} | PoW Target: {'0'*self.blockchain.difficulty} | Status: Online"
        )
        self.blocks_table.setRowCount(len(chain))

        for row, b in enumerate(chain):
            self.blocks_table.setItem(row, 0, QTableWidgetItem(f"#{b.index}"))
            dt = datetime.datetime.fromtimestamp(b.timestamp).strftime("%Y-%m-%d %H:%M:%S")
            self.blocks_table.setItem(row, 1, QTableWidgetItem(dt))
            self.blocks_table.setItem(row, 2, QTableWidgetItem(str(b.nonce)))
            self.blocks_table.setItem(row, 3, QTableWidgetItem(f"{b.previous_hash[:12]}..."))

            hash_item = QTableWidgetItem(b.hash)
            hash_item.setForeground(Qt.GlobalColor.darkGreen if b.hash.startswith("0"*self.blockchain.difficulty) else Qt.GlobalColor.red)
            self.blocks_table.setItem(row, 4, hash_item)

            tx_count = len(b.data) if isinstance(b.data, list) else 1
            self.blocks_table.setItem(row, 5, QTableWidgetItem(f"{tx_count} TX(s)"))

        # Select latest block
        if chain:
            self.blocks_table.selectRow(len(chain) - 1)

    def _on_block_selected(self):
        selected = self.blocks_table.currentRow()
        if 0 <= selected < len(self.blockchain.chain):
            block = self.blockchain.chain[selected]
            formatted_json = json.dumps(block.to_dict(), indent=2)
            self.block_detail_view.setPlainText(formatted_json)

    def _audit_chain(self):
        """Run full cryptographic chain verification."""
        is_valid, msg = self.blockchain.is_chain_valid()
        if is_valid:
            QMessageBox.information(
                self,
                "Audit Passed",
                f"✅ BLOCKCHAIN INTEGRITY VERIFIED!\n\n{msg}\nAll blocks are cryptographically intact and immutable."
            )
        else:
            QMessageBox.critical(
                self,
                "Security Alert",
                f"🚨 TAMPERING DETECTED!\n\n{msg}\nData modification has violated blockchain consensus!"
            )

    def _mine_new_block(self):
        self.blockchain.add_transaction({
            "action": "OPERATOR_HEARTBEAT_AUDIT",
            "operator": "AEROSAT-GROUND-CONSOLE",
            "status": "SECURE_NOMINAL"
        })
        new_block = self.blockchain.mine_pending_transactions(miner_callsign="CONSOLE-OPERATOR")
        self.refresh_blocks_view()
        QMessageBox.information(self, "Mined", f"Block #{new_block.index} successfully mined!\nHash: {new_block.hash}")

    def _notarize_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Notarize on Blockchain", "", "All Files (*.*)")
        if file_path:
            p = Path(file_path)
            ok, msg, info = self.tracker.register_file_asset(p, p.name, owner_callsign="COMMANDER-ALPHA")
            if ok:
                self.refresh_blocks_view()
                QMessageBox.information(
                    self,
                    "Notarization Success",
                    f"Asset '{p.name}' anchored to Blockchain in Block #{info.get('block_index')}!\n\nSHA-256: {info.get('file_sha256')}"
                )
            else:
                QMessageBox.critical(self, "Error", msg)
