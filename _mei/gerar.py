"""Gera as páginas do Guia do MEI a partir de _mei/ocupacoes.json.

Rodar da raiz do repositório:  python _mei/gerar.py

Escreve: index.html (home), mei/ (lista A a Z), mei/<ocupacao>/ (uma por ocupação),
calculadora-das-mei/, limite-mei/ e sitemap.xml (com as páginas do CRM junto).
Nada de travessão em texto que o público lê.
"""
import html
import json
import re
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITE = "https://valordocrm.com.br"
HOJE = date.today().isoformat()
HOJE_BR = date.today().strftime("%d/%m/%Y")
ANO = 2026

# Valores de 2026 (salário mínimo de R$ 1.621)
MINIMO = 1621.00
INSS = round(MINIMO * 0.05, 2)
INSS_CAMINHONEIRO = round(MINIMO * 0.12, 2)
LIMITE = 81000
LIMITE_CAMINHONEIRO = 251600
# LC 238/2026 (sancionada em 21/10/2026): 110 mil em 2027 e 140 mil a partir de 2028;
# dois empregados a partir de 2027. O caminhoneiro não mudou.
LIMITE_2027 = 110000
LIMITE_2028 = 140000
LEI = '<a href="/novo-limite-mei/">LC 238/2026</a>'

# Conta do AdSense (o mesmo id vai no ads.txt da raiz)
ADSENSE = "ca-pub-5457625892554793"

# Links de parceiros. Bloco só aparece quando a url estiver preenchida.
OFERTAS = {
    "contabilidade": {
        "url": "",
        "rotulo": "Indicação",
        "titulo": "Quer alguém cuidando disso por você?",
        "itens": ["DAS", "Declaração anual", "Notas fiscais"],
        "icone": "contador",
        "texto": "Prefere que alguém cuide do DAS, da declaração e das notas por você? Uma contabilidade online resolve tudo pelo celular.",
        "botao": "Ver contabilidade online",
    },
    "maquininha": {
        "url": "https://buy.infinitepay.io/smart?rid=pataconecta",
        "rotulo": "Indicação InfinitePay",
        "titulo": "Comece a receber no cartão e no Pix com o CNPJ do MEI",
        "texto": "Com a InfinitePay você usa a maquininha Smart ou cobra por aproximação no próprio celular, com o InfiniteTap, sem comprar aparelho.",
        "itens": ["Cartão e Pix", "Cobra pelo celular", "Conta no CNPJ do MEI"],
        "botao": "Quero a maquininha",
        # segundo botão, opcional
        "url2": "https://infinitepay.onelink.me/IGWD/pataconecta",
        "botao2": "Cobrar pelo celular",
        "icone": "maquininha",
    },
}

# Produto próprio: a Planilha do MEI, vendida na Kiwify. Sem link, a página de venda sai
# com noindex e botão "em breve", e as chamadas nas outras páginas não aparecem.
PLANILHA = {"kiwify": "", "preco": "47"}

POPULARES = [
    "Cabeleireiro(a) independente", "Manicure/pedicure independente", "Barbeiro independente",
    "Esteticista independente", "Maquiador(a) independente", "Depilador(a) independente",
    "Diarista independente", "Eletricista em residências e estabelecimentos comerciais independente",
    "Encanador independente", "Pedreiro independente", "Pintor(a) de parede independente",
    "Motorista (por aplicativo ou não) independente", "Motoboy independente",
    "Confeiteiro(a) independente", "Doceiro(a) independente", "Marmiteiro(a) independente",
    "Salgadeiro(a) independente", "Costureiro(a) de roupas sob medida independente",
    "Cuidador(a) de idosos e enfermos independente", "Esteticista de animais domésticos independente",
    "Professor(a) particular independente", "Instrutor(a) de idiomas independente",
    "Editor(a) de vídeo independente", "Técnico(a) de manutenção de computador independente",
    "Jardineiro(a) independente", "Tatuador(a) independente", "Lavador(a) e polidor de carro independente",
    "Animador(a) de festas independente",
]


# Palavras que as pessoas digitam e que não estão no nome oficial (só entram na busca da home)
APELIDOS = {
    "Cabeleireiro(a) independente": "salão cabelo",
    "Manicure/pedicure independente": "unha unhas",
    "Esteticista independente": "estética limpeza de pele cílios lash sobrancelha",
    "Depilador(a) independente": "depilação cera",
    "Diarista independente": "faxina faxineira limpeza doméstica",
    "Eletricista em residências e estabelecimentos comerciais independente": "casa residencial elétrica",
    "Motorista (por aplicativo ou não) independente": "uber 99 aplicativo app carro",
    "Motoboy independente": "entregador ifood moto entrega",
    "Confeiteiro(a) independente": "bolo bolos",
    "Doceiro(a) independente": "doces brigadeiro",
    "Marmiteiro(a) independente": "marmita quentinha comida",
    "Salgadeiro(a) independente": "salgados coxinha",
    "Esteticista de animais domésticos independente": "banho e tosa tosador pet",
    "Cuidador(a) de animais (pet sitter) independente": "pet sitter dog walker passeador cachorro",
    "Editor(a) de vídeo independente": "edição youtube",
    "Professor(a) particular independente": "aulas reforço escolar",
    "Lavador(a) e polidor de carro independente": "lava jato lava rápido",
    "Tatuador(a) independente": "tatuagem",
    "Técnico(a) de manutenção de computador independente": "informática notebook pc",
    "Costureiro(a) de roupas sob medida independente": "costura ajuste de roupa",
    "Pedreiro independente": "obra reforma construção",
    "Pintor(a) de parede independente": "pintura casa",
}


def e(s):
    return html.escape(s, quote=True)


def brl(v):
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + s


def nome_limpo(oc):
    n = re.sub(r",?\s*independente\s*$", "", oc.strip(), flags=re.I)
    n = re.sub(r"\s+\(a\)", "(a)", n)
    n = re.sub(r"\s+", " ", n).strip(" ,")
    return n[0].upper() + n[1:]


def slug(oc):
    n = nome_limpo(oc).lower()
    n = re.sub(r"\((a|as|os)\)", "", n)
    n = unicodedata.normalize("NFD", n)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    return n[:80].rstrip("-")


def tipo(o):
    if "aminhoneir" in o["ocupacao"]:
        return "caminhoneiro_iss" if o["iss"] else "caminhoneiro"
    if o["iss"] and o["icms"]:
        return "ambos"
    if o["iss"]:
        return "servico"
    if o["icms"]:
        return "comercio"
    return "locacao"


def das(t):
    inss = INSS_CAMINHONEIRO if t.startswith("caminhoneiro") else INSS
    icms = 1.0 if t in ("comercio", "ambos", "caminhoneiro", "caminhoneiro_iss") else 0.0
    iss = 5.0 if t in ("servico", "ambos", "caminhoneiro_iss") else 0.0
    return inss, icms, iss


