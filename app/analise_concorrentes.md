# Análise de Concorrentes — Meta Ads Library (energia solar)

**Coletado em:** 2026-07-17
**Fonte:** Meta Ads Library (dados públicos), país BR, filtro "anúncios ativos"
**Método:** MCP Meta Ads Library + navegação assistida (não Apify — ver nota no fim)

## Achado inicial importante

Dos 8 nomes/sites pesquisados (NeoSolar, Portal Solar, Solmais, SGV Solar, Energia Total,
Aldo Solar, Sou Energy, Dalsun), **apenas 4 têm anúncios ativos no Meta agora**:
**Aldo Solar, NeoSolar Energia, Dalsun e SGV Solar**.

Portal Solar (194,5 mil seguidores), Energia Total, Sou Energy e Solmais não têm nenhum
anúncio ativo nem histórico visível na biblioteca — sinal de que investem em outros canais
(SEO, Google Ads, marketplace/comparador) em vez de Meta Ads, ou rodam via conta/página
diferente da que identificamos.

## Anúncios coletados

| Concorrente | Anúncios ativos | Público-alvo | Anúncio mais antigo ainda ativo |
|---|---|---|---|
| Aldo Solar | 24 | B2B (integradores) | 22/abr/2026 (~3 meses no ar) |
| NeoSolar Energia | 7 | B2B (integradores, Off-Grid) | 16/mar/2026 (~4 meses no ar) |
| Dalsun | 7 | B2C (consumidor final) | 30/jun/2026 (~2 semanas) |
| SGV Solar | 2 | B2B (integradores) | 06/jul/2026 |

**Leitura direta:** os anúncios com mais tempo no ar (Aldo e NeoSolar) são os dois que miram
o **integrador/instalador**, não o consumidor residencial — sugere que esse é o público que
retém melhor performance pra eles a ponto de manter a campanha ativa por meses.

## Os 10 padrões que mais se repetem

1. **Gatilho de dor financeira imediata** — "Gastando R$400, R$500, R$600 de conta de luz?"
   (Dalsun). Único padrão 100% B2C encontrado; repetido nas 7 variações ativas do mesmo anúncio.

2. **Prova de autoridade/tempo de mercado** — "Maior Distribuidora de Energia Solar do Brasil",
   "+40 anos" (Aldo Solar); "líder em Off-Grid", "certificada pela ABSOLAR com selo Triplo A",
   "+15 anos de experiência" (NeoSolar).

3. **CTA via WhatsApp como canal primário** — links `api.whatsapp.com` e "Enviar mensagem pelo
   WhatsApp" dominam os CTAs de Aldo Solar; SGV Solar usa "Fale conosco" equivalente.

4. **Copy dirigida ao integrador, não ao cliente final** — 3 das 4 marcas ativas (Aldo, NeoSolar,
   SGV) falam diretamente com "você, integrador" — é o padrão dominante no conjunto coletado.

5. **Storytelling de objeção seguido de lista de bullets ✅** — "Você já perdeu venda porque a
   distribuidora demorou pra responder?" → lista de diferenciais com emoji de check (NeoSolar).

6. **Emoji temático intercalado no meio do texto** — ☀️⚡🔋📲✅🚀 aparecem em praticamente todo
   anúncio das 4 marcas, inclusive nas versões B2B mais "corporativas".

7. **Hashtags de marca no fechamento do texto** — `#AldoSolar #GiganteSolar #IntegradorSolar
   #EnergiaSolar` — padrão exclusivo da Aldo Solar, mas usado de forma consistente em quase
   todos os criativos dela.

8. **Newsjacking sazonal (Copa do Mundo)** — Aldo Solar ("Copa Gigantes do Financiamento") e
   NeoSolar ("Vai arriscar ficar sem energia e perder o gol do Brasil?") — as duas maiores
   contas ativas aproveitaram o mesmo gancho de calendário.

9. **Financiamento/crédito como quebra de objeção central** — "taxas a partir de 1,29% ao mês",
   "carta de consórcio contemplada pode ser usada pra investir em energia solar" (Aldo Solar) —
   indica que acesso a crédito, não o produto em si, é a principal barreira que essas marcas
   atacam em texto.

10. **Visual dividido em dois estilos claros por público:**
    - **B2B:** foto de produto/caixa do kit, cores fortes (vermelho/amarelo), selos de urgência
      logística ("PRONTA ENTREGA EM TODO NORDESTE" — SGV Solar; inversores GoodWe fotografados
      — Aldo Solar).
    - **B2C:** foto real de telhado residencial com painéis instalados, céu azul, texto
      sobreposto simples (Dalsun — mesmo criativo usado em todas as variações ativas).

## Perfil de cliente sugerido, com base nos padrões observados

### Perfil A — o mais perseguido pelos concorrentes ativos (B2B / integrador)

- Já opera como integrador/instalador solar, com CNPJ ativo
- Dores centrais: fornecedor lento pra responder, falta de estoque, dificuldade de
  financiar o cliente final, prazo de entrega/logística
- Decisor: dono ou gestor comercial de integradora pequena/média
- Gatilhos que funcionam nos concorrentes: agilidade logística, suporte técnico,
  condições de financiamento, prova de autoridade (selo, anos de mercado)
- Canal de conversão preferido: WhatsApp direto, não formulário

### Perfil B — o único perseguido diretamente por um concorrente (B2C / residencial)

- Proprietário de imóvel residencial com conta de luz de R$400+/mês
- Dor: conta de luz cara, sem noção clara de quanto economizaria
- Gatilho: economia imediata (até 90%), simulação rápida, prova visual (foto real do telhado)
- Único concorrente ativo mirando esse perfil: Dalsun

### Observação para o projeto "Sistema de Leads para Empresas"

Nenhum dos 4 concorrentes ativos mira exatamente o segmento do seu projeto — **empresas
(CNPJ) como consumidoras finais de energia solar** (supermercado, hotel, indústria etc. do
seu ICP). Aldo/NeoSolar/SGV vendem equipamento *para* integradores (B2B2B), e Dalsun mira
residências (B2C). Isso pode ser lido como um espaço pouco disputado diretamente no Meta Ads
— ou como um sinal de que o público-empresa se converte melhor por outros canais (prospecção
ativa/SDR, como o seu projeto já está construindo, em vez de anúncio de massa).

## Nota metodológica

Não havia MCP do Apify conectado nesta sessão. Os dados foram coletados via MCP nativo
`Meta_ADS_MCP` (busca estruturada por `page_id`) combinado com navegação assistida na
Meta Ads Library pública para identificar corretamente qual página do Facebook corresponde
a cada concorrente (a busca por palavra-chave sozinha traz muito ruído de outras marcas).
Dados públicos, sem necessidade de login além do já autenticado no Chrome.
