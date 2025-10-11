# LayoutPress v0.3.0 - Preview Accuracy & UX Improvements

## 🎯 Highlights

Esta versão traz correções críticas que garantem que o **preview corresponde exatamente ao PDF exportado**, além de melhorias significativas na interface e experiência do usuário.

## ✨ Principais Novidades

### 🔧 Preview Agora Corresponde ao PDF Exportado (CRÍTICO)
**Problema Resolvido:**
- Versões anteriores mostravam um layout diferente no preview comparado ao PDF final
- Preview usava lógica de grid arbitrária enquanto export usava cálculo baseado em sangria

**Solução:**
- ✅ Preview agora usa **exatamente a mesma lógica** do motor de imposição (`impositor.py`)
- ✅ Cálculo baseado no tamanho real da imagem COM sangria aplicada
- ✅ Posicionamento, espaçamento e número de imagens por folha idênticos ao PDF final
- ✅ O que você vê é exatamente o que será impresso!

### 🎨 Interface Redesenhada

**Botões de Paginação Modernos:**
- ✅ Removidos os botões pequenos do painel de controles
- ✅ Novos botões grandes e estilizados na **parte inferior central do preview**
- ✅ Design intuitivo: `"◀ Anterior"` e `"Próxima ▶"`
- ✅ Indicador visual claro: `"Folha X / Y"`
- ✅ Cores consistentes com o tema roxo (#5856d6)

**Dark Theme Completo:**
- ✅ Tema escuro aplicado em toda a interface
- ✅ Cores equilibradas para conforto visual
- ✅ Contraste adequado para melhor legibilidade

### 🚀 Funcionalidades Corrigidas

**Modo Multipágina Funcionando no Preview:**
- ✅ Preview agora respeita o modo selecionado:
  - **"Mesma imagem repetida"**: repete a primeira imagem em todos os slots
  - **"Imagens diferentes em sequência"**: usa imagens diferentes para cada slot
- ✅ Comportamento idêntico entre preview e export

**Todos os Controles Afetam o Preview:**
- ✅ 10 controles verificados e conectados:
  - Largura e Altura (mm)
  - Manter Proporção
  - Tamanho da Folha
  - Quantidade por Folha
  - Sangria/Margem de Corte
  - Espaçamento entre Imagens
  - Modo de Impressão
  - Modo de Preenchimento da Sangria
  - Cor da Sangria
- ✅ Preview atualiza em tempo real ao alterar qualquer parâmetro

**Auto-Open PDF:**
- ✅ PDF abre automaticamente após exportação bem-sucedida
- ✅ Funciona em Windows (mais plataformas em breve)

### ⚡ Otimizações de Performance

- ✅ Sistema de bloqueio de sinais para evitar cascatas recursivas
- ✅ Timer de refresh otimizado (só roda quando necessário)
- ✅ Flag `_updating_controls` previne loops infinitos
- ✅ Preview renderiza de forma mais eficiente

## 📦 Download

**Executável para Windows:**
- `Layoutpress.exe` (~75 MB)
- Não requer instalação - apenas baixe e execute
- Inclui todas as dependências necessárias

## 🔧 Melhorias Técnicas

### Para Desenvolvedores:

**Preview Engine Reescrito:**
```python
# Agora usa a mesma lógica do impositor.py
- Adiciona sangria à primeira imagem
- Calcula dimensões em pontos (72 DPI)
- Computa cols/rows: (folha_w - 2*margem + gap) // (img_w + gap)
- Renderiza com bordas K 30% (RGB 77,77,77)
```

**Arquivos Modificados:**
- `main.py`: Reescrita de `generate_preview()`, UI de paginação, correções multipage
- `impositor_app.spec`: Adicionado `VERSION` aos datas
- `dark_theme.qss`: Theme completo
- `VERSION`: Atualizado para 0.3.0

## 🐛 Bugs Corrigidos

1. ✅ Preview mostrava layout diferente do PDF exportado
2. ✅ Modo multipágina não funcionava corretamente no preview
3. ✅ Alguns controles não atualizavam o preview
4. ✅ Botões de paginação pouco visíveis/intuitivos
5. ✅ Performance degradada por cascatas de sinais recursivos

## 🎓 Como Usar

1. **Carregar Arquivos:**
   - Clique em "📁 Abrir Arquivo(s)"
   - Selecione uma ou múltiplas imagens/PDFs
   - Preview atualiza automaticamente

2. **Ajustar Parâmetros:**
   - Configure tamanho, quantidade, sangria, espaçamento
   - Preview mostra resultado em tempo real
   - Use os botões de paginação se houver múltiplas folhas

3. **Exportar:**
   - Clique em "💾 Salvar PDF"
   - PDF abre automaticamente após criação
   - Resultado idêntico ao preview!

## 📊 Comparação: v0.2.0 → v0.3.0

| Aspecto | v0.2.0 | v0.3.0 |
|---------|--------|--------|
| **Preview = PDF** | ❌ Diferente | ✅ Idêntico |
| **Modo Multipage Preview** | ❌ Não funciona | ✅ Funcional |
| **Paginação** | Botões pequenos | ✅ Botões grandes centralizados |
| **Controles Update Preview** | ⚠️ Alguns não | ✅ Todos funcionam |
| **Performance** | ⚠️ Lenta (cascatas) | ✅ Otimizada |
| **Auto-open PDF** | ❌ Não | ✅ Sim |
| **Dark Theme** | ⚠️ Parcial | ✅ Completo |

## ⚠️ Notas Importantes

**Avisos de Console (Benignos):**
```
Could not parse stylesheet of object QPushButton(...)
```
- Não afetam funcionalidade
- Relacionados a sintaxe multi-linha do Qt
- Estilos são aplicados corretamente

**Requisitos:**
- Windows 10 ou superior
- Nenhuma instalação adicional necessária
- 100 MB de espaço livre em disco

## 🙏 Agradecimentos

Obrigado a todos que testaram as versões anteriores e reportaram issues!

## 🔗 Links

- **Repositório:** https://github.com/WednyFernandes/LayoutPress
- **Issues:** https://github.com/WednyFernandes/LayoutPress/issues
- **Website:** https://wednyfernandes.com.br

---

**Desenvolvido por:** Wedny Fernandes  
**Data de Release:** 11 de Outubro de 2025  
**Versão:** 0.3.0  
**Branch:** dev