TIPO_TXT = {
    "servico": "Prestação de serviço",
    "comercio": "Comércio ou indústria",
    "ambos": "Comércio e serviço",
    "locacao": "Aluguel de bens",
    "caminhoneiro": "Transporte de carga",
    "caminhoneiro_iss": "Transporte de carga",
}

TIPO_CALC = {"servico": "servico", "comercio": "comercio", "ambos": "ambos", "locacao": "locacao",
             "caminhoneiro": "caminhoneiro", "caminhoneiro_iss": "caminhoneiro_iss"}


def chamada_planilha(ref):
    if not PLANILHA["kiwify"]:
        return ""
    return (f'<aside class="oferta"><p><span class="rot">Planilha do MEI {ANO}</span>'
            f'Anote o que entra e sai e a planilha monta o relatório mensal, acompanha o limite, os DAS e '
            f'separa os números da declaração anual. R$ {PLANILHA["preco"]}, pagamento único.</p>'
            f'<div class="oferta-botoes"><a class="btn" href="/planilha-mei/?ref={e(ref)}">Ver a planilha</a></div></aside>')


ICONES = {
    "maquininha": '<svg viewBox="0 0 48 48" fill="none" stroke="#10231B" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><rect x="11" y="4" width="26" height="40" rx="5"/><rect x="16" y="10" width="16" height="10" rx="2"/><path d="M17 27h2M23 27h2M29 27h2M17 33h2M23 33h2M29 33h2M17 39h14"/></svg>',
    "contador": '<svg viewBox="0 0 48 48" fill="none" stroke="#10231B" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M12 6h18l8 8v28H12z"/><path d="M30 6v8h8M18 24h12M18 31h12M18 38h7"/></svg>',
}


def oferta(chave, ref):
    """Bloco de indicação. Some sozinho enquanto a url estiver vazia."""
    o = OFERTAS[chave]
    if not o["url"]:
        return ""
    # link de indicação vai sem parâmetro extra, pra não atrapalhar a atribuição do parceiro
    botoes = f'<a class="btn sol" rel="sponsored noopener" target="_blank" href="{e(o["url"])}" data-oferta="{chave}" data-ref="{e(ref)}">{e(o["botao"])} →</a>'
    if o.get("url2"):
        botoes += f'<a class="btn claro" rel="sponsored noopener" target="_blank" href="{e(o["url2"])}" data-oferta="{chave}-2" data-ref="{e(ref)}">{e(o["botao2"])}</a>'
    itens = "".join(f"<li>{e(i)}</li>" for i in o.get("itens", []))
    return (f'<aside class="parceiro"><div class="dentro"><div class="icone" aria-hidden="true">{ICONES.get(o.get("icone", ""), "")}</div><div>'
            f'<span class="etq">{e(o["rotulo"])}</span><h3>{e(o.get("titulo", ""))}</h3><p>{e(o["texto"])}</p>'
            f'<ul>{itens}</ul><div class="botoes">{botoes}</div>'
            f'<p class="nota">Link de indicação: se você contratar por ele, o Guia do MEI pode receber uma comissão, sem custo a mais pra você.</p>'
            f'</div></div></aside>')


def cabeca(titulo, descricao, caminho, extra_ld=None, robots="index,follow"):
    url = SITE + caminho
    ld = [x for x in (extra_ld or [])]
    lds = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)}</title>
<meta name="description" content="{e(descricao)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Guia do MEI">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(descricao)}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="pt_BR">
<meta property="og:image" content="{SITE}/assets/mei/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE}" crossorigin="anonymous"></script>
<link rel="preload" href="/assets/mei/jakarta-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/mei.css?v=2">
<link rel="icon" href="/assets/mei/favicon.ico" sizes="48x48">
<link rel="icon" href="/assets/mei/marca.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/mei/icone-180.png">
<meta name="theme-color" content="#0A5C3E">
{lds}
</head>
<body>
<a class="pular" href="#conteudo">Pular para o conteúdo</a>
<header class="topo"><div class="w">
  <a class="marca" href="/"><img src="/assets/mei/marca.svg" alt="" width="36" height="36"><span>guia do <b>MEI</b></span></a>
  <nav class="nav">
    <a href="/mei/">Profissões</a>
    <a href="/calculadora-das-mei/">Calculadora do DAS</a>
    <a href="/limite-mei/">Limite</a>
    {'<a class="destaque" href="/planilha-mei/">Planilha do MEI</a>' if PLANILHA["kiwify"] else ''}
  </nav>
</div></header>
"""


RODAPE = f"""<footer class="rodape"><div class="w">
  <div><a class="marca" href="/"><img src="/assets/mei/marca.svg" alt="" width="32" height="32"><span>guia do <b>MEI</b></span></a>
  <p>Informação independente, sem ligação com o governo. Abrir MEI no Portal do Empreendedor é grátis.</p></div>
  <div><a href="/mei/">Profissões</a> · <a href="/calculadora-das-mei/">DAS</a> · <a href="/limite-mei/">Limite</a> · <a href="/privacidade/">Privacidade</a> · <a href="/crm/">Provando o valor do CRM</a></div>
