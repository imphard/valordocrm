# Provando o valor do CRM — site

Site estático do infoproduto. Sem build, sem dependências: são arquivos HTML e CSS servidos direto pelo GitHub Pages.

## Estrutura

```
index.html                     página de vendas  (PLACEHOLDER — substituir)
calculadora/index.html         calculadora       (PLACEHOLDER — substituir)
blog/index.html                índice dos artigos
blog/como-medir-crm/           artigo: "como medir CRM"
blog/metricas-de-crm/          artigo: "métricas de CRM"
assets/site.css                design system (paleta, tipografia, componentes)
assets/fonts/                  Appetite Pro (Regular, Itálico, Bold, Heavy)
404.html  robots.txt  sitemap.xml  .nojekyll
```

`.nojekyll` desliga o processamento Jekyll do GitHub Pages — sem ele, pastas iniciadas
com `_` são ignoradas e alguns arquivos somem da publicação.

## Paleta e tipografia

Tudo vem de variáveis CSS no topo de `assets/site.css`. Trocar os três hexes de marca
(`--magenta`, `--laranja`, `--roxo`) reflete no site inteiro.

As fontes são servidas como arquivos `.otf` em `assets/fonts/`, não em base64. Em um site
com várias páginas isso é melhor: o navegador baixa uma vez e reaproveita em todas, em vez
de carregar ~250 KB de base64 embutido em cada HTML.

> **Licença da fonte:** arquivos `.otf` publicados ficam acessíveis para download. Confirme
> se a licença da Appetite Pro cobre uso como webfont antes de publicar. Se não cobrir,
> as saídas são comprar a licença web, converter para `.woff2` com subset apenas dos
> caracteres usados, ou aplicar a fonte só nos títulos.

## Rodar localmente

```bash
python -m http.server 5510
```

## Publicar no GitHub Pages

O site roda em `valordocrm.com.br`. Como o domínio é próprio, o repositório pode ter
qualquer nome: com domínio customizado, um repositório comum também é servido na raiz
do domínio, sem o nome dele no caminho da URL.

### 1. Criar o repositório

No GitHub, um repositório **público** e **vazio** chamado `valordocrm`
(sem README, sem .gitignore, sem licença — este projeto já tem os dois primeiros).

### 2. Enviar os arquivos

```bash
git remote add origin https://github.com/imphard/valordocrm.git
git push -u origin main
```

O Git Credential Manager abre o navegador para você entrar na conta do GitHub.

### 3. Apontar o DNS

No painel do Registro.br, em **DNS → Editar Zona** (o domínio já usa o DNS automático
deles, então não é preciso trocar servidor de nomes):

| Tipo  | Nome  | Valor |
|-------|-------|-------|
| A     | `@`   | `185.199.108.153` |
| A     | `@`   | `185.199.109.153` |
| A     | `@`   | `185.199.110.153` |
| A     | `@`   | `185.199.111.153` |
| AAAA  | `@`   | `2606:50c0:8000::153` |
| AAAA  | `@`   | `2606:50c0:8001::153` |
| AAAA  | `@`   | `2606:50c0:8002::153` |
| AAAA  | `@`   | `2606:50c0:8003::153` |
| CNAME | `www` | `imphard.github.io.` |

Os quatro registros A são os endereços do GitHub Pages, e os quatro AAAA são os mesmos
em IPv6. O `www` aponta para o GitHub, que o redireciona para o endereço sem `www`.

### 4. Ligar o Pages

Em **Settings → Pages**: Source = `Deploy from a branch`, branch `main`, pasta `/ (root)`.
O campo Custom domain já vem preenchido com `valordocrm.com.br`, porque o arquivo `CNAME`
na raiz deste repositório faz esse papel.

Quando a verificação do DNS passar, marque **Enforce HTTPS**. O certificado é emitido
automaticamente e de graça. O DNS costuma propagar em minutos; o certificado pode levar
até uma hora depois disso.

### Atualizações seguintes

```bash
git add -A && git commit -m "descrição da mudança" && git push
```

O site atualiza sozinho em um ou dois minutos.

## O que NÃO entra neste repositório

O PDF do guia é o produto pago. Em repositório público qualquer pessoa baixa o arquivo,
e o Google indexa. A entrega tem que acontecer fora daqui: e-mail pós-compra, área de
membros ou link assinado com expiração. Por isso `*.pdf` está no `.gitignore`.

## Checkout e entrega (Kiwify)

A venda e a entrega do PDF acontecem na Kiwify, fora deste repositório. O site só leva o
visitante até lá.

- O botão de compra da página de vendas aponta para o link de checkout
  (`https://pay.kiwify.com.br/jm98Xz9`).
- `assets/rastreio.js` está incluído em todas as páginas. Ele lê o `?ref=` da URL,
  guarda na sessão e injeta `utm_source`, `utm_medium` e `utm_content` em qualquer link
  que contenha `kiwify`. Com isso o painel da Kiwify mostra qual artigo trouxe a venda.
- Os links internos já saem marcados: `?ref=artigo-como-medir-crm`,
  `?ref=artigo-metricas-de-crm`, `?ref=blog`, `?ref=calculadora`.
- Nada mais é necessário: sem cookie de terceiros, sem script externo, sem consentimento
  de rastreio, porque a informação não sai do domínio até o clique de compra.
