import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QScrollArea, QGridLayout, 
    QMessageBox, QComboBox, QTabWidget, QSplitter, QProgressBar, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QAction

# Import Shared Core
from app_shared import (
    WindowsEffect, get_theme_manager, AnimatedButton, PDFEngine, 
    PROFILES, get_system_accent_color, FullPageDialog, merge_pdfs
)
from ai_core import ModelManager

class TrainerPageCard(QWidget):
    clicked = pyqtSignal(int)
    right_clicked = pyqtSignal(int)
    
    def __init__(self, page_num, pixmap, prediction=None, parent=None):
        super().__init__(parent)
        self.page_num = page_num
        self.selected = False
        self.prediction = prediction 
        
        self.setFixedSize(160, 240)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Image
        self.img_lbl = QLabel()
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.setPixmap(pixmap.scaled(140, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.img_lbl)
        
        # Page Number
        self.lbl = QLabel(f"Pág {page_num + 1}")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setStyleSheet("font-size: 11px; color: #888;")
        layout.addWidget(self.lbl)
        
        # Prediction Label
        self.pred_lbl = QLabel()
        self.pred_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pred_lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
        if prediction:
            self.pred_lbl.setText(f"IA: {prediction}")
        else:
            self.pred_lbl.setText("")
        layout.addWidget(self.pred_lbl)
        
        self._update_style()
        
    def set_selected(self, val):
        self.selected = val
        self._update_style()
        
    def set_prediction(self, text):
        self.prediction = text
        self.pred_lbl.setText(f"IA: {text}")
        
    def _update_style(self):
        tm = get_theme_manager()
        t = tm.get_theme()
        
        if self.selected:
            self.setStyleSheet(f"background-color: {t['primary']}; border-radius: 8px; color: white;")
            self.pred_lbl.setStyleSheet("color: white; font-weight: bold;")
            self.lbl.setStyleSheet("color: rgba(255,255,255,0.8);")
        else:
            border_col = t['border']
            bg_col = t['surface']
            self.setStyleSheet(f"background-color: {bg_col}; border-radius: 8px; border: 1px solid {border_col};")
            self.pred_lbl.setStyleSheet(f"color: {t['accent']}; font-weight: bold;")
            self.lbl.setStyleSheet(f"color: {t['text_secondary']};")
            
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.page_num)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.page_num)

class TrainerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Entrenador de IA - ClasificadorPDF")
        self.resize(1100, 750)
        
        # Init Managers
        self.mgr = ModelManager()
        self.engine = None
        
        # State for separate tabs
        self.teach_cards = []
        self.teach_selected = set()
        
        self.test_cards = []
        self.test_selected = set()
        self.test_engine = None 
        
        # Theme
        tm = get_theme_manager()
        tm.auto_theme = True 
        tm.transparency_mode = "mica"
        self.setStyleSheet(tm.get_stylesheet())
        
        # UI
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Top Bar
        top_bar = QWidget()
        top_bar.setStyleSheet(f"background-color: {tm.get_theme()['surface']}; border-bottom: 1px solid {tm.get_theme()['border']};")
        top_layout = QHBoxLayout(top_bar)
        top_layout.addWidget(QLabel("🧠 Entrenador Maestro"))
        top_layout.addStretch()
        reset_btn = AnimatedButton("🗑 Reiniciar Memoria IA")
        reset_btn.clicked.connect(self._reset_memory)
        top_layout.addWidget(reset_btn)
        main_layout.addWidget(top_bar)
        
        # 2. Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        self._init_teach_tab()
        self._init_test_tab()
        
        # Effects
        try:
            WindowsEffect.apply_best_effect(int(self.winId()), dark_mode=True)
        except: pass
        
    def _init_teach_tab(self):
        teach_widget = QWidget()
        self.tabs.addTab(teach_widget, "👨‍🏫 Enseñar (Entrenamiento)")
        layout = QHBoxLayout(teach_widget)
        
        # Sidebar
        panel = QWidget()
        panel.setFixedWidth(280)
        v = QVBoxLayout(panel)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(15)
        
        v.addWidget(QLabel("<b>Modo Entrenamiento</b>"))
        v.addWidget(QLabel("1. Cargar PDF:"))
        btn = AnimatedButton("📂 Abrir PDF")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self._open_teach_pdf)
        v.addWidget(btn)
        
        v.addWidget(QLabel("2. Categoría Correcta:"))
        self.teach_combo = QComboBox()
        self._populate_combo(self.teach_combo)
        v.addWidget(self.teach_combo)
        
        v.addSpacing(10)
        self.teach_btn = AnimatedButton("🧠 MEMORIZAR SELECCIÓN")
        self.teach_btn.clicked.connect(self._learn_teach_selection)
        self.teach_btn.setEnabled(False)
        v.addWidget(self.teach_btn)
        
        self.teach_status = QLabel("Listo.")
        self.teach_status.setWordWrap(True)
        v.addWidget(self.teach_status)
        v.addWidget(QLabel("<small>Clic Der: Ver página completa</small>"))
        v.addStretch()
        layout.addWidget(panel)
        
        # Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.teach_grid_widget = QWidget()
        self.teach_grid = QGridLayout(self.teach_grid_widget)
        scroll.setWidget(self.teach_grid_widget)
        layout.addWidget(scroll)

    def _init_test_tab(self):
        test_widget = QWidget()
        self.tabs.addTab(test_widget, "🧪 Probar y Corregir (Active Learning)")
        layout = QHBoxLayout(test_widget)
        
        # Sidebar
        panel = QWidget()
        panel.setFixedWidth(280)
        v = QVBoxLayout(panel)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(15)
        
        v.addWidget(QLabel("<b>Modo Prueba Activa</b>"))
        v.addWidget(QLabel("1. Cargar PDF para Test:"))
        btn = AnimatedButton("📂 Abrir PDF de Prueba")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self._open_test_pdf)
        v.addWidget(btn)
        
        v.addWidget(QLabel("2. Si la IA se equivoca:"))
        v.addWidget(QLabel("Selecciona las páginas erradas y elige la categoría real:"))
        
        self.test_combo = QComboBox()
        self._populate_combo(self.test_combo)
        v.addWidget(self.test_combo)
        
        self.correct_btn = AnimatedButton("✅ CORREGIR Y APRENDER")
        self.correct_btn.clicked.connect(self._correct_test_selection)
        self.correct_btn.setEnabled(False)
        self.correct_btn.setStyleSheet("background-color: #10B981; color: white;") 
        v.addWidget(self.correct_btn)
        
        self.test_progress = QProgressBar()
        self.test_progress.setVisible(False)
        v.addWidget(self.test_progress)
        
        self.test_status = QLabel("Carga un PDF para ver predicciones.")
        self.test_status.setWordWrap(True)
        v.addWidget(self.test_status)
        v.addWidget(QLabel("<small>Clic Der: Ver página completa</small>"))
        
        # Quick Text Test
        v.addSpacing(20)
        v.addWidget(QLabel("Prueba Rápida (Texto):"))
        self.txt_test = QTextEdit()
        self.txt_test.setMaximumHeight(80)
        self.txt_test.textChanged.connect(self._text_test)
        v.addWidget(self.txt_test)
        self.txt_res = QLabel("...")
        v.addWidget(self.txt_res)
        
        v.addStretch()
        layout.addWidget(panel)
        
        # Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.test_grid_widget = QWidget()
        self.test_grid = QGridLayout(self.test_grid_widget)
        scroll.setWidget(self.test_grid_widget)
        layout.addWidget(scroll)

    def _populate_combo(self, combo):
        cats = []
        for profile in PROFILES.values():
            for abbr, name in profile["CATEGORIES"]:
                cats.append(f"{abbr} - {name}")
        combo.addItems(sorted(list(set(cats))))

    # --- TEACH TAB LOGIC ---
    def _open_teach_pdf(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Abrir PDF(s) para Entrenar", "", "PDF Files (*.pdf)")
        if not paths: return
        
        path_to_load = None
        if len(paths) == 1:
            path_to_load = paths[0]
        else:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.teach_status.setText("Fusionando PDFs...")
            QApplication.processEvents()
            try:
                merged = merge_pdfs(paths)
                if merged:
                    path_to_load = merged
                else:
                    QMessageBox.warning(self, "Error", "No se pudieron fusionar los archivos.")
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
            finally:
                QApplication.restoreOverrideCursor()
        
        if not path_to_load: return
        
        self.teach_status.setText("Cargando...")
        QApplication.processEvents()
        
        if self.engine: self.engine.close()
        self.engine = PDFEngine(path_to_load)
        
        self._clear_layout(self.teach_grid)
        self.teach_cards = []
        self.teach_selected = set()
        
        for i in range(self.engine.doc.page_count):
            pix = self.engine.get_page_preview(i, 0.2)
            if pix:
                card = TrainerPageCard(i, pix)
                card.clicked.connect(self._on_teach_click)
                card.right_clicked.connect(lambda p: self._show_full_page(self.engine, p))
                self.teach_grid.addWidget(card, i // 4, i % 4)
                self.teach_cards.append(card)
        self.teach_status.setText(f"Listo: {os.path.basename(path_to_load)}")

    def _on_teach_click(self, page_num):
        if page_num in self.teach_selected:
            self.teach_selected.remove(page_num)
        else:
            self.teach_selected.add(page_num)
        for c in self.teach_cards:
            c.set_selected(c.page_num in self.teach_selected)
        self.teach_btn.setEnabled(len(self.teach_selected) > 0)
        self.teach_btn.setText(f"🧠 MEMORIZAR ({len(self.teach_selected)})")

    def _learn_teach_selection(self):
        cat = self.teach_combo.currentText().split(" - ")[0]
        self._learn_pages(self.engine, self.teach_selected, cat, self.teach_status)
        self.teach_selected = set()
        for c in self.teach_cards: c.set_selected(False)
        self.teach_btn.setEnabled(False)

    # --- TEST TAB LOGIC ---
    def _open_test_pdf(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Abrir PDF(s) de Prueba", "", "PDF Files (*.pdf)")
        if not paths: return
        
        path_to_load = None
        if len(paths) == 1:
            path_to_load = paths[0]
        else:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.test_status.setText("Fusionando PDFs...")
            QApplication.processEvents()
            try:
                merged = merge_pdfs(paths)
                if merged:
                    path_to_load = merged
                else:
                    QMessageBox.warning(self, "Error", "No se pudieron fusionar los archivos.")
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
            finally:
                QApplication.restoreOverrideCursor()

        if not path_to_load: return
        
        self.test_status.setText("Analizando PDF...")
        self.test_progress.setVisible(True)
        self.test_progress.setValue(0)
        QApplication.processEvents()
        
        if self.test_engine: self.test_engine.close()
        self.test_engine = PDFEngine(path_to_load)
        
        self._clear_layout(self.test_grid)
        self.test_cards = []
        self.test_selected = set()
        
        total = self.test_engine.doc.page_count
        self.test_progress.setMaximum(total)
        
        for i in range(total):
            # 1. Get Image
            pix = self.test_engine.get_page_preview(i, 0.2)
            
            # 2. Predict (Auto)
            page = self.test_engine.doc.load_page(i)
            text = page.get_text("text")
            pred = self.mgr.predict(text)
            
            # 3. Create Card
            if pix:
                card = TrainerPageCard(i, pix, prediction=pred)
                card.clicked.connect(self._on_test_click)
                card.right_clicked.connect(lambda p: self._show_full_page(self.test_engine, p))
                self.test_grid.addWidget(card, i // 4, i % 4)
                self.test_cards.append(card)
            
            self.test_progress.setValue(i + 1)
            QApplication.processEvents()
            
        self.test_progress.setVisible(False)
        self.test_status.setText(f"Análisis completo: {os.path.basename(path_to_load)}")

    def _on_test_click(self, page_num):
        if page_num in self.test_selected:
            self.test_selected.remove(page_num)
        else:
            self.test_selected.add(page_num)
        
        for c in self.test_cards:
            c.set_selected(c.page_num in self.test_selected)
            
        self.correct_btn.setEnabled(len(self.test_selected) > 0)
        self.correct_btn.setText(f"✅ CORREGIR ({len(self.test_selected)})")

    def _correct_test_selection(self):
        cat = self.test_combo.currentText().split(" - ")[0]
        self._learn_pages(self.test_engine, self.test_selected, cat, self.test_status)
        
        # Update UI to reflect "Correction"
        for page_num in self.test_selected:
            for c in self.test_cards:
                if c.page_num == page_num:
                    c.set_prediction(f"{cat} (Corregido)")
                    c.set_selected(False)
        
        self.test_selected = set()
        self.correct_btn.setEnabled(False)
        QMessageBox.information(self, "Corregido", f"La IA ha aprendido que estas páginas son '{cat}'.")

    # --- SHARED HELPERS ---
    def _learn_pages(self, engine, pages, category, status_lbl):
        count = 0
        for page_num in pages:
            page = engine.doc.load_page(page_num)
            text = page.get_text("text")
            if len(text.strip()) > 10:
                self.mgr.learn(text, category)
                count += 1
            QApplication.processEvents()
        status_lbl.setText(f"Aprendidas {count} páginas como {category}.")
        
    def _show_full_page(self, engine, page_num):
        if not engine: return
        dlg = FullPageDialog(engine, page_num, self)
        dlg.exec()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _reset_memory(self):
        if QMessageBox.question(self, "Reset", "¿Borrar memoria?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.mgr.data = []
            self.mgr._save_data()
            self.mgr.model = None
            QMessageBox.information(self, "Reset", "Memoria borrada.")
            
    def _text_test(self):
        txt = self.txt_test.toPlainText()
        pred = self.mgr.predict(txt)
        self.txt_res.setText(f"Pred: {pred}" if pred else "...")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TrainerWindow()
    window.show()
    sys.exit(app.exec())
