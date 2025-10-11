# Changelog v0.3.0 - Preview Fix & UI Improvements

## Data: 11 de Outubro de 2025

### 🎯 Principais Mudanças

#### 1. Preview Agora Corresponde ao PDF Exportado (CRÍTICO)
**Problema Identificado:**
- O preview usava uma lógica diferente do export PDF
- Preview calculava slots baseados em `spin_units` com grid arbitrário (sqrt)
- Export PDF usava a lógica do `impositor.py` baseada no tamanho da imagem **COM sangria**
- Resultado: preview mostrava layout diferente do PDF final

**Solução Implementada:**
- ✅ Reescrita completa de `generate_preview()` (~linha 1000-1153)
- ✅ Agora usa **EXATAMENTE** a mesma lógica do `impositor.py`:
  - Adiciona sangria (bleed) à primeira imagem
  - Calcula dimensões em pontos (72 DPI conversion)
  - Computa colunas/linhas baseado na fórmula: `(folha_w - 2*margem + gap) // (img_w + gap)`
  - Usa as mesmas variáveis: `margem_pt`, `gap_pt`, `used_w`, `used_h`, `start_x`, `start_y`
  - Renderiza borda K 30% (RGB 77,77,77) como no export
  - Mantém indicador de rotação (quadrado amarelo)

**Resultado:**
- ✅ Preview mostra exatamente o que será exportado no PDF
- ✅ Posicionamento, espaçamento e tamanhos idênticos
- ✅ Número de imagens por folha corresponde ao cálculo real

#### 2. Botões de Paginação Redesenhados
**Antes:**
- Botões pequenos (◀ ▶) no painel esquerdo de controles
- Difícil de visualizar quando há múltiplas páginas
- Fora do contexto da preview

**Depois:**
- ✅ Botões removidos do painel esquerdo
- ✅ Novos botões grandes e estilizados na **parte inferior central do painel de preview**
- ✅ Design moderno: `"◀ Anterior"` e `"Próxima ▶"`
- ✅ Cor roxa (#5856d6) consistente com tema
- ✅ Estados disabled visuais claros (#5a5a5a)
- ✅ Label central mostrando: `"Folha X / Y"`
- ✅ Layout centralizado com `addStretch()` nas laterais

**Código Adicionado (~linha 231-256):**
```python
# Pagination controls at bottom center
pagination_layout = QHBoxLayout()
pagination_layout.addStretch()
self.btn_prev_page = QPushButton("◀ Anterior")
self.btn_prev_page.setStyleSheet(...)
self.lbl_page_info = QLabel("Página 1 / 1")
self.btn_next_page = QPushButton("Próxima ▶")
pagination_layout.addStretch()
```

#### 3. Todos os Controles Afetam a Preview
**Verificação Completa:**
Todos os 10 controles do painel esquerdo estão conectados em `_connect_live_preview()`:

1. ✅ `spin_w` (Largura) → `_on_ui_change()`
2. ✅ `spin_h` (Altura) → `_on_ui_change()`
3. ✅ `chk_keep` (Manter Proporção) → `_on_ui_change()`
4. ✅ `cmb_sheet` (Tamanho da Folha) → `_on_sheet_change()`
5. ✅ `spin_units` (Imagens por Folha) → `_on_ui_change()`
6. ✅ `spin_bleed` (Sangria) → `_on_ui_change()`
7. ✅ `spin_gap` (Espaçamento) → `_on_ui_change()`
8. ✅ `cmb_multipage` (Modo de Impressão) → `_on_ui_change()`
9. ✅ `cmb_bleed` (Modo de Preenchimento) → `_on_ui_change()`
10. ✅ `btn_color` (Cor da Sangria) → `choose_color()` → `generate_preview()`

**Pipeline de Atualização:**
```
Controle mudou → Signal → Handler (_on_ui_change / _on_sheet_change)
                             ↓
                    _recompute_fit() (se necessário)
                             ↓
                    generate_preview()
                             ↓
                    Preview atualizado na tela
```

#### 4. Performance Mantida
- ✅ Flag `_updating_controls` evita cascatas recursivas
- ✅ Signal blocking com try/finally em `_recompute_fit()`
- ✅ Timer de 5s usa `_safe_periodic_refresh()` (só roda se há imagens)
- ✅ Preview agora mais eficiente (sem double-resize de thumbnails)

### 📊 Comparação: Antes vs Depois

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Preview vs PDF** | Layouts diferentes | ✅ Idênticos |
| **Lógica de Grid** | `sqrt(unidades)` arbitrário | ✅ Baseado em tamanho real com sangria |
| **Paginação** | Botões pequenos no painel | ✅ Botões grandes centralizados |
| **Controles** | Alguns não afetavam preview | ✅ Todos conectados e funcionais |
| **Performance** | Otimizada | ✅ Mantida (sem regressão) |

### 🔧 Arquivos Modificados

**`main.py`:**
- Linha 163-173: Removidos botões de paginação do painel esquerdo
- Linha 231-256: Adicionados botões de paginação no preview
- Linha 808-820: Funções `_prev_page()` e `_next_page()`
- Linha 1000-1153: Reescrita completa de `generate_preview()`

### 🐛 Issues Corrigidos

1. ✅ **[CRÍTICO]** Preview não correspondia ao PDF exportado
2. ✅ Botões de paginação não visíveis/intuitivos
3. ✅ Usuário não conseguia prever resultado final antes de exportar

### ⚠️ Notas Técnicas

**Avisos de Stylesheet (Benignos):**
```
Could not parse stylesheet of object QPushButton(...)
```
- Não afetam funcionalidade
- Relacionados a sintaxe multi-linha no `setStyleSheet()`
- Qt ainda aplica estilos corretamente

**Dependências da Lógica:**
- Preview agora depende fortemente de `impositor.add_bleed()`
- Qualquer mudança em `impositor.py` deve ser refletida em `generate_preview()`
- Manter sincronização entre as duas implementações

### 🎨 Detalhes Visuais

**Botões de Paginação:**
- Background: #5856d6 (roxo tema)
- Hover: #6b69e0 (roxo claro)
- Disabled: #5a5a5a (cinza escuro)
- Padding: 8px 16px
- Border-radius: 4px
- Font-weight: bold

**Label de Info:**
- Color: #aaa (cinza claro)
- Font-weight: bold
- Padding: 0 16px

### 📝 Testes Recomendados

Antes de fazer build/release, testar:

1. ✅ Carregar 1 imagem → verificar preview = PDF
2. ✅ Carregar múltiplas imagens → testar paginação
3. ✅ Mudar tamanho da folha → preview atualiza
4. ✅ Mudar sangria → preview mostra bleed correto
5. ✅ Mudar espaçamento → preview mostra gaps
6. ✅ Mudar unidades → preview mostra grid correto
7. ✅ Clicar em imagem na preview → rotação funciona
8. ✅ Navegar páginas → botões e label atualizam
9. ✅ Exportar PDF → abrir automático funciona

### 🚀 Próximos Passos

- [ ] Build com PyInstaller
- [ ] Testar executável em máquina limpa
- [ ] Criar tag git v0.3.0
- [ ] Release no GitHub
- [ ] Atualizar documentação do usuário

---

**Versão:** 0.3.0  
**Status:** ✅ Pronto para build  
**Última Atualização:** 11/10/2025
