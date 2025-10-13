from PIL import Image, ImageOps
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import math
from typing import Optional, Tuple, Dict, Literal

PT_PER_MM = 72 / 25.4

class Impositor:
    """
    Classe para imposição de imagens em PDFs para impressão.
    """

    SHEETS_PT: Dict[str, Tuple[float, float]] = {
        "A5": (148 * PT_PER_MM, 210 * PT_PER_MM),
        "A4": (210 * PT_PER_MM, 297 * PT_PER_MM),
        "A3": (297 * PT_PER_MM, 420 * PT_PER_MM),
        "SRA3": (320 * PT_PER_MM, 450 * PT_PER_MM),
    }

    def __init__(self, dpi: int = 300):
        """
        Inicializa o impositor com DPI padrão.

        Args:
            dpi: Resolução em DPI para processamento de imagens.
        """
        self.dpi = dpi

    def read_image(self, path: str) -> Image.Image:
        """
        Lê uma imagem ou PDF e retorna como objeto PIL Image.

        Args:
            path: Caminho para o arquivo (PDF, JPG, PNG, etc.).

        Returns:
            Imagem PIL em RGB.

        Raises:
            ValueError: Se o formato não for suportado.
        """
        if path.lower().endswith(".pdf"):
            pdf = fitz.open(path)
            pix = pdf[0].get_pixmap(dpi=self.dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return img
        elif path.lower().endswith((".jpg", ".jpeg", ".png")):
            return Image.open(path).convert("RGB")
        else:
            raise ValueError("Formato de arquivo não suportado. Use PDF, JPG ou PNG.")

    def resize_image_mm(self, img: Image.Image, largura_mm: Optional[float] = None,
                       altura_mm: Optional[float] = None, manter_proporcao: bool = True) -> Image.Image:
        """
        Redimensiona a imagem para as dimensões especificadas em mm.

        Args:
            img: Imagem PIL.
            largura_mm: Largura desejada em mm.
            altura_mm: Altura desejada em mm.
            manter_proporcao: Se True, mantém a proporção.

        Returns:
            Imagem redimensionada.
        """
        if not largura_mm and not altura_mm:
            return img

        # Converte mm -> px
        largura_px = int(largura_mm * self.dpi / 25.4) if largura_mm else None
        altura_px = int(altura_mm * self.dpi / 25.4) if altura_mm else None

        if manter_proporcao:
            img = ImageOps.contain(img, (largura_px or img.width, altura_px or img.height))
        else:
            img = img.resize((largura_px or img.width, altura_px or img.height))

        return img

    def add_bleed(self, img: Image.Image, sangria_mm: float = 3,
                  modo: Literal["mirror", "solid", "none"] = "mirror", cor_sangria: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
        """
        Adiciona sangria (bleed) à imagem.

        Args:
            img: Imagem PIL.
            sangria_mm: Sangria em mm.
            modo: Modo de sangria ("mirror", "solid", "none").

        Returns:
            Imagem com sangria.
        """
        sangria_px = int(sangria_mm * self.dpi / 25.4)
        if sangria_px <= 0 or modo == "none":
            return img

        if modo == "mirror":
            # Criar espelhamento real: bordas espelhadas
            new_width = img.width + 2 * sangria_px
            new_height = img.height + 2 * sangria_px
            new_img = Image.new("RGB", (new_width, new_height), (255, 255, 255))

            # Centro: imagem original
            new_img.paste(img, (sangria_px, sangria_px))

            # Bordas: espelhadas
            # Topo
            top_strip = img.crop((0, 0, img.width, sangria_px)).transpose(Image.FLIP_TOP_BOTTOM)
            new_img.paste(top_strip, (sangria_px, 0))

            # Baixo
            bottom_strip = img.crop((0, img.height - sangria_px, img.width, img.height)).transpose(Image.FLIP_TOP_BOTTOM)
            new_img.paste(bottom_strip, (sangria_px, new_height - sangria_px))

            # Esquerda
            left_strip = img.crop((0, 0, sangria_px, img.height)).transpose(Image.FLIP_LEFT_RIGHT)
            new_img.paste(left_strip, (0, sangria_px))

            # Direita
            right_strip = img.crop((img.width - sangria_px, 0, img.width, img.height)).transpose(Image.FLIP_LEFT_RIGHT)
            new_img.paste(right_strip, (new_width - sangria_px, sangria_px))

            # Cantos: espelhados duplamente
            # Top-left
            tl_corner = img.crop((0, 0, sangria_px, sangria_px)).transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
            new_img.paste(tl_corner, (0, 0))

            # Top-right
            tr_corner = img.crop((img.width - sangria_px, 0, img.width, sangria_px)).transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
            new_img.paste(tr_corner, (new_width - sangria_px, 0))

            # Bottom-left
            bl_corner = img.crop((0, img.height - sangria_px, sangria_px, img.height)).transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
            new_img.paste(bl_corner, (0, new_height - sangria_px))

            # Bottom-right
            br_corner = img.crop((img.width - sangria_px, img.height - sangria_px, img.width, img.height)).transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
            new_img.paste(br_corner, (new_width - sangria_px, new_height - sangria_px))

            return new_img
        elif modo == "solid":
            return ImageOps.expand(img, border=sangria_px, fill=cor_sangria)
        else:
            return img

    def calculate_max_units(self, img: Image.Image, folha: str = "A4", sangria_mm: float = 3,
                           margem_mm: float = 5) -> int:
        """
        Calcula o máximo de unidades que cabem na folha considerando margem de segurança.

        Args:
            img: Imagem PIL.
            folha: Tipo de folha.
            sangria_mm: Sangria em mm.
            margem_mm: Margem de segurança em mm.

        Returns:
            Número máximo de unidades.
        """
        if folha not in self.SHEETS_PT:
            raise ValueError(f"Folha '{folha}' não suportada.")

        folha_w_pt, folha_h_pt = self.SHEETS_PT[folha]
        margem_pt = margem_mm * PT_PER_MM

        # Tamanho da imagem com sangria
        img_with_bleed = self.add_bleed(img, sangria_mm)
        img_w_pt = img_with_bleed.width * 72 / self.dpi
        img_h_pt = img_with_bleed.height * 72 / self.dpi

        # Espaço disponível
        available_w = folha_w_pt - 2 * margem_pt
        available_h = folha_h_pt - 2 * margem_pt

        # Quantas cabem horizontal e vertical
        cols = max(1, int(available_w // img_w_pt))
        rows = max(1, int(available_h // img_h_pt))

        return cols * rows

    def generate_preview(self, img: Image.Image, folha: str = "A4", unidades: int = 10,
                        sangria_mm: float = 3, modo_sangria: Literal["mirror", "solid", "none"] = "mirror",
                        margem_mm: float = 5, gap_mm: float = 0, cor_sangria: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
        """
        Gera uma preview da imposição em uma folha.

        Args:
            img: Imagem PIL.
            folha: Tipo de folha.
            unidades: Número de unidades.
            sangria_mm: Sangria em mm.
            modo_sangria: Modo de sangria.
            margem_mm: Margem em mm.
            gap_mm: Gap em mm.

        Returns:
            Imagem preview da folha.
        """
        if folha not in self.SHEETS_PT:
            raise ValueError(f"Folha '{folha}' não suportada.")

        folha_w_pt, folha_h_pt = self.SHEETS_PT[folha]
        margem_pt = margem_mm * PT_PER_MM
        gap_pt = gap_mm * PT_PER_MM

        # Criar imagem branca para a folha
        preview = Image.new("RGB", (int(folha_w_pt), int(folha_h_pt)), (255, 255, 255))

        img_bleed = self.add_bleed(img, sangria_mm, modo_sangria, cor_sangria)
        img_w_pt = img_bleed.width * 72 / self.dpi
        img_h_pt = img_bleed.height * 72 / self.dpi

        # Redimensionar img_bleed para pt
        img_bleed_resized = img_bleed.resize((int(img_w_pt), int(img_h_pt)), Image.LANCZOS)

        # compute how many cols/rows will be used to place up to 'unidades'
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

        # limit by unidades
        max_slots = cols * rows
        slots = min(unidades, max_slots)

        # compute used width/height and center offsets (top-left coordinate system for PIL)
        used_w = cols * img_w_pt + (cols - 1) * gap_pt
        used_h = rows * img_h_pt + (rows - 1) * gap_pt
        start_x = max(margem_pt, (folha_w_pt - used_w) / 2.0)
        start_y = max(margem_pt, (folha_h_pt - used_h) / 2.0)

        from PIL import ImageDraw
        draw = ImageDraw.Draw(preview)
        border_color = (77, 77, 77)  # K 30%

        count = 0
        for r in range(rows):
            for c in range(cols):
                if count >= slots:
                    break
                px = int(round(start_x + c * (img_w_pt + gap_pt)))
                py = int(round(start_y + r * (img_h_pt + gap_pt)))
                # ensure we don't paste partially outside the preview canvas
                if px < 0 or py < 0 or px + int(img_w_pt) > preview.width or py + int(img_h_pt) > preview.height:
                    # skip placements that would overflow (safety)
                    count += 1
                    continue
                preview.paste(img_bleed_resized, (px, py))
                # draw K 30% border around the placed image
                rect = [px, py, px + int(img_w_pt), py + int(img_h_pt)]
                # stroke width: ~0.5 mm -> convert to preview pixels (points map 1:1 here)
                stroke_px = max(1, int(round(0.5 * PT_PER_MM)))
                draw.rectangle(rect, outline=border_color, width=stroke_px)
                count += 1
            if count >= slots:
                break

        return preview

    def impose_to_pdf(self, img: Image.Image, folha: str = "A4", unidades: int = 10,
                      sangria_mm: float = 3, modo_sangria: Literal["mirror", "solid", "none"] = "mirror",
                      margem_mm: float = 5, gap_mm: float = 0, rotacionar: bool = True,
                      output_path: str = "output.pdf", cor_sangria: Tuple[int, int, int] = (255, 255, 255),
                      multi_mode: Optional[str] = None) -> None:
        """
        Impõe a imagem em um PDF com múltiplas unidades por folha.

        Args:
            img: Imagem PIL.
            folha: Tipo de folha (A5, A4, A3, SRA3).
            unidades: Número de unidades por folha.
            sangria_mm: Sangria em mm.
            modo_sangria: Modo de sangria.
            margem_mm: Margem em mm.
            gap_mm: Espaço entre unidades em mm.
            rotacionar: Se True, otimiza rotação.
            output_path: Caminho para salvar o PDF.

        Raises:
            ValueError: Se parâmetros forem inválidos.
        """
        if folha not in self.SHEETS_PT:
            raise ValueError(f"Folha '{folha}' não suportada. Use uma das: {list(self.SHEETS_PT.keys())}")
        if unidades <= 0:
            raise ValueError("Unidades deve ser maior que 0.")
        if sangria_mm < 0 or margem_mm < 0 or gap_mm < 0:
            raise ValueError("Valores de mm devem ser não-negativos.")

        folha_w, folha_h = self.SHEETS_PT[folha]
        margem_pt = margem_mm * PT_PER_MM
        gap_pt = gap_mm * PT_PER_MM

        # support img being a list (multipage source)
        def _place_single_image(canvas_obj, pil_img):
            # Prepare image with bleed and sizes in points
            pil_img_bleed = self.add_bleed(pil_img, sangria_mm, modo_sangria, cor_sangria)
            img_w_pt_local = pil_img_bleed.width * 72 / self.dpi
            img_h_pt_local = pil_img_bleed.height * 72 / self.dpi

            # compute cols/rows similar to generate_preview
            if img_w_pt_local + gap_pt > 0:
                cols = int((folha_w - 2 * margem_pt + gap_pt) // (img_w_pt_local + gap_pt))
            else:
                cols = 1
            if img_h_pt_local + gap_pt > 0:
                rows = int((folha_h - 2 * margem_pt + gap_pt) // (img_h_pt_local + gap_pt))
            else:
                rows = 1

            cols = max(1, cols)
            rows = max(1, rows)

            per_page = cols * rows

            used_w = cols * img_w_pt_local + (cols - 1) * gap_pt
            used_h = rows * img_h_pt_local + (rows - 1) * gap_pt
            start_x = max(margem_pt, (folha_w - used_w) / 2.0)
            start_y_top = max(margem_pt, (folha_h - used_h) / 2.0)  # distance from top in preview coords

            # place pages repeating this image until unidades reached
            count_total = 0
            while count_total < unidades:
                placed = 0
                for r in range(rows):
                    for c in range(cols):
                        if placed >= per_page or count_total >= unidades:
                            break
                        x_local = start_x + c * (img_w_pt_local + gap_pt)
                        # convert preview top-left y to reportlab bottom-left y
                        y_bl = folha_h - start_y_top - img_h_pt_local - r * (img_h_pt_local + gap_pt)
                        canvas_obj.drawInlineImage(pil_img_bleed, x_local, y_bl, width=img_w_pt_local, height=img_h_pt_local)
                        try:
                            canvas_obj.setStrokeColorRGB(0.3, 0.3, 0.3)
                            canvas_obj.setLineWidth(0.5 * PT_PER_MM)
                            canvas_obj.rect(x_local, y_bl, img_w_pt_local, img_h_pt_local, stroke=1, fill=0)
                            canvas_obj.setLineWidth(1)
                        except Exception:
                            pass
                        placed += 1
                        count_total += 1
                    if placed >= per_page or count_total >= unidades:
                        break
                if count_total < unidades:
                    canvas_obj.showPage()

        c = canvas.Canvas(output_path, pagesize=(folha_w, folha_h))

        # If img is a list, support multipage modes
        if isinstance(img, (list, tuple)):
            if multi_mode == 'repeat_per_page':
                # For each source page, create pages repeating that image
                for pil_img in img:
                    _place_single_image(c, pil_img)
                    c.showPage()
            elif multi_mode == 'one_each':
                # Place one of each image sequentially on sheets, filling grid
                # We'll reuse generate_preview logic to compute placements.
                # Convert each image to its bleed-resized version in points.
                imgs_pt = []
                for pil_img in img:
                    pil_img_bleed = self.add_bleed(pil_img, sangria_mm, modo_sangria, cor_sangria)
                    imgs_pt.append((pil_img_bleed, pil_img_bleed.width * 72 / self.dpi, pil_img_bleed.height * 72 / self.dpi))

                # compute cols/rows by using first image size as reference (approx)
                if imgs_pt:
                    ref_w = imgs_pt[0][1]
                    ref_h = imgs_pt[0][2]
                else:
                    ref_w = ref_h = 1
                cols = max(1, int((folha_w - 2 * margem_pt + gap_pt) // (ref_w + gap_pt)))
                rows = max(1, int((folha_h - 2 * margem_pt + gap_pt) // (ref_h + gap_pt)))
                per_page = cols * rows
                idx = 0
                used_w = cols * ref_w + (cols - 1) * gap_pt
                used_h = rows * ref_h + (rows - 1) * gap_pt
                start_x = max(margem_pt, (folha_w - used_w) / 2.0)
                start_y_top = max(margem_pt, (folha_h - used_h) / 2.0)
                while idx < len(imgs_pt):
                    count = 0
                    for r in range(rows):
                        for c_idx in range(cols):
                            if count >= per_page or idx >= len(imgs_pt):
                                break
                            pil_img_bleed, iw, ih = imgs_pt[idx]
                            x = start_x + c_idx * (ref_w + gap_pt)
                            y_bl = folha_h - start_y_top - ref_h - r * (ref_h + gap_pt)
                            c.drawInlineImage(pil_img_bleed, x, y_bl, width=iw, height=ih)
                            try:
                                c.setStrokeColorRGB(0.3, 0.3, 0.3)
                                c.setLineWidth(0.5 * PT_PER_MM)
                                c.rect(x, y_bl, iw, ih, stroke=1, fill=0)
                                c.setLineWidth(1)
                            except Exception:
                                pass
                            idx += 1
                            count += 1
                        if count >= per_page or idx >= len(imgs_pt):
                            break
                    c.showPage()
            else:
                # fallback: repeat behavior
                for pil_img in img:
                    _place_single_image(c, pil_img)
                    c.showPage()
            c.save()
            return

        # default single image behavior (centered to match preview)
        img = self.add_bleed(img, sangria_mm, modo_sangria, cor_sangria)

        img_w_pt = img.width * 72 / self.dpi
        img_h_pt = img.height * 72 / self.dpi

        # compute cols/rows and centering like generate_preview
        if img_w_pt + gap_pt > 0:
            cols = int((folha_w - 2 * margem_pt + gap_pt) // (img_w_pt + gap_pt))
        else:
            cols = 1
        if img_h_pt + gap_pt > 0:
            rows = int((folha_h - 2 * margem_pt + gap_pt) // (img_h_pt + gap_pt))
        else:
            rows = 1

        cols = max(1, cols)
        rows = max(1, rows)

        per_page = cols * rows
        used_w = cols * img_w_pt + (cols - 1) * gap_pt
        used_h = rows * img_h_pt + (rows - 1) * gap_pt
        start_x = max(margem_pt, (folha_w - used_w) / 2.0)
        start_y_top = max(margem_pt, (folha_h - used_h) / 2.0)

        count_total = 0
        while count_total < unidades:
            placed = 0
            for r in range(rows):
                for c_idx in range(cols):
                    if placed >= per_page or count_total >= unidades:
                        break
                    x = start_x + c_idx * (img_w_pt + gap_pt)
                    y_bl = folha_h - start_y_top - img_h_pt - r * (img_h_pt + gap_pt)
                    c.drawInlineImage(img, x, y_bl, width=img_w_pt, height=img_h_pt)
                    try:
                        c.setStrokeColorRGB(0.3, 0.3, 0.3)
                        c.setLineWidth(0.5 * PT_PER_MM)
                        c.rect(x, y_bl, img_w_pt, img_h_pt, stroke=1, fill=0)
                        c.setLineWidth(1)
                    except Exception:
                        pass
                    placed += 1
                    count_total += 1
                if placed >= per_page or count_total >= unidades:
                    break
            if count_total < unidades:
                c.showPage()

        c.save()
