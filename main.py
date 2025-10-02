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
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt

from impositor import Impositor, PT_PER_MM
from PIL import Image


class MainWindow(QWidget):
    """Clean, minimal GUI for Impositor."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Impositor - Simples")
        self.impositor = Impositor()
        self.img: Optional[Image.Image] = None
        self.cor_sangria: Tuple[int, int, int] = (255, 255, 255)
        self._build_ui()

    def _build_ui(self) -> None:
        # Root layout with two columns: controls (left) and preview (right)
        root = QHBoxLayout()

        controls = QVBoxLayout()
        controls.setSpacing(8)

        # File group
        file_group = QGroupBox("Arquivo")
        fg_layout = QHBoxLayout()
        self.btn_load = QPushButton("Carregar imagem/PDF")
        self.btn_load.clicked.connect(self.load_file)
        self.btn_load.setShortcut('Ctrl+O')
        fg_layout.addWidget(self.btn_load)
        self.lbl_file = QLabel("Nenhum arquivo carregado")
        self.lbl_file.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        fg_layout.addWidget(self.lbl_file)
        file_group.setLayout(fg_layout)
        controls.addWidget(file_group)

        # Size group
        size_group = QGroupBox("Tamanho (mm)")
        sg = QHBoxLayout()
        sg.addWidget(QLabel("Largura:"))
        self.spin_w = QDoubleSpinBox()
        self.spin_w.setRange(0, 10000)
        self.spin_w.setDecimals(1)
        self.spin_w.setToolTip("Largura final em milímetros")
        sg.addWidget(self.spin_w)
        sg.addWidget(QLabel("Altura:"))
        self.spin_h = QDoubleSpinBox()
        self.spin_h.setRange(0, 10000)
        self.spin_h.setDecimals(1)
        self.spin_h.setToolTip("Altura final em milímetros")
        sg.addWidget(self.spin_h)
        self.chk_keep = QCheckBox("Manter proporção")
        self.chk_keep.setChecked(True)
        self.chk_keep.setToolTip("Preserva a relação largura/altura ao redimensionar")
        sg.addWidget(self.chk_keep)
        size_group.setLayout(sg)
        controls.addWidget(size_group)

        # Imposition options
        imp_group = QGroupBox("Imposição")
        ig = QHBoxLayout()
        ig.addWidget(QLabel("Folha:"))
        self.cmb_sheet = QComboBox()
        try:
            self.cmb_sheet.addItems(list(self.impositor.SHEETS_PT.keys()))
        except Exception:
            self.cmb_sheet.addItems(["A4"])
        self.cmb_sheet.setToolTip("Selecione o tamanho da folha para a imposição")
        ig.addWidget(self.cmb_sheet)
        ig.addWidget(QLabel("Unidades:"))
        self.spin_units = QSpinBox()
        self.spin_units.setRange(1, 1000)
        self.spin_units.setValue(1)
        self.spin_units.setToolTip("Número de unidades por folha")
        ig.addWidget(self.spin_units)
        ig.addWidget(QLabel("Sangria (mm):"))
        self.spin_bleed = QDoubleSpinBox()
        self.spin_bleed.setRange(0, 100)
        self.spin_bleed.setDecimals(1)
        self.spin_bleed.setValue(0)  # default: no bleed
        self.spin_bleed.setToolTip("Tamanho da sangria em mm")
        ig.addWidget(self.spin_bleed)
        ig.addWidget(QLabel("Espaço (mm):"))
        self.spin_gap = QDoubleSpinBox()
        self.spin_gap.setRange(0, 50)
        self.spin_gap.setDecimals(1)
        self.spin_gap.setValue(0)  # default: no gap
        self.spin_gap.setToolTip("Espaço entre unidades em mm")
        ig.addWidget(self.spin_gap)
        self.cmb_bleed = QComboBox()
        self.cmb_bleed.addItems(["Espelhar Bordas", "Cor Sólida", "Sem Sangria"])
        self.cmb_bleed.setToolTip("Modo de tratamento das bordas/sangria")
        ig.addWidget(self.cmb_bleed)
        self.btn_color = QPushButton("Cor da sangria")
        self.btn_color.clicked.connect(self.choose_color)
        self.btn_color.setToolTip("Escolha a cor usada quando 'Cor Sólida' estiver selecionado")
        # only enable color button when "Cor Sólida" is selected
        try:
            self.btn_color.setEnabled(self.cmb_bleed.currentText() == 'Cor Sólida')
        except Exception:
            pass
        ig.addWidget(self.btn_color)
        imp_group.setLayout(ig)
        controls.addWidget(imp_group)

        # Actions
        act_layout = QHBoxLayout()
        # Preview is auto-updated; remove explicit preview button
        self.btn_export = QPushButton("Exportar PDF")
        self.btn_export.clicked.connect(self.export_pdf)
        self.btn_export.setShortcut('Ctrl+E')
        act_layout.addWidget(self.btn_export)
        controls.addLayout(act_layout)

        controls.addStretch()

        # Right side: preview
        preview_box = QGroupBox("Preview")
        pv_layout = QVBoxLayout()
        self.lbl_preview = QLabel(alignment=Qt.AlignCenter)
        self.lbl_preview.setMinimumSize(600, 480)
        # show graphite background in widget; the sheet image will be pasted with a white border
        self.lbl_preview.setStyleSheet("background: #4a4a4a; border: 1px solid #333;")
        pv_layout.addWidget(self.lbl_preview)
        preview_box.setLayout(pv_layout)

        root.addLayout(controls, 0)
        root.addWidget(preview_box, 1)

        # Apply a light modern stylesheet for clarity
        self.setStyleSheet("QGroupBox { font-weight: bold; } QPushButton { padding: 6px 10px; }")

        self.setLayout(root)

        # Connect many inputs to live preview
        self._connect_live_preview()
        # accept drag and drop files
        self.setAcceptDrops(True)
        # enable/disable color button based on bleed mode
        self.cmb_bleed.currentTextChanged.connect(lambda txt: self.btn_color.setEnabled(txt == 'Cor Sólida'))
        # default sheet A4
        try:
            self.cmb_sheet.setCurrentText('A4')
        except Exception:
            pass

    def load_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Abrir arquivo", "", "Images and PDFs (*.png *.jpg *.jpeg *.pdf)")
        if not path:
            return
        try:
            self.img = self.impositor.read_image(path)
            self.lbl_file.setText(path.split("/")[-1])
            # set default size to file's size in mm
            w_px, h_px = self.img.width, self.img.height
            dpi = self.impositor.dpi
            w_mm = round(w_px * 25.4 / dpi, 1)
            h_mm = round(h_px * 25.4 / dpi, 1)
            self.spin_w.setValue(w_mm)
            self.spin_h.setValue(h_mm)

            # compute best sheet and rotation to maximize units (or switch to larger sheet if needed)
            best_sheet, best_units, rotate_img = self._find_best_sheet_and_rotation(self.img)
            try:
                self.cmb_sheet.setCurrentText(best_sheet)
            except Exception:
                pass
            self.spin_units.setRange(1, max(1, best_units))
            self.spin_units.setValue(max(1, best_units))
            self._rotate_for_export = rotate_img

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
            try:
                self.img = self.impositor.read_image(path)
                self.lbl_file.setText(path.split("/")[-1])
                self.generate_preview()
            except Exception as e:
                self.lbl_file.setText(f"Erro: {e}")

    def choose_color(self) -> None:
        col = QColorDialog.getColor()
        if col.isValid():
            self.cor_sangria = (col.red(), col.green(), col.blue())
            self.btn_color.setStyleSheet(f"background-color: rgb{self.cor_sangria};")
            # regenerate preview after color selection
            self.generate_preview()

    def _bleed_mode(self) -> str:
        txt = self.cmb_bleed.currentText()
        if txt == "Espelhar Bordas":
            return "mirror"
        if txt == "Cor Sólida":
            return "solid"
        return "none"

    def _connect_live_preview(self) -> None:
        # Connect widgets that should trigger an immediate preview update
        widgets = [
            self.spin_w,
            self.spin_h,
            self.chk_keep,
            self.cmb_sheet,
            self.spin_units,
            self.spin_bleed,
            self.cmb_bleed,
        ]
        for widget in widgets:
            try:
                # many Qt widgets expose valueChanged or currentIndexChanged
                if hasattr(widget, 'valueChanged'):
                    widget.valueChanged.connect(lambda *_: self.generate_preview())
                elif hasattr(widget, 'currentIndexChanged'):
                    widget.currentIndexChanged.connect(lambda *_: self.generate_preview())
            except Exception:
                pass
        # checkbox
        self.chk_keep.stateChanged.connect(lambda *_: self.generate_preview())

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
            units = self._units_for_image_and_sheet(test_img, selected, sangria, gap)
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
                units = self._units_for_image_and_sheet(test_img, name, sangria, gap)
                if units >= 1:
                    return name, units, rotate

        largest = max(self.impositor.SHEETS_PT.items(), key=lambda kv: kv[1][0] * kv[1][1])[0]
        units = self._units_for_image_and_sheet(img, largest, sangria, gap)
        return largest, units, False

    def pil_to_pixmap(self, pil: Image.Image) -> QPixmap:
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        qimg = QImage.fromData(buf.getvalue())
        return QPixmap.fromImage(qimg)

    def generate_preview(self) -> None:
        if not self.img:
            return
        w_val = self.spin_w.value()
        h_val = self.spin_h.value()
        w = w_val if (w_val is not None and w_val > 0) else None
        h = h_val if (h_val is not None and h_val > 0) else None
        img = self.img
        if (w is not None) or (h is not None):
            img = self.impositor.resize_image_mm(img, largura_mm=w, altura_mm=h, manter_proporcao=self.chk_keep.isChecked())
        modo = self._bleed_mode()
        # apply rotation chosen to maximize fit for preview
        if getattr(self, '_rotate_for_export', False):
            img = img.rotate(90, expand=True)
        try:
            # Determine unidades but clamp to what actually fits on the sheet
            folha = self.cmb_sheet.currentText()
            unidades_requested = self.spin_units.value()
            max_fit = self._units_for_image_and_sheet(img, folha, self.spin_bleed.value(), self.spin_gap.value())
            unidades = min(max(1, max_fit), max(1, unidades_requested))
            # If only one unit, compute margins to center the item on the sheet
            # folha already assigned above
            if unidades == 1:
                # Build bleed image to compute size in points
                img_bleed = self.impositor.add_bleed(img, self.spin_bleed.value(), modo, self.cor_sangria)
                img_w_pt = img_bleed.width * 72 / self.impositor.dpi
                img_h_pt = img_bleed.height * 72 / self.impositor.dpi
                folha_w_pt, folha_h_pt = self.impositor.SHEETS_PT.get(folha, self.impositor.SHEETS_PT['A4'])
                margin_x_pt = max(0.0, (folha_w_pt - img_w_pt) / 2.0)
                margin_mm = margin_x_pt / PT_PER_MM
                preview = self.impositor.generate_preview(img, folha=folha, unidades=unidades, sangria_mm=self.spin_bleed.value(), modo_sangria=modo, cor_sangria=self.cor_sangria, margem_mm=margin_mm, gap_mm=self.spin_gap.value())
            else:
                preview = self.impositor.generate_preview(img, folha=self.cmb_sheet.currentText(), unidades=unidades, sangria_mm=self.spin_bleed.value(), modo_sangria=modo, cor_sangria=self.cor_sangria, gap_mm=self.spin_gap.value())
            # compose over graphite background with a white sheet inset for better contrast
            try:
                padding = 20
                bg = Image.new('RGB', (preview.width + padding * 2, preview.height + padding * 2), (74, 74, 74))
                # create white sheet area
                sheet_box = Image.new('RGB', (preview.width, preview.height), (255, 255, 255))
                bg.paste(sheet_box, (padding, padding))
                bg.paste(preview, (padding, padding))
                composite = bg
            except Exception:
                composite = preview
            pix = self.pil_to_pixmap(composite)
            scaled = pix.scaled(self.lbl_preview.width(), self.lbl_preview.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_preview.setPixmap(scaled)
        except Exception as e:
            self.lbl_preview.setText(f"Erro no preview: {e}")

    def export_pdf(self) -> None:
        if not self.img:
            self.lbl_file.setText("Nenhum arquivo carregado")
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", "output.pdf", "PDF Files (*.pdf)")
        if not save_path:
            return
        w_val = self.spin_w.value()
        h_val = self.spin_h.value()
        w = w_val if (w_val is not None and w_val > 0) else None
        h = h_val if (h_val is not None and h_val > 0) else None
        img = self.img
        if (w is not None) or (h is not None):
            img = self.impositor.resize_image_mm(img, largura_mm=w, altura_mm=h, manter_proporcao=self.chk_keep.isChecked())
        modo = self._bleed_mode()
        try:
            folha = self.cmb_sheet.currentText()
            # rotate image if earlier decision indicated better fit
            img_to_export = img.rotate(90, expand=True) if getattr(self, '_rotate_for_export', False) else img
            # limit unidades to what fits
            max_fit = self._units_for_image_and_sheet(img_to_export, folha, self.spin_bleed.value(), self.spin_gap.value())
            unidades = min(self.spin_units.value(), max(1, max_fit))
            # If single unit, compute margin so the item is centered on the page
            if unidades == 1:
                img_bleed = self.impositor.add_bleed(img_to_export, self.spin_bleed.value(), modo, self.cor_sangria)
                img_w_pt = img_bleed.width * 72 / self.impositor.dpi
                folha_w_pt, folha_h_pt = self.impositor.SHEETS_PT.get(folha, self.impositor.SHEETS_PT['A4'])
                margin_x_pt = max(0.0, (folha_w_pt - img_w_pt) / 2.0)
                margem_mm = margin_x_pt / PT_PER_MM
                self.impositor.impose_to_pdf(img_to_export, folha=folha, unidades=unidades, sangria_mm=self.spin_bleed.value(), modo_sangria=modo, margem_mm=margem_mm, gap_mm=self.spin_gap.value(), output_path=save_path, cor_sangria=self.cor_sangria)
            else:
                self.impositor.impose_to_pdf(img_to_export, folha=self.cmb_sheet.currentText(), unidades=unidades, sangria_mm=self.spin_bleed.value(), modo_sangria=modo, gap_mm=self.spin_gap.value(), output_path=save_path, cor_sangria=self.cor_sangria)
            self.lbl_file.setText(f"Exportado: {save_path}")
        except Exception as e:
            self.lbl_file.setText(f"Erro exportar: {e}")


def main() -> None:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()