</div></footer>
<script src="/assets/mei.js?v=3" defer></script>
<script src="/assets/analitica.js" defer></script>
</body>
</html>
"""


def migalha(itens):
    partes = []
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": []}
    for i, (nome, caminho) in enumerate(itens, 1):
        ld["itemListElement"].append({"@type": "ListItem", "position": i, "name": nome, "item": SITE + caminho})
        partes.append(f'<a href="{caminho}">{e(nome)}</a>' if i < len(itens) else e(nome))
    return '<nav class="migalha" aria-label="Você está em">' + " › ".join(partes) + "</nav>", ld


def escrever(caminho, conteudo):
    p = RAIZ / caminho.strip("/") / "index.html" if caminho != "/" else RAIZ / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(conteudo, encoding="utf-8", newline="\n")


def tabela_das(t):
    inss, icms, iss = das(t)
    linhas = [f"<tr><td>INSS ({'12' if t.startswith('caminhoneiro') else '5'}% do salário mínimo)</td><td class=num>{brl(inss)}</td></tr>"]
    if icms:
        linhas.append(f"<tr><td>ICMS (vai pro estado)</td><td class=num>{brl(icms)}</td></tr>")
    if iss:
        linhas.append(f"<tr><td>ISS (vai pra prefeitura)</td><td class=num>{brl(iss)}</td></tr>")
    linhas.append(f'<tr class="total"><td>Total por mês</td><td class=num>{brl(inss + icms + iss)}</td></tr>')
    return '<div class="rolagem"><table><thead><tr><th>Parte do DAS</th><th class="num">Valor em 2026</th></tr></thead><tbody>' + "".join(linhas) + "</tbody></table></div>"


def texto_nota(t):
    servico = t in ("servico", "ambos", "caminhoneiro_iss")
    comercio = t in ("comercio", "ambos", "caminhoneiro", "caminhoneiro_iss")
    partes = ["<p>A regra é a mesma pra todo MEI: <strong>vendeu ou prestou serviço pra empresa (CNPJ), a nota é obrigatória</strong>. "
              "Pra cliente pessoa física, o MEI não é obrigado a emitir, mas pode emitir se o cliente pedir.</p>"]
    if servico:
        partes.append("<p>Nota de serviço (NFS-e) o MEI emite de graça no <strong>Emissor Nacional</strong>, pelo site ou pelo aplicativo NFS-e Mobile, com a conta gov.br. Desde setembro de 2023 é o único caminho pra nota de serviço do MEI.</p>")
    if comercio:
        partes.append("<p>Nota de venda de mercadoria (NF-e) sai pelo sistema da Secretaria da Fazenda do seu estado. Cada estado tem o seu, e em vários deles o MEI emite sem certificado digital.</p>")
    if t == "locacao":
        partes.append("<p>Aluguel de bens não é serviço nem venda de mercadoria: não paga ISS nem ICMS. Pra cliente empresa, a forma de documentar varia por prefeitura, então vale confirmar na sua.</p>")
    return "".join(partes)


def pagina_ocupacao(o, s, nome, parecidas):
    t = tipo(o)
    inss, icms, iss = das(t)
    mes = inss + icms + iss
    limite = LIMITE_CAMINHONEIRO if t.startswith("caminhoneiro") else LIMITE
    caminho = f"/mei/{s}/"
    impostos = " e ".join(x for x, ok in (("ISS", iss), ("ICMS", icms)) if ok) or "só INSS"
    titulo = f"MEI {nome}: CNAE {o['cnae']} e DAS de {brl(mes)} em {ANO}"
    if len(titulo) > 70:
        titulo = f"MEI {nome}: CNAE e DAS {ANO}"
    descricao = (f"{nome} pode ser MEI com o CNAE {o['cnae']} ({o['desc']}). Em {ANO} o DAS é {brl(mes)} por mês, "
                 f"com limite de {brl(limite)[:-3]} (sobe em 2027). Veja nota fiscal, obrigações e como abrir de graça.")
    inclui = {(True, True): "o INSS, o ICMS e o ISS", (False, True): "o INSS e o ISS",
              (True, False): "o INSS e o ICMS", (False, False): "só o INSS"}[(bool(icms), bool(iss))]
    mig, ld_mig = migalha([("Início", "/"), ("Profissões", "/mei/"), (nome, caminho)])
    faq = [
        (f"Qual o CNAE do MEI {nome.lower()}?",
         f"O CNAE é {o['cnae']}, {o['desc']}. Na hora de abrir o MEI, a ocupação aparece na lista como \"{o['ocupacao']}\"."),
        (f"Quanto o MEI {nome.lower()} paga por mês em {ANO}?",
         f"{brl(mes)} por mês no DAS, que vence todo dia 20. Esse valor já inclui {inclui}."),
        (f"Quanto o MEI {nome.lower()} pode faturar?",
         (f"Até {brl(limite)[:-3]} por ano. No ano em que abre, o limite é proporcional: {brl(limite / 12)[:-3]} por mês de atividade."
          if t.startswith("caminhoneiro") else
          f"Até R$ 81.000 em {ANO}. Pela Lei Complementar 238/2026, o limite sobe pra R$ 110.000 em 2027 e R$ 140.000 a partir de 2028. "
          "No ano em que abre, é proporcional aos meses de atividade.")),
        ("Pode ter funcionário?", f"Em {ANO}, um empregado. A partir de 2027, a Lei Complementar 238/2026 permite dois, cada um ganhando o salário mínimo ou o piso da categoria."),
    ]
    ld_faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    lista_par = "".join(f'<a href="/mei/{ps}/">{e(pn)}<span>CNAE {e(pc)}</span></a>' for ps, pn, pc in parecidas)

    corpo = f"""<main id="conteudo"><div class="w">
{mig}
<div class="titulo-pag">
  <h1>MEI {e(nome)}: CNAE, DAS e o que precisa saber em {ANO}</h1>
  <p class="entrada">{e(nome)} pode se formalizar como MEI. Aqui está o código certo, quanto paga por mês e o que a lei pede de você, com os valores de {ANO}.</p>
</div>

<dl class="resumo">
  <div><dt>CNAE</dt><dd>{e(o['cnae'])}<small>{e(o['desc'])}</small></dd></div>
  <div><dt>DAS por mês</dt><dd>{brl(mes)}<small>{brl(mes * 12)} no ano</small></dd></div>
  <div><dt>Tipo</dt><dd>{TIPO_TXT[t]}<small>Paga {impostos if impostos != 'só INSS' else 'só o INSS'}</small></dd></div>
  <div><dt>Limite em {ANO}</dt><dd>{brl(limite)[:-3]}<small>{"Caminhoneiro não mudou com a lei nova" if t.startswith("caminhoneiro") else "Sobe pra R$ 110 mil em 2027 e R$ 140 mil em 2028"}</small></dd></div>
</dl>

{oferta("maquininha", s)}

<section>
  <h2>Quanto o MEI {e(nome.lower())} paga de DAS</h2>
  <p>O DAS é a guia única do MEI. Ele junta a contribuição pro INSS com o imposto da sua atividade, num valor fixo que não muda com o quanto você fatura. Vence todo dia 20, referente ao mês anterior.</p>
  {tabela_das(t)}
  <p>Pagando em dia você conta tempo pra aposentadoria por idade e tem direito a auxílio-doença e salário-maternidade, depois das carências do INSS. <a href="/calculadora-das-mei/?tipo={TIPO_CALC[t]}">Simular o DAS, inclusive com atraso</a>.</p>
</section>


<section>
  <h2>Pode ser MEI? As condições</h2>
  <ul class="lista">
    <li><strong>Faturar até {brl(limite)[:-3]} por ano</strong>, somando tudo que entrar pelo CNPJ.{"" if t.startswith("caminhoneiro") else " A " + LEI + " sobe o limite pra R$ 110 mil em 2027 e R$ 140 mil a partir de 2028."}</li>
    <li><strong>Não ser sócio, dono ou administrador de outra empresa.</strong></li>
    <li><strong>Ter no máximo um empregado em {ANO}</strong>, com salário mínimo ou piso da categoria. A partir de 2027 podem ser dois.</li>
    <li><strong>Exercer uma atividade da lista oficial.</strong> {e(nome)} está na lista, então essa parte está resolvida. Dá pra somar até 15 ocupações secundárias.</li>
  </ul>
  <div class="aviso"><p>Servidor público federal na ativa não pode ser MEI. Servidor estadual ou municipal depende do estatuto do seu órgão.</p></div>
</section>

<section>
  <h2>Precisa emitir nota fiscal?</h2>
  {texto_nota(t)}
</section>

