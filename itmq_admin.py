import sys
import os
import json
import itmq_license
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QFrame, QStackedWidget,
                             QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette

# --- CONFIG & STYLES ---
COLORS = {
    "BG": "#F5F2EB",
    "SIDEBAR": "#FFFFFF",
    "ACCENT": "#E67E22",
    "TEXT": "#2D3436",
    "TEXT_MUTED": "#636E72",
    "BORDER": "#E0E0E0",
    "WHITE": "#FFFFFF",
    "SUCCESS": "#27AE60"
}

ADMIN_DB_PATH = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), "ITMQ-GD", "admin_history.json")

class ModernButton(QPushButton):
    def __init__(self, text, primary=False):
        super().__init__(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(35)
        if primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS["ACCENT"]};
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                    padding: 0 15px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: #D35400;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS["TEXT"]};
                    border-radius: 6px;
                    padding: 0 15px;
                    border: 1px solid {COLORS["BORDER"]};
                }}
                QPushButton:hover {{
                    background-color: rgba(0,0,0,0.05);
                }}
            """)

class SidebarButton(QPushButton):
    def __init__(self, text, icon_text=""):
        super().__init__(text)
        self.setCheckable(True)
        self.setFixedHeight(45)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding-left: 20px;
                border: none;
                border-radius: 8px;
                color: {COLORS["TEXT_MUTED"]};
                font-weight: 500;
                font-size: 13px;
                background: transparent;
            }}
            QPushButton:hover {{
                background: rgba(230, 126, 34, 0.05);
                color: {COLORS["ACCENT"]};
            }}
            QPushButton:checked {{
                background: rgba(230, 126, 34, 0.1);
                color: {COLORS["ACCENT"]};
                font-weight: bold;
            }}
        """)

class AdminDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ITMQ License Admin v1.0")
        self.resize(1000, 650)
        self.setWindowIcon(QIcon("icon.png")) # Fallback
        
        self.history = self.load_history()
        self.setup_ui()
        
    def load_history(self):
        if os.path.exists(ADMIN_DB_PATH):
            try:
                with open(ADMIN_DB_PATH, "r") as f:
                    return json.load(f)
            except: pass
        return []

    def save_history(self):
        os.makedirs(os.path.dirname(ADMIN_DB_PATH), exist_ok=True)
        try:
            with open(ADMIN_DB_PATH, "w") as f:
                json.dump(self.history, f, indent=4)
        except: pass

    def setup_ui(self):
        # Main Widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- SIDEBAR ---
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background-color: {COLORS['SIDEBAR']}; border-right: 1px solid {COLORS['BORDER']};")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(15, 30, 15, 30)
        side_layout.setSpacing(10)
        
        logo = QLabel("ITMQ ADMIN")
        logo.setStyleSheet(f"color: {COLORS['ACCENT']}; font-size: 18px; font-weight: bold; margin-bottom: 20px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(logo)
        
        self.btn_gen = SidebarButton("Generador")
        self.btn_monitor = SidebarButton("Monitor")
        self.btn_audit = SidebarButton("Auditor")
        
        self.side_group = [self.btn_gen, self.btn_monitor, self.btn_audit]
        for btn in self.side_group:
            btn.clicked.connect(self.switch_page)
            side_layout.addWidget(btn)
        
        self.btn_gen.setChecked(True)
        side_layout.addStretch()
        
        footer_info = QLabel(f"Machine ID: {itmq_license.get_machine_id()[:8]}...")
        footer_info.setStyleSheet(f"color: {COLORS['TEXT_MUTED']}; font-size: 10px;")
        footer_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(footer_info)
        
        main_layout.addWidget(sidebar)
        
        # --- CONTENT AREA ---
        content_container = QStackedWidget()
        content_container.setStyleSheet(f"background-color: {COLORS['BG']};")
        
        # PAGES
        self.page_gen = self.create_gen_page()
        self.page_monitor = self.create_monitor_page()
        self.page_audit = self.create_audit_page()
        
        content_container.addWidget(self.page_gen)
        content_container.addWidget(self.page_monitor)
        content_container.addWidget(self.page_audit)
        
        self.content_stack = content_container
        main_layout.addWidget(content_container)

    def switch_page(self):
        btn = self.sender()
        for b in self.side_group: b.setChecked(False)
        btn.setChecked(True)
        
        if btn == self.btn_gen: self.content_stack.setCurrentIndex(0)
        elif btn == self.btn_monitor: 
            self.refresh_monitor()
            self.content_stack.setCurrentIndex(1)
        elif btn == self.btn_audit: self.content_stack.setCurrentIndex(2)

    # --- PAGE CREATORS ---
    def create_gen_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        title = QLabel("Generador de Licencias")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['TEXT']};")
        layout.addWidget(title)
        
        card = QFrame()
        card.setStyleSheet(f"background: white; border-radius: 12px; border: 1px solid {COLORS['BORDER']};")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(15)
        
        card_layout.addWidget(QLabel("Nombre del Cliente / Referencia"))
        self.input_note = QLineEdit()
        self.input_note.setPlaceholderText("Ej: Juan Perez - Dept. IT")
        self.input_note.setStyleSheet("padding: 10px; border: 1px solid #DDD; border-radius: 5px;")
        card_layout.addWidget(self.input_note)
        
        card_layout.addWidget(QLabel("Duración de la Licencia"))
        self.combo_duration = QComboBox()
        self.combo_duration.addItems(["7D (Prueba)", "30D (Mensual)", "90D (Trimestral)", "365D (Anual)", "LIFETIME (Vitalicia)"])
        self.combo_duration.setStyleSheet("padding: 8px; border: 1px solid #DDD; border-radius: 5px;")
        card_layout.addWidget(self.combo_duration)
        
        
        self.btn_generate = ModernButton("GENERAR LLAVE", primary=True)
        self.btn_generate.clicked.connect(self.do_generate)
        card_layout.addWidget(self.btn_generate)
        
        # Result section
        self.result_frame = QFrame()
        self.result_frame.hide()
        res_layout = QVBoxLayout(self.result_frame)
        res_layout.addWidget(QLabel("Llave Generada:"))
        self.output_key = QLineEdit()
        self.output_key.setReadOnly(True)
        self.output_key.setStyleSheet(f"font-family: 'Consolas'; font-size: 16px; color: {COLORS['ACCENT']}; font-weight: bold; padding: 10px; background: #F9F9F9;")
        res_layout.addWidget(self.output_key)
        
        btn_copy = ModernButton("Copiar al Portapapeles")
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(self.output_key.text()))
        res_layout.addWidget(btn_copy)
        
        # New Export Button
        btn_export = ModernButton("Copiar JSON para Servidor (Remoto)")
        btn_export.clicked.connect(self.do_export_json)
        res_layout.addWidget(btn_export)
        
        card_layout.addWidget(self.result_frame)
        layout.addWidget(card)
        layout.addStretch()
        return page

    def create_monitor_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        title = QLabel("Monitor de Licencias Emitidas")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['TEXT']};")
        layout.addWidget(title)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Fecha", "Cliente", "Acceso", "Tipo", "Llave Maestra"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(f"background: white; border: 1px solid {COLORS['BORDER']}; border-radius: 8px;")
        
        layout.addWidget(self.table)
        
        btn_clear = QPushButton("Limpiar Historial")
        btn_clear.clicked.connect(self.clear_history)
        layout.addWidget(btn_clear, alignment=Qt.AlignmentFlag.AlignRight)
        
        return page

    def create_audit_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        title = QLabel("Auditor de Integridad")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['TEXT']};")
        layout.addWidget(title)
        
        card = QFrame()
        card.setStyleSheet(f"background: white; border-radius: 12px; border: 1px solid {COLORS['BORDER']};")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        
        card_layout.addWidget(QLabel("Introducir Llave a Verificar"))
        self.audit_key = QLineEdit()
        self.audit_key.setStyleSheet("padding: 10px; border: 1px solid #DDD; border-radius: 5px;")
        card_layout.addWidget(self.audit_key)
        
        btn_check = ModernButton("VERIFICAR VALIDEZ", primary=True)
        btn_check.clicked.connect(self.do_audit)
        card_layout.addWidget(btn_check)
        
        self.audit_res = QLabel("")
        self.audit_res.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.audit_res.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 15px;")
        card_layout.addWidget(self.audit_res)
        
        layout.addWidget(card)
        layout.addStretch()
        return page

    # --- LOGIC ---
        # No HWID needed for universal keys
        
        dur_full = self.combo_duration.currentText()
        dtype = dur_full.split(" ")[0] # "30D", "90D" etc
        
        key = itmq_license.generate_key(dtype)
        self.output_key.setText(key)
        self.result_frame.show()
        
        # Save to history
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "client": self.input_note.text().strip() or "Anonimo",
            "hwid": "Universal",
            "type": dtype,
            "key": key
        }
        self.history.insert(0, entry)
        self.save_history()

    def refresh_monitor(self):
        self.table.setRowCount(0)
        for i, entry in enumerate(self.history):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(entry["date"]))
            self.table.setItem(i, 1, QTableWidgetItem(entry["client"]))
            self.table.setItem(i, 2, QTableWidgetItem(entry["hwid"]))
            self.table.setItem(i, 3, QTableWidgetItem(entry["type"]))
            self.table.setItem(i, 4, QTableWidgetItem(entry["key"]))

    def do_audit(self):
        key = self.audit_key.text().strip()
        
        if not key: return
        
        dtype = itmq_license.validate_key(key)
        if dtype:
            self.audit_res.setText(f"✅ VÁLIDA: Licencia {dtype}")
            self.audit_res.setStyleSheet(f"color: {COLORS['SUCCESS']}; font-weight: bold;")
        else:
            self.audit_res.setText("❌ INVÁLIDA: La llave no coincide con el ID")
            self.audit_res.setStyleSheet("color: #E74C3C; font-weight: bold;")

    def do_export_json(self):
        # We need the HWID for the online check, even if we generated a master key locally
        # Since the Admin dashboard is now master-key focused, we might need a manual HWID input 
        # specifically for this feature, OR we just use the generated key format.
        # But wait, online activation checks HWID against the JSON.
        # So we need to assist the admin in creating that JSON entry.
        
        # We'll ask for the client's HWID via a dialog since we removed the input field
        mock_hwid, ok = self.get_input_dialog("Online Activation", "Ingrese el Machine ID del cliente para autorizar:")
        if not ok or not mock_hwid: return

        dur_full = self.combo_duration.currentText()
        dtype = dur_full.split(" ")[0]
        
        section = f'"{mock_hwid.strip().upper()}": "{dtype}"'
        final_str = f"Agregue esto a su JSON:\n{section}"
        
        QApplication.clipboard().setText(section)
        QMessageBox.showinfo("Copiado", f"Se ha copiado el formato JSON al portapapeles:\n\n{section}\n\nAgréguelo a su archivo remoto 'licenses.json'.")

    def get_input_dialog(self, title, label):
        # Simple QInputDialog wrapper
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, title, label)
        return text, ok

    def clear_history(self):
        if QMessageBox.question(self, "Confirmar", "¿Eliminar todo el historial?") == QMessageBox.StandardButton.Yes:
            self.history = []
            self.save_history()
            self.refresh_monitor()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("ITMQ License Admin")
    
    # Simple Style tweaks for better look on Windows
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLORS["BG"]))
    app.setPalette(palette)
    
    window = AdminDashboard()
    window.show()
    sys.exit(app.exec())
