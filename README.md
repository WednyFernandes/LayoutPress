# Impositor App

Aplicativo desktop para imposição de imagens em PDFs para impressão pré-impressão.

## Funcionalidades

- Carregar imagens (JPG, PNG) ou PDFs
- Redimensionar imagens mantendo proporção
- Adicionar sangria (bleed) com modos: mirror (espelhar bordas), solid (branco), none (sem)
- Impor múltiplas unidades por folha (A5, A4, A3, SRA3)
- Preview em tempo real da folha final
- Cálculo automático do máximo de unidades por folha
- Interface intuitiva com seções organizadas
- Tooltips explicativos em todos os controles
- Exportar para PDF pronto para impressão

## Como Usar

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

2. Execute o aplicativo:
   ```bash
   python main.py
   ```

3. **Passo 1**: Clique em "📁 Abrir Imagem ou PDF" e selecione seu arquivo.

4. **Passo 2**: Ajuste o tamanho da imagem se necessário (largura/altura em mm).

5. **Passo 3**: Configure a imposição:
   - Escolha o tipo de folha
   - Ajuste sangria, margem, etc.
   - O número máximo de unidades é calculado automaticamente

6. **Passo 4**: Veja o preview em tempo real e clique em "💾 Exportar PDF".

## Dicas para Leigos

- **Sangria (Bleed)**: Margem extra que será cortada. Use 3mm para segurança.
- **Mirror**: Espelha as bordas da imagem para uma transição suave.
- **Solid**: Adiciona fundo branco.
- **Margem**: Deixe pelo menos 5mm para evitar cortes na imagem útil.
- O preview mostra exatamente como ficará a folha impressa.
- Os campos são preenchidos automaticamente com valores ideais.

## Refatoração

O projeto foi refatorado para melhor estrutura:
- Classe `Impositor` encapsula a lógica de processamento
- Type hints para melhor legibilidade
- Validação de entrada
- Documentação com docstrings
- Dependências limpas
- GUI melhorada com tooltips e preview dinâmico