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

1. Crie no GitHub um repositório **público** com o nome exato `SEUUSUARIO.github.io`.
2. No terminal, dentro desta pasta:

```bash
git remote add origin https://github.com/SEUUSUARIO/SEUUSUARIO.github.io.git
git push -u origin main
```

3. Em **Settings → Pages**, defina Source = `Deploy from a branch`, branch `main`, pasta `/ (root)`.
4. Em poucos minutos o site fica em `https://SEUUSUARIO.github.io/`.

Toda vez que quiser atualizar: `git add -A && git commit -m "..." && git push`.

## O que NÃO entra neste repositório

O PDF do guia é o produto pago. Em repositório público qualquer pessoa baixa o arquivo,
e o Google indexa. A entrega tem que acontecer fora daqui: e-mail pós-compra, área de
membros ou link assinado com expiração. Por isso `*.pdf` está no `.gitignore`.