<section>
  <h2>O que fazer todo mês e todo ano</h2>
  <ol class="lista">
    <li><strong>Pagar o DAS até o dia 20.</strong> Atrasou, entra multa de 0,33% por dia (até 20%) mais juros.</li>
    <li><strong>Preencher o relatório mensal de receitas</strong> até o dia 20 e guardar junto com as notas de compra e as que você emitiu. Não precisa enviar pra ninguém, mas pode ser cobrado numa fiscalização.</li>
    <li><strong>Entregar a declaração anual (DASN-SIMEI) até 31 de maio</strong>, informando quanto faturou no ano anterior. Atrasou, tem multa.</li>
    <li><strong>Acompanhar o limite de faturamento.</strong> <a href="/limite-mei/">Ver quanto ainda dá pra faturar este ano</a>.</li>
  </ol>
</section>

{chamada_planilha(s)}

{oferta("contabilidade", s)}

<section>
  <h2>Como abrir o MEI {e(nome.lower())}</h2>
  <ol class="lista">
    <li>Tenha uma conta gov.br nível prata ou ouro.</li>
    <li>Entre no Portal do Empreendedor e escolha "Quero ser MEI" e depois "Formalize-se".</li>
    <li>Na ocupação principal, procure por <strong>{e(o['ocupacao'])}</strong>.</li>
    <li>Confirme endereço e declarações. O CNPJ sai na hora.</li>
  </ol>
  <div class="aviso vermelho"><p><strong>Abrir MEI é grátis.</strong> Sites que cobram pra abrir, ou boletos de "taxa do MEI" que chegam pelo correio ou e-mail, não são do governo. O único pagamento obrigatório é o DAS mensal.</p></div>
</section>

<section>
  <h2>Perguntas frequentes</h2>
  {"".join(f'<details><summary>{e(q)}</summary><div><p>{e(a)}</p></div></details>' for q, a in faq)}
</section>

{oferta("maquininha", s + "-fim")}

<section>
  <h2>Ocupações parecidas</h2>
  <div class="grade">{lista_par}</div>
</section>

<p class="fonte">Fonte: lista de ocupações do Anexo XI da Resolução CGSN nº 140/2018 e valores calculados com o salário mínimo de {ANO} (R$ 1.621). Atualizado em {HOJE_BR}. Confira sempre no Portal do Empreendedor antes de abrir ou alterar o seu MEI.</p>
</div></main>
"""
    return cabeca(titulo, descricao, caminho, [ld_mig, ld_faq]) + corpo + RODAPE


def pagina_home(ocs, por_nome):
    dados = [[nome_limpo(o["ocupacao"]), slug(o["ocupacao"]), o["cnae"], APELIDOS.get(o["ocupacao"], "")] for o in ocs]
    pop = "".join(
        f'<a href="/mei/{slug(n)}/">{e(nome_limpo(n))}<span>CNAE {e(por_nome[n]["cnae"])}</span></a>'
        for n in POPULARES if n in por_nome)
    ld_site = {"@context": "https://schema.org", "@type": "WebSite", "name": "Guia do MEI",
               "alternateName": "Guia do MEI por profissão", "url": SITE + "/"}
    titulo = f"Guia do MEI {ANO}: CNAE, DAS e regras por profissão"
    descricao = (f"Ache sua profissão entre as {len(ocs)} ocupações permitidas ao MEI e veja o CNAE, quanto paga de DAS em {ANO}, "
                 "nota fiscal e limite de faturamento. Com calculadoras grátis.")
    linhas = [
        ("Serviço (ISS)", INSS + 5), ("Comércio ou indústria (ICMS)", INSS + 1),
        ("Comércio e serviço", INSS + 6), ("Caminhoneiro", INSS_CAMINHONEIRO + 1),
    ]
    tab = "".join(f"<tr><td>{a}</td><td class=num>{brl(v)}</td></tr>" for a, v in linhas)
    corpo = f"""<main id="conteudo">
<div class="hero"><div class="w">
  <p class="chapeu">Atualizado pra {ANO}</p>
  <h1>Tudo do MEI, explicado pra <em>sua profissão</em></h1>
  <p>Digite o que você faz e veja o CNAE certo, quanto paga por mês, se precisa de nota e como abrir de graça.</p>
  <div class="busca">
    <label for="busca-ocupacao" class="pular">Sua profissão</label>
    <input id="busca-ocupacao" type="search" placeholder="Ex.: manicure, eletricista, confeiteira" autocomplete="off">
    <ul id="busca-resultados" class="resultados"></ul>
  </div>
  <div class="selos"><span>{len(ocs)} profissões</span><span>Valores de {ANO}</span><span>Grátis, sem cadastro</span></div>
</div></div>

<div class="w">
<section>
  <h2>As profissões mais procuradas</h2>
  <div class="grade">{pop}</div>
  <p style="margin-top:14px"><a href="/mei/">Ver as {len(ocs)} ocupações permitidas, de A a Z</a></p>
</section>
{oferta("maquininha", "home")}

<section>
  <h2>Quanto o MEI paga em {ANO}</h2>
  <p>O DAS subiu junto com o salário mínimo, que foi pra R$ 1.621. O INSS é 5% disso ({brl(INSS)}), e o caminhoneiro paga 12% ({brl(INSS_CAMINHONEIRO)}).</p>
  <div class="rolagem"><table><thead><tr><th>Atividade</th><th class="num">DAS por mês</th></tr></thead><tbody>{tab}</tbody></table></div>
  <p><a class="btn" href="/calculadora-das-mei/">Calcular o meu DAS</a></p>
</section>

<section>
  <p class="chapeu" style="color:#8A6400">Lei nova</p>
  <h2>O limite do MEI vai subir pra R$ 140 mil</h2>
  <p>A Lei Complementar 238/2026, sancionada em 21 de outubro, aumenta o limite de faturamento em duas etapas e libera um segundo empregado. Em {ANO} nada muda: vale R$ 81 mil até dezembro.</p>
  <div class="rolagem" style="max-width:560px"><table><thead><tr><th>Ano</th><th class="num">Limite</th><th class="num">Por mês</th></tr></thead><tbody>
  <tr><td>{ANO}</td><td class=num>R$ 81.000</td><td class=num>R$ 6.750</td></tr>
  <tr><td>2027</td><td class=num>R$ 110.000</td><td class=num>R$ 9.166,67</td></tr>
  <tr class="total"><td>2028 em diante</td><td class=num>R$ 140.000</td><td class=num>R$ 11.666,67</td></tr></tbody></table></div>
  <p>A mesma lei perdoa dívidas de DAS em atraso até 13/10/2026, pra quem pagar em dia os seis meses seguintes.</p>
  <p><a class="btn" href="/novo-limite-mei/">Tudo que muda com a lei nova</a> <a class="btn sec" href="/perdao-dividas-mei/">Perdão das dívidas do MEI</a></p>
</section>

