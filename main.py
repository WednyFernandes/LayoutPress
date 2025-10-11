"""Minimal GUI front-end for the Impositor class.

This file provides a compact, syntactically-clean PySide6 GUI that:
- loads an image or PDF
- allows resizing in mm with optional keep-proportion
- chooses bleed mode (Português labels)
- picks a solid bleed color
- shows a preview and exports an imposed PDF using Impositor
"""

from typing import Optional, Tuple
import io
import sys
import os
import subprocess
import tempfile

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QColorDialog,
    QCheckBox,
    QGroupBox,
    QSizePolicy,
)
from PySide6.QtGui import QPixmap, QImage, QIcon
from PySide6.QtCore import Qt, QTimer

from impositor import Impositor, PT_PER_MM
from PIL import Image
import fitz
import math


class MainWindow(QWidget):
    """Clean, minimal GUI for Impositor."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LayoutPress — Imposição Rápida")
        self.impositor = Impositor()
        # support single or multiple source pages/images
        self.imgs: list[Image.Image] = []
        # per-source rotation state (in 90deg steps, 0/90/180/270)
        self.imgs_rotation: list[int] = []
        self.current_page: int = 0
        # store last loaded file path to build a default export name
        self._last_loaded_path: Optional[str] = None
        # single-page input (PDF will load first page only)
        self.cor_sangria: Tuple[int, int, int] = (255, 255, 255)
        self._build_ui()
        # prefer an initial 5:4 width:height ratio (resizable)
        self.resize(1000, 800)  # width 1000, height 800 => 5:4

    def _build_ui(self) -> None:
        # Root layout with two columns: controls (left) and preview (right)
        root = QHBoxLayout()

        controls = QVBoxLayout()
        controls.setSpacing(8)

        # File group
        file_group = QGroupBox("📁 Arquivo(s)")
        file_group.setStyleSheet("QGroupBox { font-weight: bold; color: #4a9eff; }")
        fg_layout = QHBoxLayout()
        self.btn_load = QPushButton("📂 Abrir Imagem ou PDF")
        self.btn_load.clicked.connect(self.load_file)
        self.btn_load.setShortcut('Ctrl+O')
        self.btn_load.setStyleSheet("QPushButton { background-color: #4a9eff; color: white; font-weight: bold; padding: 8px 12px; border-radius: 4px; border: none; } QPushButton:hover { background-color: #3a8eef; }")
        fg_layout.addWidget(self.btn_load)
        self.lbl_file = QLabel("Nenhum arquivo carregado ainda")
        self.lbl_file.setStyleSheet("color: #aaa;")
        self.lbl_file.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred)
        fg_layout.addWidget(self.lbl_file)
        file_group.setLayout(fg_layout)
        controls.addWidget(file_group)

        # Size group
        size_group = QGroupBox("📏 Tamanho da Imagem (milímetros)")
        size_group.setStyleSheet("QGroupBox { font-weight: bold; color: #ff9500; }")
        sg = QHBoxLayout()
        sg.addWidget(QLabel("Largura (mm):"))
        self.spin_w = QDoubleSpinBox()
        self.spin_w.setRange(0, 10000)
        self.spin_w.setDecimals(1)
        self.spin_w.setToolTip("Largura final de cada imagem em milímetros")
        sg.addWidget(self.spin_w)
        sg.addWidget(QLabel("Altura (mm):"))
        self.spin_h = QDoubleSpinBox()
        self.spin_h.setRange(0, 10000)
        self.spin_h.setDecimals(1)
        self.spin_h.setToolTip("Altura final de cada imagem em milímetros")
        sg.addWidget(self.spin_h)
        self.chk_keep = QCheckBox("🔒 Manter Proporção")
        # default: off (user requested)
        self.chk_keep.setChecked(False)
        self.chk_keep.setToolTip("Preserva a proporção original ao redimensionar (evita distorção)")
        sg.addWidget(self.chk_keep)
        size_group.setLayout(sg)
        controls.addWidget(size_group)

    # Imposition options (stacked for responsive layout)
        imp_group = QGroupBox("⚙️ Configurações de Impressão")
        imp_group.setStyleSheet("QGroupBox { font-weight: bold; color: #34c759; }")
        ig = QVBoxLayout()
        ig.addWidget(QLabel("📄 Tamanho da Folha de Impressão:"))
        self.cmb_sheet = QComboBox()
        try:
            self.cmb_sheet.addItems(list(self.impositor.SHEETS_PT.keys()))
        except Exception:
            self.cmb_sheet.addItems(["A4"])
        self.cmb_sheet.setToolTip(
            "Selecione o tamanho do papel onde as imagens serão impressas")
        ig.addWidget(self.cmb_sheet)
        
        # rotation indicator (hidden unless automatic rotation is applied)
        self.lbl_rot = QLabel("Rotacionado")
        self.lbl_rot.setToolTip(
            "Rotação automática aplicada para melhor encaixe")
        self.lbl_rot.setStyleSheet(
            'background:#d97706; color:#fff; padding:2px 6px; border-radius:4px; font-size:10px;')
        self.lbl_rot.setVisible(False)
        ig.addWidget(self.lbl_rot)

        ig.addWidget(QLabel("🔢 Quantas Imagens por Folha:"))
        self.spin_units = QSpinBox()
        self.spin_units.setRange(1, 1000)
        self.spin_units.setValue(1)
        self.spin_units.setToolTip("Número de cópias da imagem que caberão em cada folha impressa")
        ig.addWidget(self.spin_units)
        
        # Rotation hint for click-to-rotate feature
        self.lbl_rotation_hint = QLabel("💡 Dica: Clique em uma imagem na visualização para rotacioná-la 90°")
        self.lbl_rotation_hint.setStyleSheet("color: #999; font-size: 10px; font-style: italic; padding: 4px;")
        self.lbl_rotation_hint.setWordWrap(True)
        ig.addWidget(self.lbl_rotation_hint)

        ig.addWidget(QLabel("✂️ Sangria/Margem de Corte (mm):"))
        self.spin_bleed = QDoubleSpinBox()
        self.spin_bleed.setRange(0, 100)
        self.spin_bleed.setDecimals(1)
        self.spin_bleed.setValue(0)  # default: no bleed
        self.spin_bleed.setToolTip("Margem extra para corte após impressão. 0 = sem margem extra")
        ig.addWidget(self.spin_bleed)

        ig.addWidget(QLabel("📏 Espaçamento entre Imagens (mm):"))
        self.spin_gap = QDoubleSpinBox()
        self.spin_gap.setRange(0, 50)
        self.spin_gap.setDecimals(1)
        self.spin_gap.setValue(0)  # default: no gap
        self.spin_gap.setToolTip("Espaço em branco entre cada imagem na folha. 0 = sem espaço")
        ig.addWidget(self.spin_gap)

        # multipage options (always visible now for better UX)
        ig.addWidget(QLabel("🗂️ Modo de Impressão (múltiplas imagens/páginas):"))
        self.cmb_multipage = QComboBox()
        self.cmb_multipage.addItems([
            "Mesma imagem repetida (cópias iguais)",
            "Imagens diferentes em sequência"
        ])
        self.cmb_multipage.setToolTip("Escolha se quer repetir a mesma imagem várias vezes ou imprimir páginas diferentes em sequência")
        ig.addWidget(self.cmb_multipage)

        # bleed mode (Português labels)
        ig.addWidget(QLabel("🎨 Modo de Preenchimento da Sangria:"))
        self.cmb_bleed = QComboBox()
        self.cmb_bleed.addItems(
            ["Espelhar Bordas da Imagem", "Preencher com Cor Sólida", "Sem Sangria (Não Adicionar)"])
        self.cmb_bleed.setToolTip("Como preencher a área extra de sangria: espelhando a borda da imagem ou com uma cor")
        ig.addWidget(self.cmb_bleed)

        self.btn_color = QPushButton("🎨 Escolher Cor da Sangria")
        self.btn_color.clicked.connect(self.choose_color)
        self.btn_color.setToolTip("Clique para escolher a cor que preencherá a margem de sangria")
        self.btn_color.setStyleSheet("QPushButton { background-color: #ff9500; color: white; font-weight: bold; padding: 6px 10px; border-radius: 4px; border: none; } QPushButton:hover { background-color: #e88500; } QPushButton:disabled { background-color: #5a5a5a; color: #888; }")
        # only enable color button when "Cor Sólida" is selected
        try:
            self.btn_color.setEnabled(
                self.cmb_bleed.currentText() == 'Preencher com Cor Sólida')
        except Exception:
            pass
        ig.addWidget(self.btn_color)

        imp_group.setLayout(ig)
        controls.addWidget(imp_group)

        # Actions
        act_layout = QHBoxLayout()
        # Preview is auto-updated; remove explicit preview button
        self.btn_export = QPushButton("💾 Salvar PDF Pronto para Impressão")
        self.btn_export.clicked.connect(self.export_pdf)
        self.btn_export.setShortcut('Ctrl+E')
        self.btn_export.setStyleSheet("QPushButton { background-color: #34c759; color: white; font-weight: bold; padding: 10px 16px; border-radius: 6px; font-size: 14px; border: none; } QPushButton:hover { background-color: #2eb84a; }")
        act_layout.addWidget(self.btn_export)
        controls.addLayout(act_layout)

        controls.addStretch()

        # Right side: preview
        preview_box = QGroupBox("👁️ Visualização da Folha de Impressão")
        preview_box.setStyleSheet("QGroupBox { font-weight: bold; color: #5856d6; }")
        pv_layout = QVBoxLayout()
        self.lbl_preview = QLabel(alignment=Qt.AlignCenter)
        self.lbl_preview.setMinimumSize(600, 480)
        # show graphite background in widget; the sheet image will be pasted with a white border
        self.lbl_preview.setStyleSheet(
            "background: #2a2a2a; border: 2px solid #5856d6; border-radius: 4px;")
        pv_layout.addWidget(self.lbl_preview)
        
        # Pagination controls at bottom center
        pagination_layout = QHBoxLayout()
        pagination_layout.addStretch()
        self.btn_prev_page = QPushButton("◀ Anterior")
        self.btn_prev_page.setStyleSheet(
            "background: #5856d6; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; border: none;"
            "QPushButton:hover { background: #6b69e0; }"
            "QPushButton:disabled { background: #5a5a5a; color: #888; }")
        self.btn_prev_page.clicked.connect(self._prev_page)
        self.lbl_page_info = QLabel("Página 1 / 1")
        self.lbl_page_info.setStyleSheet("color: #aaa; font-weight: bold; padding: 0 16px;")
        self.btn_next_page = QPushButton("Próxima ▶")
        self.btn_next_page.setStyleSheet(
            "background: #5856d6; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; border: none;"
            "QPushButton:hover { background: #6b69e0; }"
            "QPushButton:disabled { background: #5a5a5a; color: #888; }")
        self.btn_next_page.clicked.connect(self._next_page)
        pagination_layout.addWidget(self.btn_prev_page)
        pagination_layout.addWidget(self.lbl_page_info)
        pagination_layout.addWidget(self.btn_next_page)
        pagination_layout.addStretch()
        pv_layout.addLayout(pagination_layout)
        
        preview_box.setLayout(pv_layout)

        root.addLayout(controls, 0)
        root.addWidget(preview_box, 1)

        # Footer with clickable link and version on the right
        footer_h = QHBoxLayout()
        left_lbl = QLabel('Desenvolvido por ')
        left_lbl.setStyleSheet("color: #888; font-size: 10px;")
        link = QLabel('<a href="https://wednyfernandes.com.br" style="color:#88b0ff; text-decoration:none;">wednyfernandes.com.br</a>')
        link.setTextFormat(Qt.RichText)
        link.setOpenExternalLinks(True)
        link.setStyleSheet("color: #88b0ff; font-size: 10px;")
        left_box = QHBoxLayout()
        left_box.addWidget(left_lbl)
        left_box.addWidget(link)
        left_box.addStretch()

        # Version label on the right
        self.lbl_version = QLabel("")
        self.lbl_version.setStyleSheet("color: #888; font-size: 10px;")
        # small update button
        self.btn_check_updates = QPushButton("🔄 Verificar Atualizações")
        self.btn_check_updates.setToolTip("Verifica se há uma versão nova do LayoutPress disponível")
        self.btn_check_updates.setStyleSheet("QPushButton { background-color: #5856d6; color: white; padding: 4px 8px; border-radius: 3px; font-size: 9px; border: none; } QPushButton:hover { background-color: #4846c6; }")
        self.btn_check_updates.clicked.connect(self.check_for_updates)

        footer_h.addLayout(left_box)
        footer_h.addWidget(self.btn_check_updates)
        footer_h.addWidget(self.lbl_version)

        main_v = QVBoxLayout()
        main_v.addLayout(root)
        main_v.addLayout(footer_h)
        self.setLayout(main_v)

        # Apply a modern dark theme stylesheet
        self.setStyleSheet("""
            QWidget { 
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QGroupBox { 
                font-weight: bold; 
                font-size: 13px;
                padding: 10px;
                margin-top: 10px;
                border: 2px solid #404040;
                border-radius: 6px;
                background-color: #2a2a2a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #e0e0e0;
            }
            QPushButton { 
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 12px;
                background-color: #404040;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QLabel { 
                font-size: 11px;
                color: #e0e0e0;
                background: transparent;
            }
            QDoubleSpinBox, QSpinBox, QComboBox {
                padding: 4px;
                border: 1px solid #505050;
                border-radius: 3px;
                background: #2a2a2a;
                color: #e0e0e0;
            }
            QDoubleSpinBox:hover, QSpinBox:hover, QComboBox:hover {
                border: 1px solid #606060;
            }
            QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #4a9eff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #e0e0e0;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #e0e0e0;
                selection-background-color: #4a9eff;
                selection-color: white;
                border: 1px solid #505050;
            }
            QCheckBox {
                color: #e0e0e0;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #505050;
                border-radius: 3px;
                background: #2a2a2a;
            }
            QCheckBox::indicator:checked {
                background: #4a9eff;
                border: 1px solid #4a9eff;
            }
        """)

        # Connect many inputs to live preview
        self._connect_live_preview()
        # accept drag and drop files
        self.setAcceptDrops(True)
        # Flag to prevent recursive signal cascades
        self._updating_controls = False
        # periodic preview refresh (every 5 seconds) as a safety net
        # Note: Only refresh if there are images loaded to avoid unnecessary work
        try:
            self._preview_timer = QTimer(self)
            self._preview_timer.timeout.connect(self._safe_periodic_refresh)
            self._preview_timer.start(5000)
        except Exception:
            pass
        # enable/disable color button based on bleed mode
        self.cmb_bleed.currentTextChanged.connect(
            lambda txt: self.btn_color.setEnabled(txt == 'Preencher com Cor Sólida'))
        # default sheet A4
        try:
            self.cmb_sheet.setCurrentText('A4')
        except Exception:
            pass

        # load local version and display
        try:
            self.lbl_version.setText(self._read_local_version())
        except Exception:
            self.lbl_version.setText("")

        # multipage support removed: app now handles a single image (first page of PDF)

    def load_file(self) -> None:
        # open dialog starting in Downloads folder by default
        import os
        start_dir = os.path.join(os.path.expanduser('~'), 'Downloads') if os.path.exists(
            os.path.join(os.path.expanduser('~'), 'Downloads')) else ''
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Abrir arquivo", start_dir, "Images and PDFs (*.png *.jpg *.jpeg *.pdf)")
        if not paths:
            return
        try:
            self.imgs = []
            self.imgs_rotation = []
            # handle PDFs by extracting all pages
            for path in paths:
                if path.lower().endswith('.pdf'):
                    pdf = fitz.open(path)
                    for p in pdf:
                        pix = p.get_pixmap(dpi=self.impositor.dpi)
                        img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                        self.imgs.append(img)
                        self.imgs_rotation.append(0)
                else:
                    im = self.impositor.read_image(path)
                    self.imgs.append(im)
                    self.imgs_rotation.append(0)

            # remember loaded path for export filename default
            self._last_loaded_path = path
            self.lbl_file.setText(path.split("/")[-1])

            # set default size to first file's size in mm
            if self.imgs:
                w_px, h_px = self.imgs[0].width, self.imgs[0].height
                dpi = self.impositor.dpi
                w_mm = round(w_px * 25.4 / dpi, 1)
                h_mm = round(h_px * 25.4 / dpi, 1)
                self.spin_w.setValue(w_mm)
                self.spin_h.setValue(h_mm)

            # compute best sheet and rotation based on first image
            if self.imgs:
                best_sheet, best_units, rotate_img = self._find_best_sheet_and_rotation(self.imgs[0])
            else:
                best_sheet, best_units, rotate_img = ('A4', 1, False)
            try:
                self.cmb_sheet.setCurrentText(best_sheet)
            except Exception:
                pass
            self.spin_units.setRange(1, max(1, best_units))
            self.spin_units.setValue(max(1, best_units))
            self._rotate_for_export = rotate_img

            # pagination init
            self.current_page = 0
            self._update_pagination_controls()

            # auto-generate preview (live)
            self.generate_preview()
        except Exception as e:
            self.lbl_file.setText(f"Erro: {e}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if path:
            # reuse load_file logic by setting start path and calling load behavior
            try:
                # allow dropping a file path to load it
                self._last_loaded_path = path
                # call load_file-like behavior by delegating to load_file but passing path
                # hack: set QFileDialog default selection by temporarily calling the same logic
                # simpler: replicate the core bits
                self.imgs = []
                self.imgs_rotation = []
                if path.lower().endswith('.pdf'):
                    pdf = fitz.open(path)
                    for p in pdf:
                        pix = p.get_pixmap(dpi=self.impositor.dpi)
                        img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                        self.imgs.append(img)
                        self.imgs_rotation.append(0)
                else:
                    im = self.impositor.read_image(path)
                    self.imgs.append(im)
                    self.imgs_rotation.append(0)

                self.lbl_file.setText(path.split('/')[-1])
                self.current_page = 0
                self._update_pagination_controls()
                self.generate_preview()
            except Exception as e:
                self.lbl_file.setText(f"Erro: {e}")

    def choose_color(self) -> None:
        col = QColorDialog.getColor()
        if col.isValid():
            self.cor_sangria = (col.red(), col.green(), col.blue())
            self.btn_color.setStyleSheet(
                f"background-color: rgb{self.cor_sangria};")
            # regenerate preview after color selection
            self.generate_preview()

    def _bleed_mode(self) -> str:
        txt = self.cmb_bleed.currentText()
        if txt == "Espelhar Bordas da Imagem":
            return "mirror"
        if txt == "Preencher com Cor Sólida":
            return "solid"
        return "none"

    def _connect_live_preview(self) -> None:
        # Connect widgets that should trigger an immediate preview update
        # central handler that recomputes and regenerates preview
        def _safe_connect(sig, handler):
            try:
                sig.connect(handler)
            except Exception:
                pass

        # per-widget connections -> use a single handler to keep behavior consistent
        _safe_connect(self.spin_w.valueChanged,
                      lambda *_: self._on_ui_change())
        _safe_connect(self.spin_h.valueChanged,
                      lambda *_: self._on_ui_change())
        _safe_connect(self.spin_units.valueChanged,
                      lambda *_: self._on_ui_change())
        _safe_connect(self.spin_bleed.valueChanged,
                      lambda *_: self._on_ui_change())
        _safe_connect(self.spin_gap.valueChanged,
                      lambda *_: self._on_ui_change())
        _safe_connect(self.chk_keep.stateChanged,
                      lambda *_: self._on_ui_change())
        _safe_connect(self.cmb_sheet.currentIndexChanged,
                      lambda *_: self._on_sheet_change())
        _safe_connect(self.cmb_bleed.currentTextChanged,
                      lambda *_: self._on_ui_change())
        _safe_connect(self.cmb_multipage.currentIndexChanged, lambda *_: self._on_ui_change())
        # pagination buttons
        try:
            _safe_connect(self.btn_prev_page.clicked, lambda *_: self._change_page(-1))
            _safe_connect(self.btn_next_page.clicked, lambda *_: self._change_page(1))
        except Exception:
            pass
        # color button already triggers generate_preview in choose_color

        # enable clicking on preview for rotation toggling
        try:
            self.lbl_preview.mousePressEvent = self._preview_clicked
        except Exception:
            pass

    def _safe_periodic_refresh(self) -> None:
        """Periodic refresh that only runs if images are loaded."""
        try:
            if self.imgs and not self._updating_controls:
                self.generate_preview()
        except Exception:
            pass

    def _recompute_fit(self) -> None:
        """Recalculate best sheet, units and rotation based on current size inputs.

        This uses the currently loaded image resized to the target mm dimensions. It updates
        the sheet selection (only if it improves fit) and the `spin_units` range so the
        UI reflects the true maximum number of units that can fit.
        """
        if not self.imgs or self._updating_controls:
            return
        
        # Block recursive signals while updating controls
        self._updating_controls = True
        try:
            # get requested physical size (may be None)
            w_val = self.spin_w.value()
            h_val = self.spin_h.value()
            w = w_val if (w_val is not None and w_val > 0) else None
            h = h_val if (h_val is not None and h_val > 0) else None
            # make a resized copy consistent with what preview/export will use
            resized = self.impositor.resize_image_mm(
                self.imgs[self.current_page], largura_mm=w, altura_mm=h, manter_proporcao=self.chk_keep.isChecked())
            best_sheet, best_units, rotate_img = self._find_best_sheet_and_rotation(resized)
            # update sheet only if it improves fit (or if current is empty)
            try:
                # always set reasonable upper bound for units
                self.spin_units.setRange(1, max(1, best_units))
                # if current value > best_units, clamp it
                if self.spin_units.value() > best_units:
                    self.spin_units.setValue(max(1, best_units))
                # prefer to set sheet to best choice (but don't change if user explicitly selected)
                # Comment out auto-change to prevent unwanted sheet changes
                # try:
                #     self.cmb_sheet.setCurrentText(best_sheet)
                # except Exception:
                #     pass
                # remember rotation decision for export/preview
                self._rotate_for_export = rotate_img
            except Exception:
                pass
        except Exception:
            pass
        finally:
            self._updating_controls = False

        # update rotation indicator whenever we recompute fit
        try:
            self.lbl_rot.setVisible(
                bool(getattr(self, '_rotate_for_export', False)))
        except Exception:
            pass

    def _preview_clicked(self, event) -> None:
        """Handle mouse clicks on the preview; when tiled view is shown, rotate the clicked image slot by 90 degrees."""
        try:
            if not self.imgs:
                return
            # we only support click-to-rotate on tiled previews (when unidades > 1 or multiple images)
            unidades_req = max(1, self.spin_units.value())
            start_idx = self.current_page * unidades_req
            end_idx = start_idx + unidades_req
            imgs_slice = self.imgs[start_idx:end_idx]
            if not imgs_slice:
                return

            # build same tiled dims as generate_preview to map click coords
            count = len(imgs_slice)
            # compute grid from requested unidades (pages per sheet) to keep layout stable
            unidades_grid = max(1, unidades_req)
            cols = int(math.ceil(math.sqrt(unidades_grid)))
            rows = int(math.ceil(unidades_grid / cols))
            gap = int(max(0, round(self.spin_gap.value() * (self.impositor.dpi / 25.4))))

            thumbs = []
            max_w = max_h = 0
            for p in imgs_slice:
                th = p.copy()
                th.thumbnail((600, 600), Image.LANCZOS)
                thumbs.append(th)
                max_w = max(max_w, th.width)
                max_h = max(max_h, th.height)

            page_pad = 2
            slot_w = max_w + page_pad * 2
            slot_h = max_h + page_pad * 2
            total_w = cols * slot_w + (cols + 1) * gap
            total_h = rows * slot_h + (rows + 1) * gap

            # find clicked position mapped into tiled image coordinates
            px = event.position().x()
            py = event.position().y()
            lbl_w = self.lbl_preview.width()
            lbl_h = self.lbl_preview.height()
            # map px,py from label space into bg image space based on scaling used in generate_preview
            try:
                pixmap = self.lbl_preview.pixmap()
                if pixmap is None:
                    return
                pm_w = pixmap.width()
                pm_h = pixmap.height()
                # compute top-left of pixmap within label
                offset_x = max(0, (lbl_w - pm_w) // 2)
                offset_y = max(0, (lbl_h - pm_h) // 2)
                rel_x = px - offset_x
                rel_y = py - offset_y
                if rel_x < 0 or rel_y < 0 or rel_x >= pm_w or rel_y >= pm_h:
                    return

                # bg dimensions: sheet placed on bg with padding
                folha_w_pt, folha_h_pt = self.impositor.SHEETS_PT.get(self.cmb_sheet.currentText(), self.impositor.SHEETS_PT['A4'])
                sheet_w = int(round(folha_w_pt))
                sheet_h = int(round(folha_h_pt))
                padding = 20
                bg_w = sheet_w + padding * 2
                bg_h = sheet_h + padding * 2

                # compute scale from displayed pixmap to bg image
                scale_x = bg_w / pm_w
                scale_y = bg_h / pm_h
                bx = int(rel_x * scale_x)
                by = int(rel_y * scale_y)

                # map into sheet coordinates by removing padding
                tx = bx - padding
                ty = by - padding
            except Exception:
                return

            # iterate cells to find which slot was clicked (slot coords are in sheet space)
            i = 0
            y = gap
            found = None
            for r in range(rows):
                x = gap
                for c in range(cols):
                    if i >= count:
                        break
                    cell_x = x
                    cell_y = y
                    if tx >= cell_x and tx <= cell_x + slot_w and ty >= cell_y and ty <= cell_y + slot_h:
                        found = i
                        break
                    x += slot_w + gap
                    i += 1
                if found is not None:
                    break
                y += slot_h + gap

            if found is None:
                return

            global_idx = start_idx + found
            # toggle rotation by +90 degrees
            if global_idx >= len(self.imgs_rotation):
                # ensure list is large enough
                while len(self.imgs_rotation) <= global_idx:
                    self.imgs_rotation.append(0)
            self.imgs_rotation[global_idx] = (self.imgs_rotation[global_idx] + 90) % 360
            # regenerate preview to show rotation indicator
            self.generate_preview()
        except Exception:
            return

    def _on_ui_change(self) -> None:
        """Unified handler for UI changes: recompute fit and refresh preview, and update rotation indicator."""
        if self._updating_controls:
            return
        try:
            # recompute may change sheet/units/rotation
            self._recompute_fit()
        except Exception:
            pass
        try:
            # update rotation indicator explicitly
            self.lbl_rot.setVisible(
                bool(getattr(self, '_rotate_for_export', False)))
        except Exception:
            pass
        try:
            self.generate_preview()
        except Exception:
            pass

    def _on_sheet_change(self) -> None:
        """Handler for sheet size changes: auto-adjust max units that fit on new paper size."""
        if self._updating_controls:
            return
        
        self._updating_controls = True
        try:
            if self.imgs:
                # recompute fit with new sheet size
                w_val = self.spin_w.value()
                h_val = self.spin_h.value()
                w = w_val if (w_val is not None and w_val > 0) else None
                h = h_val if (h_val is not None and h_val > 0) else None
                resized = self.impositor.resize_image_mm(
                    self.imgs[self.current_page], largura_mm=w, altura_mm=h, manter_proporcao=self.chk_keep.isChecked())
                best_sheet, best_units, rotate_img = self._find_best_sheet_and_rotation(resized)
                # update units range and value
                self.spin_units.setRange(1, max(1, best_units))
                if self.spin_units.value() > best_units:
                    self.spin_units.setValue(max(1, best_units))
                self._rotate_for_export = rotate_img
        except Exception:
            pass
        finally:
            self._updating_controls = False
        
        # Manually call preview update (don't call _on_ui_change to avoid recursion)
        try:
            self.lbl_rot.setVisible(bool(getattr(self, '_rotate_for_export', False)))
            self.generate_preview()
        except Exception:
            pass

    def _update_pagination_controls(self) -> None:
        # interpret current_page as sheet index; compute total sheets based on unidades (pages per sheet)
        unidades = max(1, self.spin_units.value())
        total_imgs = len(self.imgs)
        if total_imgs <= 0:
            self.btn_prev_page.setEnabled(False)
            self.btn_next_page.setEnabled(False)
            self.lbl_page_info.setText("")
            return
        import math
        total_sheets = math.ceil(total_imgs / unidades)
        # show pagination controls only when there are multiple source pages
        has_multi = total_imgs > 1
        self.btn_prev_page.setVisible(has_multi)
        self.btn_next_page.setVisible(has_multi)
        self.lbl_page_info.setVisible(has_multi)
        if not has_multi or total_sheets <= 1:
            self.btn_prev_page.setEnabled(False)
            self.btn_next_page.setEnabled(False)
            self.lbl_page_info.setText("")
        else:
            self.btn_prev_page.setEnabled(self.current_page > 0)
            self.btn_next_page.setEnabled(self.current_page < total_sheets - 1)
            self.lbl_page_info.setText(f"Folha {self.current_page+1} / {total_sheets}")

    def _change_page(self, delta: int) -> None:
        if not self.imgs:
            return
        unidades = max(1, self.spin_units.value())
        import math
        total_sheets = math.ceil(len(self.imgs) / unidades)
        self.current_page = max(0, min(self.current_page + delta, max(0, total_sheets - 1)))
        self._update_pagination_controls()
        self.generate_preview()

    def _prev_page(self) -> None:
        """Navigate to previous sheet."""
        self._change_page(-1)

    def _next_page(self) -> None:
        """Navigate to next sheet."""
        self._change_page(1)

    def _read_local_version(self) -> str:
        try:
            base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
            vfile = os.path.join(base, 'VERSION')
            if os.path.exists(vfile):
                with open(vfile, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception:
            pass
        return ""

    def _get_remote_version(self) -> str:
        """Fetch VERSION from the GitHub repo branch (raw).

        Uses the repository defined below. Returns version string or empty on error.
        """
        try:
            import requests  # type: ignore[import]
        except Exception:
            return ""
        try:
            owner = 'WednyFernandes'
            repo = 'LayoutPress'
            branch = 'dev'
            url = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/VERSION'
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.text.strip()
        except Exception:
            return ""

    def _download_asset(self, url: str, dest_path: str) -> bool:
        try:
            import requests  # type: ignore[import]
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
            return True
        except Exception:
            return False

    def check_for_updates(self) -> None:
        """Check remote VERSION and prompt user to download and update if newer."""
        try:
            from PySide6.QtWidgets import QMessageBox
        except Exception:
            return

        local = self._read_local_version() or '0.0.0'
        remote = self._get_remote_version() or ''
        if not remote:
            QMessageBox.information(self, 'Atualizações', 'Não foi possível verificar atualizações (sem conexão).')
            return
        try:
            from packaging.version import parse as parse_version
            if parse_version(remote) <= parse_version(local):
                QMessageBox.information(self, 'Atualizações', f'Versão atual ({local}) está atualizada.')
                return
        except Exception:
            pass

        # Ask user to download and update
        reply = QMessageBox.question(self, 'Atualização disponível', f'Versão {remote} disponível (você tem {local}). Deseja baixar e instalar?', QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # Get release asset via GitHub Releases API
        try:
            import requests  # type: ignore[import]
            api = f'https://api.github.com/repos/WednyFernandes/LayoutPress/releases/latest'
            r = requests.get(api, timeout=10)
            r.raise_for_status()
            data = r.json()
            asset_url = None
            for a in data.get('assets', []):
                name = a.get('name', '').lower()
                if name.endswith('.exe') or name.endswith('.zip'):
                    asset_url = a.get('browser_download_url')
                    break
            if not asset_url:
                QMessageBox.information(self, 'Atualizações', 'Nenhum pacote de atualização encontrado nos releases.')
                return
            # download to temp
            import tempfile
            tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(asset_url)[1])
            tmpf.close()
            ok = self._download_asset(asset_url, tmpf.name)
            if not ok:
                QMessageBox.information(self, 'Atualizações', 'Falha ao baixar o pacote de atualização.')
                return
            # call updater (python updater.py target newfile) or if frozen, pass exe path
            target = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
            updater_py = os.path.join(os.path.dirname(__file__), 'updater.py')
            try:
                subprocess.Popen([sys.executable, updater_py, target, tmpf.name], close_fds=True)
            except Exception:
                QMessageBox.information(self, 'Atualizações', 'Não foi possível iniciar o atualizador.')
                return
            QMessageBox.information(self, 'Atualizações', 'O atualizador foi iniciado. O aplicativo será fechado para aplicar a atualização.')
            os._exit(0)
        except Exception as e:
            QMessageBox.information(self, 'Atualizações', f'Erro ao verificar atualizações: {e}')

    def _units_for_image_and_sheet(self, img: Image.Image, folha: str, sangria_mm: float, gap_mm: float, margem_mm: float = 5.0) -> int:
        """Compute how many units of img fit on given sheet name considering bleed and gap."""
        if folha not in self.impositor.SHEETS_PT:
            return 0
        folha_w_pt, folha_h_pt = self.impositor.SHEETS_PT[folha]
        margem_pt = margem_mm * PT_PER_MM
        gap_pt = gap_mm * PT_PER_MM

        img_bleed = self.impositor.add_bleed(img, sangria_mm)
        img_w_pt = img_bleed.width * 72 / self.impositor.dpi
        img_h_pt = img_bleed.height * 72 / self.impositor.dpi

        available_w = folha_w_pt - 2 * margem_pt
        available_h = folha_h_pt - 2 * margem_pt

        cols = 0
        rows = 0
        if img_w_pt + gap_pt > 0:
            cols = int((available_w + gap_pt) // (img_w_pt + gap_pt))
        if img_h_pt + gap_pt > 0:
            rows = int((available_h + gap_pt) // (img_h_pt + gap_pt))

        return max(0, cols * rows)

    def _find_best_sheet_and_rotation(self, img: Image.Image) -> tuple[str, int, bool]:
        """Find best sheet and rotation for img to maximize units.

        Returns (sheet_name, max_units, rotate_bool).
        """
        sangria = self.spin_bleed.value()
        gap = self.spin_gap.value()
        selected = self.cmb_sheet.currentText()

        best_sheet = selected
        best_units = 0
        best_rotate = False

        for rotate in (False, True):
            test_img = img.rotate(90, expand=True) if rotate else img
            units = self._units_for_image_and_sheet(
                test_img, selected, sangria, gap)
            if units > best_units:
                best_units = units
                best_rotate = rotate

        if best_units >= 1:
            return selected, best_units, best_rotate

        sheets = list(self.impositor.SHEETS_PT.items())
        sheets.sort(key=lambda kv: kv[1][0] * kv[1][1])
        for name, _dims in sheets:
            for rotate in (False, True):
                test_img = img.rotate(90, expand=True) if rotate else img
                units = self._units_for_image_and_sheet(
                    test_img, name, sangria, gap)
                if units >= 1:
                    return name, units, rotate

        largest = max(self.impositor.SHEETS_PT.items(),
                      key=lambda kv: kv[1][0] * kv[1][1])[0]
        units = self._units_for_image_and_sheet(img, largest, sangria, gap)
        return largest, units, False

    def pil_to_pixmap(self, pil: Image.Image) -> QPixmap:
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        qimg = QImage.fromData(buf.getvalue())
        return QPixmap.fromImage(qimg)

    def generate_preview(self) -> None:
        """
        Generate preview using the SAME logic as PDF export (impositor.py).
        This ensures preview matches the final exported PDF exactly.
        """
        try:
            # If no image loaded, clear preview
            if not self.imgs:
                self.lbl_preview.clear()
                return

            w_val = self.spin_w.value()
            h_val = self.spin_h.value()
            w = w_val if (w_val is not None and w_val > 0) else None
            h = h_val if (h_val is not None and h_val > 0) else None

            folha = self.cmb_sheet.currentText()
            modo = self._bleed_mode()
            sangria_mm = self.spin_bleed.value()
            gap_mm = self.spin_gap.value()
            margem_mm = 5.0
            unidades_req = max(1, self.spin_units.value())
            
            # Get multipage mode to determine how to handle multiple images
            multipage_mode = 'repeat_per_page' if self.cmb_multipage.currentText().startswith('Mesma imagem') else 'one_each'

            # compute which images belong to the current sheet
            start_idx = self.current_page * unidades_req
            end_idx = start_idx + unidades_req
            imgs_slice = self.imgs[start_idx:end_idx]
            if not imgs_slice:
                self.lbl_preview.clear()
                return

            # prepare images for preview (same as export)
            pil_imgs = []
            for p_idx, p in enumerate(imgs_slice):
                p2 = p.copy()
                # apply requested resize
                if (w is not None) or (h is not None):
                    p2 = self.impositor.resize_image_mm(p2, largura_mm=w, altura_mm=h, manter_proporcao=self.chk_keep.isChecked())
                # apply per-image rotation state
                rot = self.imgs_rotation[start_idx + p_idx] if (start_idx + p_idx) < len(self.imgs_rotation) else 0
                if rot:
                    p2 = p2.rotate(rot, expand=True)
                pil_imgs.append(p2)

            # Get sheet dimensions
            folha_w_pt, folha_h_pt = self.impositor.SHEETS_PT.get(folha, self.impositor.SHEETS_PT['A4'])
            sheet_w = int(round(folha_w_pt))
            sheet_h = int(round(folha_h_pt))
            
            # Create white sheet (same as impositor.generate_preview)
            preview = Image.new("RGB", (sheet_w, sheet_h), (255, 255, 255))
            
            # Use FIRST image to compute grid (same logic as export)
            if not pil_imgs:
                self.lbl_preview.clear()
                return
                
            first_img = pil_imgs[0]
            
            # Add bleed and compute dimensions IN POINTS (same as export)
            img_bleed = self.impositor.add_bleed(first_img, sangria_mm, modo, self.cor_sangria)
            img_w_pt = img_bleed.width * 72 / self.impositor.dpi
            img_h_pt = img_bleed.height * 72 / self.impositor.dpi
            
            margem_pt = margem_mm * PT_PER_MM
            gap_pt = gap_mm * PT_PER_MM
            
            # Compute cols/rows EXACTLY like impositor.py
            if img_w_pt + gap_pt > 0:
                cols = int((folha_w_pt - 2 * margem_pt + gap_pt) // (img_w_pt + gap_pt))
            else:
                cols = 1
            if img_h_pt + gap_pt > 0:
                rows = int((folha_h_pt - 2 * margem_pt + gap_pt) // (img_h_pt + gap_pt))
            else:
                rows = 1
            
            cols = max(1, cols)
            rows = max(1, rows)
            
            # Limit slots by unidades (how many images we want to place)
            per_page = cols * rows
            slots = min(unidades_req, per_page)
            count = min(len(pil_imgs), slots)
            
            # Compute layout dimensions (same as impositor.py)
            used_w = cols * img_w_pt + (cols - 1) * gap_pt
            used_h = rows * img_h_pt + (rows - 1) * gap_pt
            start_x = max(margem_pt, (folha_w_pt - used_w) / 2.0)
            start_y = max(margem_pt, (folha_h_pt - used_h) / 2.0)
            
            from PIL import ImageDraw
            draw = ImageDraw.Draw(preview)
            border_color = (77, 77, 77)  # K 30% - same as impositor.py
            
            # Place images on the sheet (up to unidades)
            placed = 0
            for r in range(rows):
                for c in range(cols):
                    if placed >= count:
                        break
                    
                    # Get the image for this slot based on multipage mode
                    if multipage_mode == 'repeat_per_page':
                        # Repeat first image (or cycle through available images)
                        img_idx = placed % len(pil_imgs)
                    else:
                        # 'one_each': use different images in sequence
                        # In preview, we show the slice for current page
                        img_idx = min(placed, len(pil_imgs) - 1)
                    
                    current_img = pil_imgs[img_idx]
                    
                    # Add bleed to this specific image
                    img_with_bleed = self.impositor.add_bleed(current_img, sangria_mm, modo, self.cor_sangria)
                    
                    # Resize to points for preview rendering
                    img_w_pt_cur = img_with_bleed.width * 72 / self.impositor.dpi
                    img_h_pt_cur = img_with_bleed.height * 72 / self.impositor.dpi
                    img_resized = img_with_bleed.resize((int(img_w_pt_cur), int(img_h_pt_cur)), Image.LANCZOS)
                    
                    # Compute position
                    px = int(round(start_x + c * (img_w_pt + gap_pt)))
                    py = int(round(start_y + r * (img_h_pt + gap_pt)))
                    
                    # Safety check - don't paste outside bounds
                    if px < 0 or py < 0 or px + int(img_w_pt_cur) > preview.width or py + int(img_h_pt_cur) > preview.height:
                        placed += 1
                        continue
                    
                    # Paste image
                    preview.paste(img_resized, (px, py))
                    
                    # Draw border (K 30%)
                    rect = [px, py, px + int(img_w_pt_cur), py + int(img_h_pt_cur)]
                    stroke_px = max(1, int(round(0.5 * PT_PER_MM)))
                    try:
                        draw.rectangle(rect, outline=border_color, width=stroke_px)
                    except Exception:
                        pass
                    
                    # Draw rotation indicator if image is rotated
                    global_idx = start_idx + placed
                    try:
                        if global_idx < len(self.imgs_rotation) and self.imgs_rotation[global_idx] % 360 != 0:
                            draw.rectangle([px + 6, py + 6, px + 22, py + 22], fill=(200, 180, 0))
                    except Exception:
                        pass
                    
                    placed += 1
                if placed >= count:
                    break

            # place the sheet onto a darker background so it stands out in the preview
            padding = 20
            bg_w = preview.width + padding * 2
            bg_h = preview.height + padding * 2
            bg = Image.new('RGB', (bg_w, bg_h), (74, 74, 74))
            bg.paste(preview, (padding, padding))
            pix = self.pil_to_pixmap(bg)
            scaled = pix.scaled(self.lbl_preview.width(), self.lbl_preview.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_preview.setPixmap(scaled)
        except Exception as e:
            self.lbl_preview.setText(f"Erro no preview: {e}")

    def export_pdf(self) -> None:
        if not self.imgs:
            self.lbl_file.setText("Nenhum arquivo carregado")
            return
        # build a sensible default filename: 'original - ajustado.pdf' when possible
        default_name = "output.pdf"
        try:
            if self._last_loaded_path:
                import os
                base = os.path.splitext(
                    os.path.basename(self._last_loaded_path))[0]
                default_name = f"{base} - ajustado.pdf"
        except Exception:
            default_name = "output.pdf"

        # prefer to open save dialog in same folder as last loaded file
        try:
            import os
            initial_dir = os.path.dirname(
                self._last_loaded_path) if self._last_loaded_path else ''
            start = os.path.join(
                initial_dir, default_name) if initial_dir else default_name
        except Exception:
            start = default_name

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Salvar PDF", start, "PDF Files (*.pdf)")
        if not save_path:
            return
        w_val = self.spin_w.value()
        h_val = self.spin_h.value()
        w = w_val if (w_val is not None and w_val > 0) else None
        h = h_val if (h_val is not None and h_val > 0) else None
        # prepare image(s) for export
        imgs_for_export = []
        if len(self.imgs) > 1:
            # apply resize to each page if requested
            for p in self.imgs:
                p2 = p
                if (w is not None) or (h is not None):
                    p2 = self.impositor.resize_image_mm(p2, largura_mm=w, altura_mm=h, manter_proporcao=self.chk_keep.isChecked())
                imgs_for_export.append(p2)
        else:
            img_single = self.imgs[0]
            if (w is not None) or (h is not None):
                img_single = self.impositor.resize_image_mm(img_single, largura_mm=w, altura_mm=h, manter_proporcao=self.chk_keep.isChecked())
            imgs_for_export = [img_single]
        modo = self._bleed_mode()
        # determine multipage mode from combo
        multipage_mode = 'repeat_per_page' if self.cmb_multipage.currentText().startswith('Mesma imagem') else 'one_each'
        try:
            folha = self.cmb_sheet.currentText()
            # rotate image if earlier decision indicated better fit
            # for multipage, rotate each image if needed
            img_to_export = [ (p.rotate(90, expand=True) if getattr(self, '_rotate_for_export', False) else p) for p in imgs_for_export ]
            # limit unidades to what fits
            # when passing list, compute based on first image as approximation
            max_fit = self._units_for_image_and_sheet(
                img_to_export[0], folha, self.spin_bleed.value(), self.spin_gap.value())
            unidades = min(self.spin_units.value(), max(1, max_fit))
            # compute margin when single unit requested so it's centered
            if unidades == 1:
                img_bleed = self.impositor.add_bleed(
                    img_to_export[0], self.spin_bleed.value(), modo, self.cor_sangria)
                img_w_pt = img_bleed.width * 72 / self.impositor.dpi
                folha_w_pt, folha_h_pt = self.impositor.SHEETS_PT.get(
                    folha, self.impositor.SHEETS_PT['A4'])
                margin_x_pt = max(0.0, (folha_w_pt - img_w_pt) / 2.0)
                margem_mm = margin_x_pt / PT_PER_MM
                if len(img_to_export) == 1:
                    self.impositor.impose_to_pdf(img_to_export[0], folha=folha, unidades=unidades, sangria_mm=self.spin_bleed.value(
                    ), modo_sangria=modo, margem_mm=margem_mm, gap_mm=self.spin_gap.value(), output_path=save_path, cor_sangria=self.cor_sangria)
                else:
                    # when exporting multiple source pages, use selected multipage mode
                    self.impositor.impose_to_pdf(img_to_export, folha=folha, unidades=unidades, sangria_mm=self.spin_bleed.value(
                    ), modo_sangria=modo, margem_mm=margem_mm, gap_mm=self.spin_gap.value(), output_path=save_path, cor_sangria=self.cor_sangria, multi_mode=multipage_mode)
            else:
                if len(img_to_export) == 1:
                    self.impositor.impose_to_pdf(img_to_export[0], folha=self.cmb_sheet.currentText(), unidades=unidades, sangria_mm=self.spin_bleed.value(
                    ), modo_sangria=modo, gap_mm=self.spin_gap.value(), output_path=save_path, cor_sangria=self.cor_sangria)
                else:
                    self.impositor.impose_to_pdf(img_to_export, folha=self.cmb_sheet.currentText(), unidades=unidades, sangria_mm=self.spin_bleed.value(
                    ), modo_sangria=modo, gap_mm=self.spin_gap.value(), output_path=save_path, cor_sangria=self.cor_sangria, multi_mode=multipage_mode)
            # show completed status and debug info about rotation
            rotated = bool(getattr(self, '_rotate_for_export', False))
            self.lbl_file.setText(
                f"Exportado: {save_path}  (Rotacionado: {rotated})")
            
            # auto-open the generated PDF
            try:
                import os
                import subprocess
                if os.path.exists(save_path):
                    # Windows-specific: use os.startfile for best compatibility
                    if sys.platform == 'win32':
                        os.startfile(save_path)
                    elif sys.platform == 'darwin':  # macOS
                        subprocess.Popen(['open', save_path])
                    else:  # Linux/Unix
                        subprocess.Popen(['xdg-open', save_path])
            except Exception as e_open:
                # If auto-open fails, just show a message but don't block the success notification
                print(f"Não foi possível abrir o PDF automaticamente: {e_open}")
            
            try:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "Exportado", f"Export concluído e PDF aberto:\n{save_path}\nRotacionado: {rotated}")
            except Exception:
                pass
        except Exception as e:
            self.lbl_file.setText(f"Erro exportar: {e}")


def main() -> None:
    app = QApplication(sys.argv)
    # Load dark theme from QSS file if available, otherwise use built-in dark theme
    try:
        import os
        base_dir = None
        # when running as a PyInstaller onefile bundle the data files are unpacked to _MEIPASS
        if getattr(sys, 'frozen', False):
            base_dir = getattr(sys, '_MEIPASS', None)
        if not base_dir:
            base_dir = os.path.dirname(__file__)
        qss_path = os.path.join(base_dir, 'dark_theme.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
        else:
            # Built-in fallback dark theme (matches dark_theme.qss)
            app.setStyleSheet("""
                QWidget {
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #404040;
                    border-radius: 6px;
                    background-color: #2a2a2a;
                    padding: 10px;
                    margin-top: 12px;
                }
                QPushButton {
                    background-color: #404040;
                    color: #e0e0e0;
                    padding: 6px 10px;
                    border-radius: 4px;
                }
                QPushButton:hover { background-color: #505050; }
                QLabel { color: #e0e0e0; }
                QDoubleSpinBox, QSpinBox, QComboBox {
                    background-color: #2a2a2a;
                    color: #e0e0e0;
                    border: 1px solid #505050;
                    padding: 4px;
                    border-radius: 3px;
                }
            """)
    except Exception:
        pass
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
