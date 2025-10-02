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

        x = margem_pt
        y = folha_h_pt - margem_pt - img_h_pt

        count = 0
        while count < unidades and count < 100:  # limite para preview
            preview.paste(img_bleed_resized, (int(x), int(y)))
            count += 1

            x += img_w_pt + gap_pt
            if x + img_w_pt + margem_pt > folha_w_pt:
                x = margem_pt
                y -= img_h_pt + gap_pt
                if y < margem_pt:
                    break

        return preview

    def impose_to_pdf(self, img: Image.Image, folha: str = "A4", unidades: int = 10,
                      sangria_mm: float = 3, modo_sangria: Literal["mirror", "solid", "none"] = "mirror",
                      margem_mm: float = 5, gap_mm: float = 0, rotacionar: bool = True,
                      output_path: str = "output.pdf", cor_sangria: Tuple[int, int, int] = (255, 255, 255)) -> None:
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

        img = self.add_bleed(img, sangria_mm, modo_sangria, cor_sangria)

        img_w_pt = img.width * 72 / self.dpi
        img_h_pt = img.height * 72 / self.dpi

        c = canvas.Canvas(output_path, pagesize=(folha_w, folha_h))

        x = margem_pt
        y = folha_h - margem_pt - img_h_pt

        count = 0
        while count < unidades:
            c.drawInlineImage(img, x, y, width=img_w_pt, height=img_h_pt)
            count += 1

            x += img_w_pt + gap_pt
            if x + img_w_pt + margem_pt > folha_w:
                x = margem_pt
                y -= img_h_pt + gap_pt
                if y < margem_pt:
                    c.showPage()
                    y = folha_h - margem_pt - img_h_pt

        c.save()