<section>
  <h2>Datas que todo MEI precisa lembrar</h2>
  <ul class="lista">
    <li><strong>Dia 20 de todo mês:</strong> vence o DAS do mês anterior.</li>
    <li><strong>31 de maio:</strong> prazo da declaração anual (DASN-SIMEI).</li>
    <li><strong>Janeiro:</strong> o DAS muda de valor quando o salário mínimo muda.</li>
  </ul>
</section>
</div>
</main>
<script>window.OCUPACOES={json.dumps(dados, ensure_ascii=False, separators=(",", ":"))};</script>
"""
    return cabeca(titulo, descricao, "/", [ld_site]) + corpo + RODAPE


def pagina_az(ocs):
    grupos = defaultdict(list)
    for o in ocs:
        n = nome_limpo(o["ocupacao"])
        letra = unicodedata.normalize("NFD", n[0]).upper()[0]
        grupos[letra].append((n, slug(o["ocupacao"])))
    blocos = "".join(
        f"<h3>{l}</h3>" + "".join(f'<a href="/mei/{s}/">{e(n)}</a>' for n, s in sorted(grupos[l]))
        for l in sorted(grupos))
    mig, ld = migalha([("Início", "/"), ("Profissões", "/mei/")])
    corpo = f"""<main id="conteudo"><div class="w">
{mig}
<div class="titulo-pag">
  <h1>As {len(ocs)} ocupações que podem ser MEI em {ANO}</h1>
  <p class="entrada">A lista oficial, de A a Z. Clique na sua pra ver o CNAE, o valor do DAS e as regras.</p>
</div>
<section class="az">{blocos}</section>
<p class="fonte">Fonte: Anexo XI da Resolução CGSN nº 140/2018. Atualizado em {HOJE_BR}.</p>
</div></main>
"""
    return cabeca(f"Lista de ocupações MEI {ANO}: as {len(ocs)} permitidas",
                  f"Lista completa das {len(ocs)} ocupações permitidas ao MEI em {ANO}, com CNAE e valor do DAS de cada uma.",
                  "/mei/", [ld]) + corpo + RODAPE


def pagina_das():
    mig, ld = migalha([("Início", "/"), ("Calculadora do DAS", "/calculadora-das-mei/")])
    corpo = f"""<main id="conteudo"><div class="w">
{mig}
<div class="titulo-pag">
  <h1>Calculadora do DAS MEI {ANO}</h1>
  <p class="entrada">Escolha o tipo de atividade e veja o valor da guia, o total do ano e quanto fica com atraso.</p>
</div>
<form id="calc-das" class="calc" onsubmit="return false">
  <div><label for="tipo">Sua atividade</label>
  <select id="tipo" name="tipo">
    <option value="servico">Serviço (paga ISS)</option>
    <option value="comercio">Comércio ou indústria (paga ICMS)</option>
    <option value="ambos">Comércio e serviço (ICMS e ISS)</option>
    <option value="locacao">Aluguel de bens (só INSS)</option>
    <option value="caminhoneiro">Caminhoneiro</option>
    <option value="caminhoneiro_iss">Caminhoneiro com serviço municipal</option>
  </select></div>
  <div><label for="atraso">Dias de atraso (deixe 0 se está em dia)</label>
  <input id="atraso" name="atraso" type="number" min="0" max="999" value="0" inputmode="numeric"></div>
</form>
<div class="saida"><div class="grande" id="das-mes"></div><p id="das-detalhe"></p><p id="das-atraso"></p></div>
{oferta("maquininha", "calculadora-das")}
<script>(function(){{var t=new URLSearchParams(location.search).get('tipo');var s=document.getElementById('tipo');if(t&&s.querySelector('option[value="'+t+'"]'))s.value=t;}})();</script>
<section>
  <h2>Como o valor é formado</h2>
  <p>O DAS do MEI é fixo: 5% do salário mínimo pro INSS ({brl(INSS)} em {ANO}), mais R$ 1 de ICMS pra quem vende mercadoria e R$ 5 de ISS pra quem presta serviço. O caminhoneiro paga 12% do mínimo de INSS ({brl(INSS_CAMINHONEIRO)}). Não importa se você faturou R$ 500 ou R$ 6.000 no mês: o valor é o mesmo.</p>
  <p>Não sabe se a sua atividade é serviço ou comércio? <a href="/">Procure sua profissão</a> que a página dela mostra.</p>
</section>
{oferta("contabilidade", "calculadora-das")}
<p class="fonte">Valores com o salário mínimo de {ANO} (R$ 1.621). A multa por atraso é de 0,33% ao dia, limitada a 20%, mais juros pela taxa Selic. A guia exata sai no Portal do Empreendedor ou no aplicativo MEI.</p>
</div></main>
"""
    return cabeca(f"Calculadora DAS MEI {ANO}: valor, total no ano e atraso",
                  f"Calcule o DAS do MEI em {ANO}: {brl(INSS + 5)} pra serviço, {brl(INSS + 1)} pra comércio. Veja o total do ano e a multa por atraso.",
                  "/calculadora-das-mei/", [ld]) + corpo + RODAPE


def pagina_limite():
    mig, ld = migalha([("Início", "/"), ("Limite de faturamento", "/limite-mei/")])
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    opts = '<option value="0">Antes do ano escolhido</option>' + "".join(f'<option value="{i}">Em {m} do ano escolhido</option>' for i, m in enumerate(meses, 1))
    corpo = f"""<main id="conteudo"><div class="w">
{mig}
<div class="titulo-pag">
  <h1>Limite do MEI: quanto ainda dá pra faturar</h1>
  <p class="entrada">R$ 81 mil em {ANO}, R$ 110 mil em 2027 e R$ 140 mil a partir de 2028. Escolha o ano, coloque o que já faturou e veja quanto falta.</p>
</div>
<form id="calc-limite" class="calc" onsubmit="return false">
  <div><label for="tipo">Tipo de MEI</label>
  <select id="tipo" name="tipo"><option value="geral">MEI comum</option><option value="caminhoneiro">Caminhoneiro (R$ 251,6 mil)</option></select></div>
  <div><label for="ano">Ano</label>
  <select id="ano" name="ano"><option value="{ANO}">{ANO} (R$ 81 mil)</option><option value="2027">2027 (R$ 110 mil)</option><option value="2028">2028 em diante (R$ 140 mil)</option></select></div>
  <div><label for="abertura">Quando o MEI foi aberto</label><select id="abertura" name="abertura">{opts}</select></div>
  <div><label for="faturado">Quanto já faturou no ano (R$)</label>
  <input id="faturado" name="faturado" inputmode="decimal" placeholder="Ex.: 42.000" value=""></div>
</form>
<div class="saida" id="lim-saida"><div class="grande" id="lim-grande"></div><p id="lim-texto"></p><p id="lim-limite"></p></div>
<section>
  <h2>Como funciona o limite</h2>
  <ul class="lista">
    <li><strong>MEI comum:</strong> R$ 81 mil em {ANO}, R$ 110 mil em 2027 e R$ 140 mil a partir de 2028, pela Lei Complementar 238/2026.</li>
    <li><strong>Caminhoneiro:</strong> R$ 251,6 mil por ano. A lei nova não mudou esse valor.</li>
    <li><strong>No ano de abertura, é proporcional:</strong> R$ 6.750 por mês de atividade em {ANO}, R$ 9.166,67 em 2027 e R$ 11.666,67 a partir de 2028. Mês começado conta inteiro.</li>
    <li><strong>Passou até 20%:</strong> continua MEI até dezembro, paga um DAS complementar sobre o excesso e vira microempresa em janeiro.</li>
    <li><strong>Passou mais de 20%:</strong> o desenquadramento volta pro começo do ano (ou pra data de abertura), com os impostos recalculados.</li>
  </ul>
  <p><a href="/novo-limite-mei/">Veja tudo que muda com a lei nova</a>, inclusive o segundo empregado e o perdão de dívidas.</p>
</section>
{chamada_planilha("limite")}
{oferta("maquininha", "limite")}
{oferta("contabilidade", "limite")}
</div></main>
"""
    return cabeca("Limite do MEI 2026, 2027 e 2028: calculadora de faturamento",
                  "Limite do MEI: R$ 81 mil em 2026, R$ 110 mil em 2027 e R$ 140 mil a partir de 2028 (LC 238/2026). Calcule quanto ainda pode faturar.",
                  "/limite-mei/", [ld]) + corpo + RODAPE


FONTES_LEI = ('<p class="fonte">Fontes: <a href="https://www.planalto.gov.br/ccivil_03/leis/lcp/Lcp238.htm" rel="noopener">texto da Lei Complementar nº 238/2026 no Planalto</a>, '
              '<a href="https://agenciabrasil.ebc.com.br/economia/noticia/2026-10/sancionada-lei-que-perdoa-divida-e-aumenta-limite-de-mei" rel="noopener">Agência Brasil</a> e '
              '<a href="https://fenacon.org.br/noticias/sancionada-lei-que-amplia-limite-de-faturamento-do-mei/" rel="noopener">Fenacon</a>. '
              f'Atualizado em {HOJE_BR}. As regras de detalhe saem em resolução do Comitê Gestor do Simples Nacional: confira no Portal do Empreendedor.</p>')


def pagina_novo_limite():
    mig, ld = migalha([("Início", "/"), ("Novo limite do MEI", "/novo-limite-mei/")])
    faq = [
        ("O limite de R$ 110 mil já vale em 2026?", "Não. Em 2026 o limite continua R$ 81 mil. Os R$ 110 mil valem a partir de 1º de janeiro de 2027, e os R$ 140 mil a partir de 1º de janeiro de 2028."),
        ("Quanto o MEI pode faturar por mês em 2027?", "Na média, R$ 9.166,67. No ano em que o MEI abre, o limite é esse valor vezes os meses de atividade, contando o mês de abertura inteiro."),
        ("O DAS vai aumentar por causa do limite novo?", "A lei não muda a forma do DAS: continua 5% do salário mínimo mais R$ 1 de ICMS e R$ 5 de ISS. O valor muda só quando o salário mínimo muda."),
        ("O MEI pode ter dois funcionários quando?", "A partir de 2027. Cada um recebendo exclusivamente um salário mínimo ou o piso da categoria."),
        ("Quem virou microempresa pode voltar a ser MEI?", "Pela notícia oficial da sanção, empresas do Simples que faturam dentro do novo limite poderão voltar a se enquadrar como MEI, conforme as regras que ainda serão publicadas."),
    ]
    ld_faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    ld_art = {"@context": "https://schema.org", "@type": "Article", "headline": "Novo limite do MEI: R$ 110 mil em 2027 e R$ 140 mil em 2028",
              "datePublished": "2026-10-29", "dateModified": HOJE, "publisher": {"@type": "Organization", "name": "Guia do MEI"}}
    corpo = f"""<main id="conteudo"><div class="w">
{mig}
<div class="titulo-pag">
  <p class="chapeu" style="color:#8A6400">Lei Complementar 238/2026</p>
  <h1>Novo limite do MEI: R$ 110 mil em 2027 e R$ 140 mil em 2028</h1>
  <p class="entrada">A lei foi sancionada em 21 de outubro de 2026. Ela aumenta o limite de faturamento em duas etapas, libera um segundo empregado e perdoa dívidas antigas. Em 2026, o limite continua R$ 81 mil.</p>
</div>
<dl class="resumo">
  <div><dt>Em 2026</dt><dd>R$ 81.000<small>Nada muda até dezembro</small></dd></div>
  <div><dt>Em 2027</dt><dd>R$ 110.000<small>R$ 9.166,67 por mês</small></dd></div>
  <div><dt>2028 em diante</dt><dd>R$ 140.000<small>R$ 11.666,67 por mês</small></dd></div>
  <div><dt>Empregados</dt><dd>Até 2<small>A partir de 2027</small></dd></div>
</dl>
{oferta("maquininha", "novo-limite")}
<section>
  <h2>O que muda, em ordem</h2>
  <ol class="lista">
    <li><strong>Limite de R$ 110 mil em 2027.</strong> Quem abrir o MEI no meio de 2027 tem R$ 9.166,67 por mês de atividade, e mês começado conta inteiro.</li>
    <li><strong>Limite de R$ 140 mil a partir de 2028.</strong> No ano de abertura, R$ 11.666,67 por mês.</li>
    <li><strong>Dois empregados a partir de 2027</strong>, cada um ganhando só o salário mínimo ou o piso da categoria. Hoje é um.</li>
    <li><strong>Perdão das dívidas federais do MEI</strong> constituídas até 13 de outubro de 2026, com multa e juros, pra quem pagar em dia o DAS dos seis meses seguintes. <a href="/perdao-dividas-mei/">Veja quem tem direito</a>.</li>
    <li><strong>Volta pro MEI:</strong> empresas do Simples Nacional que faturam dentro do limite novo poderão voltar a ser MEI, segundo o governo, conforme regras que ainda vão sair.</li>
  </ol>
  <div class="aviso"><p>A própria lei diz que o aumento do limite depende de a perda de arrecadação constar nas leis de orçamento de 2027 a 2029. Na prática, o governo já anunciou as datas, mas vale acompanhar.</p></div>
</section>
<section>
  <h2>O que não muda</h2>
  <ul class="lista">
    <li><strong>O limite de {ANO}:</strong> continua R$ 81 mil. Quem passar disso agora segue a regra antiga: até 20% acima, continua MEI até dezembro e paga DAS complementar; mais que isso, o desenquadramento volta pro começo do ano.</li>
    <li><strong>O DAS:</strong> continua fixo, 5% do salário mínimo mais o ICMS e o ISS da atividade. <a href="/calculadora-das-mei/">Calcular o meu DAS</a>.</li>
    <li><strong>O caminhoneiro:</strong> o limite de R$ 251,6 mil não mudou.</li>
    <li><strong>A declaração anual:</strong> segue até 31 de maio.</li>
  </ul>
  <p><a class="btn" href="/limite-mei/">Calcular quanto ainda dá pra faturar</a></p>
</section>
{chamada_planilha("novo-limite")}
<section>
  <h2>Perguntas frequentes</h2>
  {"".join(f'<details><summary>{e(q)}</summary><div><p>{e(a)}</p></div></details>' for q, a in faq)}
</section>
{FONTES_LEI}
</div></main>
"""
    return cabeca("Novo limite do MEI 2027 e 2028: R$ 110 mil e R$ 140 mil (LC 238/2026)",
                  "Lei sancionada em 21/10/2026: limite do MEI sobe pra R$ 110 mil em 2027 e R$ 140 mil em 2028, com dois empregados e perdão de dívidas. Em 2026 segue R$ 81 mil.",
                  "/novo-limite-mei/", [ld, ld_faq, ld_art]) + corpo + RODAPE


def pagina_perdao():
    mig, ld = migalha([("Início", "/"), ("Novo limite do MEI", "/novo-limite-mei/"), ("Perdão de dívidas", "/perdao-dividas-mei/")])
    faq = [
        ("Preciso pedir o perdão das dívidas?", "Pelo que o governo informou, a remissão é automática pra quem tem dívida só na Receita ou na Dívida Ativa. Quem discute a dívida na Justiça precisa desistir da ação e pedir a baixa."),
        ("Quais dívidas entram?", "Débitos federais do MEI constituídos até 13 de outubro de 2026, inscritos ou não em Dívida Ativa, inclusive parcelados ou em cobrança judicial: contribuição do INSS em atraso, multas, juros e encargos."),
        ("O que eu preciso fazer pra não perder o perdão?", "Pagar em dia o DAS dos seis meses seguintes à entrada em vigor. Atrasou nesse período, o perdão pode ser cancelado."),
        ("Paguei parte da dívida. Recebo de volta?", "Não. O que já foi pago não é devolvido."),
        ("Vale pro ICMS e o ISS em atraso?", "A lei fala em créditos de titularidade da União. ICMS (estado) e ISS (município) que fazem parte do DAS não estão claramente incluídos: confira no Portal do Empreendedor quando a regulamentação sair."),
    ]
    ld_faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    corpo = f"""<main id="conteudo"><div class="w">
{mig}
<div class="titulo-pag">
  <p class="chapeu" style="color:#8A6400">Lei Complementar 238/2026</p>
  <h1>Perdão de dívidas do MEI: quem tem direito e o que fazer</h1>
  <p class="entrada">A lei que aumentou o limite do MEI também perdoa as dívidas federais em atraso até 13 de outubro de 2026, com multa e juros. A condição é pagar o DAS em dia nos seis meses seguintes.</p>
</div>
<dl class="resumo">
  <div><dt>Dívidas até</dt><dd>13/10/2026<small>Constituídas até essa data</small></dd></div>
  <div><dt>Começa em</dt><dd>01/01/2027<small>Segundo o governo</small></dd></div>
  <div><dt>Condição</dt><dd>6 meses<small>de DAS pago em dia</small></dd></div>
  <div><dt>Devolve o que pagou?</dt><dd>Não<small>Só perdoa o que falta</small></dd></div>
</dl>
<section>
  <h2>O que fazer agora</h2>
  <ol class="lista">
    <li><strong>Veja quanto você deve.</strong> No Portal do Empreendedor (Pagamento de contribuição mensal) ou no app MEI aparecem os meses em aberto. A dívida já inscrita aparece no portal Regularize, da PGFN.</li>
    <li><strong>Não comece um parcelamento novo só por causa dessas dívidas</strong> sem conferir antes: o que já foi pago não volta.</li>
    <li><strong>Deixe o DAS de agora em dia.</strong> O perdão exige pagar em dia os seis meses depois da entrada em vigor. Marque o dia 20 no celular.</li>
    <li><strong>Se a dívida está na Justiça</strong>, fale com quem cuida do processo: pra ter a baixa é preciso desistir da ação.</li>
  </ol>
  <p><a class="btn" href="/calculadora-das-mei/">Ver o valor do meu DAS</a></p>
</section>
{oferta("maquininha", "perdao")}
{chamada_planilha("perdao")}
<section>
  <h2>Perguntas frequentes</h2>
  {"".join(f'<details><summary>{e(q)}</summary><div><p>{e(a)}</p></div></details>' for q, a in faq)}
</section>
{FONTES_LEI}
</div></main>
"""
    return cabeca("Perdão de dívidas do MEI 2026: quem tem direito (LC 238/2026)",
                  "A LC 238/2026 perdoa as dívidas federais do MEI até 13/10/2026, com multa e juros, pra quem pagar o DAS em dia por seis meses. Veja o que fazer agora.",
                  "/perdao-dividas-mei/", [ld, ld_faq]) + corpo + RODAPE


def pagina_planilha():
    link = PLANILHA["kiwify"]
    preco = PLANILHA["preco"]
    if link:
        botao = f'<a class="btn" data-checkout href="{e(link)}">Quero a planilha por R$ {preco}</a>'
    else:
        botao = '<span class="btn" style="opacity:.6;cursor:default">Disponível em breve</span>'
    mig, ld = migalha([("Início", "/"), ("Planilha do MEI", "/planilha-mei/")])
    abas = [
        ("Meu MEI", "Nome, CNPJ, quando abriu e o tipo de atividade. Daí saem o valor do seu DAS e o seu limite do ano, já proporcional se abriu este ano."),
        ("Lançamentos", "Um dinheiro por linha: data, o que foi, categoria, valor e se teve nota. As categorias já separam venda, serviço, despesa e o que você tira pra casa."),
        ("Relatório mensal", "O modelo oficial do relatório de receitas brutas, somado sozinho. Escolhe o mês, imprime ou salva em PDF e guarda com as notas."),
        ("Painel do ano", "Quanto entrou, quanto saiu e quanto sobrou em cada mês, o faturamento acumulado e quanto falta pro limite, com aviso aos 80%."),
        ("Declaração anual", "No fim do painel, os números exatos pra DASN-SIMEI: receita total, parte de comércio e parte de serviço."),
        ("DAS", "Os 12 vencimentos do ano com o valor certo. Marca a data do pagamento e vê na hora o que está atrasado."),
        ("Preço", "Quanto cobrar por produto ou serviço, somando material, seu tempo, contas fixas e taxa da maquininha. Mostra quando você está pagando pra trabalhar."),
    ]
    cards = "".join(f'<div class="cartao"><h3 style="margin-top:0">{e(t)}</h3><p style="margin:0">{e(d)}</p></div>' for t, d in abas)
    faq = [
        ("Funciona no celular?", "Funciona no aplicativo do Google Planilhas e no Excel do celular. Pra preencher todo dia, o Google Planilhas é o mais prático."),
        ("Preciso saber Excel?", "Não. Você só preenche as células brancas. Tudo que é cálculo já está pronto e marcado em verde."),
        ("Como recebo?", "Logo depois do pagamento, a Kiwify manda o arquivo pro seu e-mail. Pix cai na hora."),
        ("E se eu não gostar?", "Você tem 7 dias pra pedir o dinheiro de volta pela própria Kiwify, sem precisar explicar."),
        ("Serve pro ano que vem?", "Serve. Quando o salário mínimo mudar, você troca o valor e o ano na aba Meu MEI e o resto se ajusta."),
        ("Substitui o contador?", "Não. Ela organiza o que a lei pede do MEI. Em situação fora do comum, como passar do limite, vale falar com um contador."),
    ]
    ld_faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    relatorio = "".join(f"<tr><td>{a}</td><td class=num>{b}</td></tr>" for a, b in [
        ("VII. Serviços sem nota", "R$ 2.150,00"), ("VIII. Serviços com nota", "R$ 1.800,00"),
        ("IX. Total de serviços", "R$ 3.950,00")])
    corpo = f"""<main id="conteudo">
<div class="hero"><div class="w">
  <p class="chapeu">Planilha do MEI {ANO}</p>
  <h1>Anote o que entra e sai. O resto a planilha faz.</h1>
  <p>Relatório mensal pronto, limite de faturamento, DAS do ano, números da declaração e quanto cobrar. Excel ou Google Planilhas.</p>
  <p style="margin-top:22px">{botao}</p>
  <p style="font-size:15px;color:#D8EFE4">R$ {preco}, pagamento único. Garantia de 7 dias.</p>
</div></div>
<div class="w">
{mig}
<section>
  <h2>O que tem dentro</h2>
  <div class="grade" style="grid-template-columns:repeat(auto-fill,minmax(260px,1fr))">{cards}</div>
</section>
<section>
  <h2>O relatório que o MEI tem que guardar, sem fazer conta</h2>
  <p>Todo mês o MEI precisa preencher o relatório de receitas brutas e guardar junto com as notas. Na planilha ele sai sozinho dos seus lançamentos, separado entre com nota e sem nota, do jeito do modelo oficial.</p>
  <div class="rolagem" style="max-width:560px"><table><thead><tr><th>Exemplo de outubro</th><th class="num">Valor</th></tr></thead><tbody>{relatorio}<tr class="total"><td>X. Total geral do mês</td><td class=num>R$ 3.950,00</td></tr></tbody></table></div>
</section>
<section>
  <h2>E avisa antes de você passar do limite</h2>
  <p>O painel soma o faturamento mês a mês e compara com o seu limite, já proporcional se o MEI abriu este ano. Passou de 80%, a linha fica amarela. Passou do limite, fica vermelha e diz o que acontece.</p>
  <div class="saida" style="max-width:560px"><div class="grande">74% do limite</div><p>Faturado até setembro: R$ 59.940. Ainda dá pra faturar R$ 21.060 no ano.</p></div>
</section>
<section>
  <h2>Perguntas frequentes</h2>
  {"".join(f'<details><summary>{e(q)}</summary><div><p>{e(a)}</p></div></details>' for q, a in faq)}
</section>
<section style="text-align:center">
  <p style="margin:0 auto 14px">{botao}</p>
  <p class="fonte" style="margin:0 auto">Pagamento pela Kiwify, com Pix ou cartão. A planilha organiza as obrigações do MEI e não substitui um contador.</p>
</section>
</div>
</main>
<script>(function(){{var r=new URLSearchParams(location.search).get('ref');if(!r)return;document.querySelectorAll('a[data-checkout]').forEach(function(a){{a.href+=(a.href.indexOf('?')<0?'?':'&')+'utm_source=guiadomei&utm_content='+encodeURIComponent(r)}})}})();</script>
"""
    return cabeca(f"Planilha do MEI {ANO}: relatório mensal, limite e DAS",
                  "Planilha do MEI pra Excel e Google Planilhas: relatório mensal de receitas pronto, limite de faturamento, DAS do ano, números da declaração anual e quanto cobrar.",
                  "/planilha-mei/", [ld, ld_faq], robots="index,follow" if link else "noindex,follow") + corpo + RODAPE


def sitemap(urls):
    linhas = "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{HOJE}</lastmod></url>\n" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{linhas}</urlset>\n'


def main():
    ocs = json.load(open(RAIZ / "_mei" / "ocupacoes.json", encoding="utf-8"))
    # mesma ocupação repetida na fonte: fica a primeira
    vistos, unicas = set(), []
    for o in ocs:
        if o["ocupacao"] not in vistos:
            vistos.add(o["ocupacao"])
            unicas.append(o)
    ocs = sorted(unicas, key=lambda o: slug(o["ocupacao"]))
    por_nome = {o["ocupacao"]: o for o in ocs}
    slugs = [slug(o["ocupacao"]) for o in ocs]
    assert len(set(slugs)) == len(slugs), "slug repetido"

    por_cnae, por_grupo = defaultdict(list), defaultdict(list)
    for o in ocs:
        por_cnae[o["cnae"]].append(o)
        por_grupo[o["cnae"][:2]].append(o)

    urls = ["/", "/mei/", "/calculadora-das-mei/", "/limite-mei/"]
    for o in ocs:
        s = slug(o["ocupacao"])
        cands = [x for x in por_cnae[o["cnae"]] if x is not o] + [x for x in por_grupo[o["cnae"][:2]] if x is not o and x["cnae"] != o["cnae"]]
        parecidas = [(slug(x["ocupacao"]), nome_limpo(x["ocupacao"]), x["cnae"]) for x in cands[:6]]
        escrever(f"/mei/{s}/", pagina_ocupacao(o, s, nome_limpo(o["ocupacao"]), parecidas))
        urls.append(f"/mei/{s}/")

    escrever("/", pagina_home(ocs, por_nome))
    escrever("/mei/", pagina_az(ocs))
    escrever("/calculadora-das-mei/", pagina_das())
    escrever("/limite-mei/", pagina_limite())
    escrever("/planilha-mei/", pagina_planilha())
    escrever("/novo-limite-mei/", pagina_novo_limite())
    escrever("/perdao-dividas-mei/", pagina_perdao())
    urls[4:4] = ["/novo-limite-mei/", "/perdao-dividas-mei/"]
    if PLANILHA["kiwify"]:
        urls.append("/planilha-mei/")

    urls += ["/crm/", "/crm/calculadora/", "/crm/dimensionamento/", "/crm/blog/", "/crm/blog/como-medir-crm/",
             "/crm/blog/metricas-de-crm/", "/crm/blog/o-que-e-incrementalidade/", "/privacidade/"]
    (RAIZ / "sitemap.xml").write_text(sitemap(urls), encoding="utf-8", newline="\n")
    print(f"{len(ocs)} ocupações, {len(urls)} urls no sitemap")


if __name__ == "__main__":
    main()
