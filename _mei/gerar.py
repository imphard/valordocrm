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
  <div><a href="/mei/">Profissões</a> · <a href="/calculadora-das-mei/">DAS</a> · <a href="/limite-mei/">Limite</a> · <a href="/como-abrir-mei/">Abrir MEI</a> · <a href="/boleto-das-mei/">Boleto do DAS</a> · <a href="/declaracao-anual-mei/">Declaração anual</a> · <a href="/nota-fiscal-mei/">Nota fiscal</a> · <a href="/privacidade/">Privacidade</a> · <a href="/crm/">Provando o valor do CRM</a></div>
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
    guias_home = "".join(f'<a href="{g["url"]}">{e(g["curto"])}<span>{e(g["chapeu"])}</span></a>' for g in guias())
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
  <h2>Guias do MEI, passo a passo</h2>
  <div class="grade">{guias_home}</div>
</section>

<section>
  <h2>Datas que todo MEI precisa lembrar</h2>
  <ul class="lista">
    <li><strong>Dia 20 de todo mês:</strong> vence o DAS do mês anterior. <a href="/boleto-das-mei/">Como emitir o boleto</a>.</li>
    <li><strong>31 de maio:</strong> prazo da declaração anual (DASN-SIMEI). <a href="/declaracao-anual-mei/">Como fazer</a>.</li>
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
    <li><strong>Dois empregados a partir de 2027</strong>, cada um ganhando só o salário mínimo ou o piso da categoria. Hoje é um. <a href="/mei-pode-ter-funcionario/">Veja quanto custa</a>.</li>
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
  <p>Dívida de depois de 13/10/2026, ou de ICMS e ISS? <a href="/das-atrasado-mei/">Veja como pagar ou parcelar</a>.</p>
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


PORTAL = '<a href="https://www.gov.br/empresas-e-negocios/pt-br/empreendedor" rel="noopener">Portal do Empreendedor</a>'
PGMEI = '<a href="https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/Identificacao" rel="noopener">PGMEI</a>'


def guias():
    """Os guias dos temas que mais se procuram sobre MEI. Cada um vira uma página."""
    sal = MINIMO
    fgts, patronal, desconto = round(sal * 0.08, 2), round(sal * 0.03, 2), round(sal * 0.075, 2)
    # 13º e férias com um terço, guardados todo mês, com FGTS e INSS patronal em cima
    reserva = round((sal / 12 + sal * 4 / 3 / 12) * 1.11, 2)
    custo = round(sal + fgts + patronal + reserva, 2)
    return [
        {
            "url": "/declaracao-anual-mei/", "curto": "Declaração anual",
            "title": f"Declaração anual do MEI (DASN-SIMEI): prazo, multa e como fazer",
            "desc": "A declaração anual do MEI vai até 31 de maio. Veja quem precisa entregar, o que informar, como fazer pelo celular e quanto é a multa por atraso.",
            "chapeu": "DASN-SIMEI", "h1": "Declaração anual do MEI: prazo, multa e passo a passo",
            "entrada": "Todo ano, até 31 de maio, o MEI informa quanto faturou no ano anterior. Leva cinco minutos e é obrigatória mesmo pra quem não faturou nada.",
            "resumo": [("Prazo", "31 de maio", "Sobre o ano anterior"), ("Custo", "Grátis", "Feita pela internet"),
                       ("Sem faturar?", "Entrega igual", "Informa zero"), ("Atrasou", "R$ 50", "Multa mínima, R$ 25 se entregar sozinho")],
            "secoes": [
                f"""<h2>Quem precisa entregar</h2>
  <p>Todo MEI que teve CNPJ ativo em qualquer parte do ano anterior. Abriu em novembro? Entrega. Não vendeu nada? Entrega informando zero. Fechou o MEI? Entrega a declaração de extinção, com prazo próprio (<a href="/como-dar-baixa-mei/">veja como dar baixa</a>).</p>
  <p>A declaração de {ANO + 1} é sobre o que você faturou em {ANO}. Ela abre em janeiro e vai até 31 de maio de {ANO + 1}.</p>""",
                f"""<h2>O que você vai informar</h2>
  <ol class="lista">
    <li><strong>Receita bruta total do ano:</strong> tudo que entrou com as vendas e serviços, com nota ou sem nota. É o que entrou, não o lucro.</li>
    <li><strong>Quanto disso foi comércio ou indústria:</strong> venda de mercadoria, comida, produto que você fabrica.</li>
    <li><strong>Quanto foi serviço.</strong> As duas partes somadas dão o total.</li>
    <li><strong>Se teve empregado</strong> no ano.</li>
  </ol>
  <p>Quem guarda o relatório mensal de receitas tem a conta pronta: é só somar os doze meses.</p>""",
                f"""<h2>Passo a passo</h2>
  <ol class="lista">
    <li>Entre no {PORTAL} e escolha <strong>Já sou MEI</strong> e depois <strong>Declaração anual de faturamento</strong>. Pelo celular, o aplicativo MEI faz o mesmo.</li>
    <li>Digite o CNPJ e escolha o ano.</li>
    <li>Preencha a receita de comércio, a de serviço e se teve empregado.</li>
    <li>Confira e transmita. Salve o recibo em PDF.</li>
    <li>Se aparecer DAS em aberto no fim, ele já pode ser emitido ali mesmo.</li>
  </ol>
  <p>Errou algum valor? Dá pra fazer uma declaração retificadora no mesmo lugar, sem multa, enquanto estiver no prazo.</p>""",
                f"""<h2>Multa por atraso</h2>
  <p>É 2% ao mês sobre os impostos declarados, limitada a 20%, com mínimo de R$ 50. Como o imposto do MEI é baixo, quase sempre a multa fica nos R$ 50. Entregando atrasada por conta própria, antes de a Receita cobrar, ela cai pela metade: R$ 25.</p>
  <p>Mais caro que a multa é não entregar. Sem a declaração, o MEI não consegue parcelar dívidas e pode ter o CNPJ cancelado.</p>
  <div class="aviso"><p>Faturou mais que o limite no ano? A declaração vai mostrar. Até 20% acima, você paga um DAS complementar sobre o excesso. <a href="/limite-mei/">Veja as regras do limite</a>.</p></div>""",
            ],
            "faq": [
                ("Qual o prazo da declaração anual do MEI?", "31 de maio de cada ano, sobre o faturamento do ano anterior."),
                ("MEI que não faturou precisa declarar?", "Precisa. Informa receita zero e entrega normalmente."),
                ("Quanto é a multa por atraso da DASN-SIMEI?", "2% ao mês sobre os impostos declarados, até 20%, com mínimo de R$ 50. Entregando por conta própria, antes de a Receita cobrar, cai pela metade."),
                ("Informo o faturamento ou o lucro?", "O faturamento: tudo que entrou com vendas e serviços, antes de tirar as despesas."),
                ("Dá pra corrigir depois de enviar?", "Dá. É só fazer uma declaração retificadora no mesmo lugar."),
            ],
            "fontes": [("Portal do Empreendedor", "https://www.gov.br/empresas-e-negocios/pt-br/empreendedor"),
                       ("DASN-SIMEI no Portal do Simples Nacional", "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/dasnsimei.app/Identificacao")],
            "leia": ["/das-atrasado-mei/", "/limite-mei/", "/nota-fiscal-mei/"],
        },
        {
            "url": "/como-abrir-mei/", "curto": "Como abrir MEI",
            "title": f"Como abrir MEI em {ANO}: passo a passo grátis pelo gov.br",
            "desc": f"Abrir MEI é grátis e leva 15 minutos. Veja o que precisa, quem pode, o passo a passo no gov.br e o que fazer depois de receber o CNPJ em {ANO}.",
            "chapeu": "Passo a passo", "h1": f"Como abrir MEI em {ANO}, de graça e pelo celular",
            "entrada": "O CNPJ sai na hora, sem contador e sem pagar nada. Você só precisa de uma conta gov.br prata ou ouro e de saber qual é a sua atividade.",
            "resumo": [("Custo", "R$ 0", "Desconfie de quem cobra"), ("Tempo", "15 min", "CNPJ sai na hora"),
                       ("Precisa de", "gov.br", "Nível prata ou ouro"), ("Paga por mês", brl(INSS + 5), "Serviço, em " + str(ANO))],
            "secoes": [
                f"""<h2>Antes de começar: você pode ser MEI?</h2>
  <ul class="lista">
    <li><strong>A sua atividade está na lista.</strong> São 470 ocupações permitidas. <a href="/">Procure a sua</a> e anote o nome exato.</li>
    <li><strong>Você vai faturar até o limite:</strong> R$ 81 mil em {ANO}, R$ 110 mil em 2027 e R$ 140 mil a partir de 2028.</li>
    <li><strong>Não é sócio, administrador ou dono</strong> de outra empresa.</li>
    <li><strong>Terá no máximo um empregado</strong> (dois a partir de 2027).</li>
    <li><strong>Servidor público:</strong> o federal em atividade não pode. Estadual e municipal depende do estatuto do seu cargo.</li>
  </ul>""",
                f"""<h2>Passo a passo</h2>
  <ol class="lista">
    <li><strong>Deixe a conta gov.br no nível prata ou ouro.</strong> No aplicativo gov.br, faça o reconhecimento facial ou entre pelo banco. O nível bronze não abre MEI.</li>
    <li>Entre no {PORTAL} e escolha <strong>Quero ser MEI</strong> e depois <strong>Formalize-se</strong>.</li>
    <li>Confirme os dados pessoais, o telefone e o e-mail.</li>
    <li><strong>Escolha a ocupação principal</strong> e, se quiser, até 15 secundárias. A principal é a que você mais faz.</li>
    <li><strong>Diga como você trabalha:</strong> em ponto fixo, em casa, na casa do cliente, pela internet, de porta em porta ou em ponto móvel.</li>
    <li>Informe o endereço, aceite as declarações e confirme.</li>
    <li>Pronto: o <strong>CNPJ e o certificado (CCMEI)</strong> saem na hora. Salve o PDF.</li>
  </ol>
  <div class="aviso"><p>Abrir MEI é grátis. Sites que cobram pra abrir, ou boletos que chegam pelo correio cobrando taxa de registro, não são do governo.</p></div>""",
                f"""<h2>Depois de abrir</h2>
  <ol class="lista">
    <li><strong>O primeiro DAS</strong> vence no dia 20 do mês seguinte à abertura. <a href="/boleto-das-mei/">Veja como emitir</a>.</li>
    <li><strong>Alvará:</strong> atividade de baixo risco é dispensada. Se você atende num ponto fixo, confirme na prefeitura.</li>
    <li><strong>Nota fiscal:</strong> pra serviço, você já pode emitir pelo emissor nacional. <a href="/nota-fiscal-mei/">Veja como</a>.</li>
    <li><strong>Separe o dinheiro:</strong> abra uma conta no CNPJ e receba os clientes nela. Fica fácil saber quanto faturou.</li>
    <li><strong>Anote o que entra todo mês.</strong> A lei pede o relatório mensal de receitas, e a declaração anual sai dele.</li>
  </ol>""",
            ],
            "faq": [
                ("Quanto custa abrir MEI?", "Nada. A abertura no Portal do Empreendedor é gratuita. Depois, o MEI paga só o DAS mensal."),
                ("Quanto tempo demora pra sair o CNPJ?", "Sai na hora, assim que você confirma o cadastro."),
                ("Por que o gov.br pede nível prata ou ouro?", "É a exigência pra formalizar. Dá pra subir de nível pelo reconhecimento facial no aplicativo gov.br ou entrando pelo seu banco."),
                ("Posso abrir MEI trabalhando de carteira assinada?", "Pode. Só fique atento se um dia for demitido: com MEI ativo, o seguro-desemprego pode ser negado se o MEI der renda suficiente pra você se manter."),
                ("Posso abrir MEI em casa?", "Pode. Na hora do cadastro, escolha a forma de atuação e use o endereço de casa."),
            ],
            "fontes": [("Portal do Empreendedor", "https://www.gov.br/empresas-e-negocios/pt-br/empreendedor"),
                       ("Lei Complementar 123/2006", "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm")],
            "leia": ["/boleto-das-mei/", "/nota-fiscal-mei/", "/mei-pode-ter-funcionario/"],
        },
        {
            "url": "/nota-fiscal-mei/", "curto": "Nota fiscal",
            "title": f"Nota fiscal do MEI em {ANO}: quando é obrigatória e como emitir",
            "desc": "Como o MEI emite nota fiscal de serviço pelo emissor nacional e de produto pela Sefaz, quando é obrigatória e o que muda em 2027.",
            "chapeu": "NFS-e e NF-e", "h1": "Nota fiscal do MEI: quando emitir e como fazer",
            "entrada": f"Em {ANO}, a nota é obrigatória quando o cliente é empresa. A partir de 2027, pela lei da reforma tributária, passa a ser obrigatória em toda venda, também pra pessoa física.",
            "resumo": [("Cliente empresa", "Obrigatória", "Já hoje"), ("Cliente pessoa", "Opcional", f"Até dezembro de {ANO}"),
                       ("A partir de 2027", "Sempre", "Em toda venda"), ("Custo", "Grátis", "Emissor do governo")],
            "secoes": [
                f"""<h2>Quando a nota é obrigatória</h2>
  <ul class="lista">
    <li><strong>Venda ou serviço pra empresa (CNPJ):</strong> obrigatória.</li>
    <li><strong>Pra pessoa física, em {ANO}:</strong> a lei dispensa. Se o cliente pedir, emita.</li>
    <li><strong>A partir de 1º de janeiro de 2027:</strong> a Lei Complementar 214/2025 (reforma tributária) passa a exigir nota em todas as vendas e serviços do MEI, pra qualquer cliente. Vale começar a se acostumar agora.</li>
  </ul>""",
                f"""<h2>Nota de serviço (NFS-e), passo a passo</h2>
  <p>Desde setembro de 2023 o MEI emite nota de serviço pelo <a href="https://www.nfse.gov.br/EmissorNacional" rel="noopener">Emissor Nacional</a>, no computador, ou pelo aplicativo NFS-e Mobile. É grátis.</p>
  <ol class="lista">
    <li>Entre com a conta gov.br e faça o primeiro acesso com o CNPJ.</li>
    <li>Clique em <strong>Emitir NFS-e</strong> e informe o CPF ou CNPJ do cliente.</li>
    <li>Escolha o código do serviço (o sistema busca pelo nome) e descreva o que foi feito.</li>
    <li>Coloque o valor e confirme. O ISS não é cobrado na nota: ele já vai no seu DAS.</li>
    <li>Baixe o PDF e mande pro cliente.</li>
  </ol>
  <p>Aparecerem campos de IBS e CBS? Em {ANO} o MEI pode deixar em branco. Eles só passam a ser exigidos do MEI em 2027.</p>""",
                f"""<h2>Nota de produto (NF-e)</h2>
  <p>Quem vende mercadoria emite a nota pela secretaria da Fazenda do estado. Precisa de inscrição estadual, que em muitos estados já sai com o MEI. Alguns estados têm emissor gratuito no site da Sefaz; outros pedem um programa e certificado digital. Procure por "emissor de nota fiscal MEI" mais o nome do seu estado no site da Sefaz.</p>""",
                f"""<h2>O que guardar</h2>
  <p>Guarde as notas que você emite, as notas das compras de mercadoria e o relatório mensal de receitas. Não precisa mandar pra ninguém, mas a fiscalização pode pedir por cinco anos.</p>""",
            ],
            "faq": [
                ("MEI é obrigado a emitir nota fiscal pra pessoa física?", f"Em {ANO}, não, a menos que o cliente peça. A partir de 1º de janeiro de 2027, pela LC 214/2025, passa a ser obrigatório em toda venda e serviço."),
                ("Onde o MEI emite nota de serviço?", "No Emissor Nacional (nfse.gov.br) ou no aplicativo NFS-e Mobile, de graça, entrando com a conta gov.br."),
                ("O MEI paga imposto em cada nota?", "Não. O imposto do MEI é o valor fixo do DAS, pago todo mês. A nota não gera imposto a mais."),
                ("Preciso preencher IBS e CBS na nota?", f"Não em {ANO}. Esses campos só passam a ser exigidos do MEI em 2027."),
                ("Esqueci de emitir. E agora?", "Emita assim que puder. No emissor nacional você informa a data em que o serviço foi prestado, que é a competência da nota."),
            ],
            "fontes": [("Emissor Nacional da NFS-e", "https://www.nfse.gov.br/EmissorNacional"),
                       ("Lei Complementar 214/2025", "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp214.htm"),
                       ("Lei Complementar 123/2006, art. 26", "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm")],
            "leia": ["/declaracao-anual-mei/", "/como-abrir-mei/", "/boleto-das-mei/"],
        },
        {
            "url": "/das-atrasado-mei/", "curto": "DAS atrasado",
            "title": f"DAS do MEI atrasado: como regularizar e parcelar em {ANO}",
            "desc": "MEI com DAS atrasado: quanto fica a multa, como pagar, como parcelar em até 60 vezes e o perdão das dívidas da LC 238/2026.",
            "chapeu": "Regularizar", "h1": "DAS do MEI atrasado: como pagar, parcelar ou entrar no perdão",
            "entrada": "Atrasar o DAS custa multa e juros, mas o risco maior é perder os benefícios do INSS. A lei nova ainda perdoa as dívidas federais até 13/10/2026. Veja o que fazer no seu caso.",
            "resumo": [("Multa", "0,33% ao dia", "No máximo 20%"), ("Juros", "Selic", "Calculados na guia"),
                       ("Parcelamento", "Até 60x", "Parcela mínima de R$ 50"), ("Perdão", "Até 13/10/2026", "LC 238/2026")],
            "secoes": [
                f"""<h2>O que acontece quando o DAS atrasa</h2>
  <ul class="lista">
    <li><strong>Multa e juros:</strong> 0,33% por dia, no máximo 20%, mais juros pela taxa Selic. <a href="/calculadora-das-mei/">Calcule a multa</a>.</li>
    <li><strong>Benefícios do INSS:</strong> o mês sem pagar não conta, e depois de um tempo sem pagar você perde a cobertura. <a href="/beneficios-inss-mei/">Veja os benefícios</a>.</li>
    <li><strong>Dívida ativa:</strong> a dívida vai pra Procuradoria da Fazenda, pode ir pro seu CPF e dificultar crédito.</li>
    <li><strong>CNPJ:</strong> MEI que fica muito tempo sem pagar e sem declarar pode ter o registro cancelado.</li>
  </ul>""",
                f"""<h2>Antes de pagar: veja se entra no perdão</h2>
  <p>A Lei Complementar 238/2026 perdoa as dívidas federais do MEI constituídas até 13 de outubro de 2026, com multa e juros, pra quem pagar em dia o DAS dos seis meses seguintes. O que já foi pago não volta. Então, se a sua dívida é dessa época, <a href="/perdao-dividas-mei/">leia as regras do perdão</a> antes de parcelar.</p>
  <p>ICMS e ISS que fazem parte do DAS são do estado e do município e podem ficar de fora do perdão.</p>""",
                f"""<h2>Como regularizar, passo a passo</h2>
  <ol class="lista">
    <li><strong>Veja o que está em aberto.</strong> No {PGMEI}, com o CNPJ, escolha o ano e veja os meses sem pagamento. Dívida já inscrita aparece no <a href="https://www.regularize.pgfn.gov.br" rel="noopener">Regularize</a>, da PGFN.</li>
    <li><strong>Entregue as declarações anuais que faltam.</strong> Sem elas, o parcelamento não abre. <a href="/declaracao-anual-mei/">Veja como</a>.</li>
    <li><strong>Pague à vista</strong> gerando a guia atualizada no próprio dia. Guia antiga, emitida em outra data, sai com valor errado.</li>
    <li><strong>Ou parcele:</strong> no Portal do Simples Nacional, em Parcelamento MEI, em até 60 vezes, com parcela mínima de R$ 50. Entram os anos cuja declaração já foi entregue.</li>
    <li><strong>Dívida ativa:</strong> negocie no Regularize. A PGFN abre de tempos em tempos transações com desconto em multa e juros.</li>
  </ol>
  <div class="aviso"><p>Depois de regularizar, o que mais protege é o DAS do mês em dia. Débito automático evita esquecer. <a href="/boleto-das-mei/">Veja como ligar</a>.</p></div>""",
            ],
            "faq": [
                ("Quanto é a multa do DAS atrasado?", "0,33% por dia de atraso, no máximo 20% do valor, mais juros pela taxa Selic."),
                ("Dá pra parcelar o DAS do MEI?", "Dá, em até 60 vezes com parcela mínima de R$ 50, no Portal do Simples Nacional. Antes é preciso entregar as declarações anuais dos anos em atraso."),
                ("Minha dívida do MEI vai ser perdoada?", "As dívidas federais constituídas até 13/10/2026 entram no perdão da LC 238/2026, com a condição de pagar o DAS em dia por seis meses."),
                ("Dívida do MEI vai pro meu CPF?", "O MEI e a pessoa são a mesma pessoa pra cobrança. Dívida inscrita em dívida ativa pode atingir o seu CPF."),
                ("Posso dar baixa no MEI com dívida?", "Pode, mas a dívida continua existindo e precisa ser paga."),
            ],
            "fontes": [("PGMEI, Receita Federal", "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/Identificacao"),
                       ("Regularize, PGFN", "https://www.regularize.pgfn.gov.br"),
                       ("Lei Complementar 238/2026", "https://www.planalto.gov.br/ccivil_03/leis/lcp/Lcp238.htm")],
            "leia": ["/perdao-dividas-mei/", "/boleto-das-mei/", "/beneficios-inss-mei/"],
        },
        {
            "url": "/mei-pode-ter-funcionario/", "curto": "Funcionário",
            "title": f"MEI pode ter funcionário? Um em {ANO}, dois a partir de 2027",
            "desc": f"O MEI pode ter um empregado em {ANO} e dois a partir de 2027 (LC 238/2026). Veja o salário permitido, quanto custa por mês e como registrar no eSocial.",
            "chapeu": "Empregado", "h1": "MEI pode ter funcionário? Pode, e a partir de 2027 são dois",
            "entrada": f"Em {ANO} o MEI pode registrar um empregado, que ganha o salário mínimo ou o piso da categoria. A Lei Complementar 238/2026 libera o segundo a partir de 2027.",
            "resumo": [(f"Em {ANO}", "1 empregado", "Mínimo ou piso"), ("A partir de 2027", "2 empregados", "LC 238/2026"),
                       ("Encargos", "11%", "8% FGTS + 3% INSS"), ("Custo real", brl(custo), "Por mês, com 13º e férias")],
            "secoes": [
                f"""<h2>As regras</h2>
  <ul class="lista">
    <li><strong>Quantos:</strong> um empregado em {ANO}, dois a partir de 1º de janeiro de 2027.</li>
    <li><strong>Quanto pode pagar:</strong> exclusivamente o salário mínimo ({brl(sal)} em {ANO}) ou o piso da categoria, se houver. Pagar mais que isso desenquadra o MEI.</li>
    <li><strong>Registro:</strong> carteira de trabalho digital e eSocial, como qualquer empregador.</li>
  </ul>""",
                f"""<h2>Quanto custa um empregado com salário mínimo</h2>
  <div class="rolagem" style="max-width:560px"><table><thead><tr><th>Item</th><th class="num">Por mês</th></tr></thead><tbody>
  <tr><td>Salário</td><td class=num>{brl(sal)}</td></tr>
  <tr><td>FGTS (8%)</td><td class=num>{brl(fgts)}</td></tr>
  <tr><td>INSS do patrão (3%)</td><td class=num>{brl(patronal)}</td></tr>
  <tr><td>Reserva pro 13º e férias com 1/3</td><td class=num>{brl(reserva)}</td></tr>
  <tr class="total"><td>Custo real por mês</td><td class=num>{brl(custo)}</td></tr></tbody></table></div>
  <p>O INSS do empregado (7,5%, {brl(desconto)}) é descontado do salário dele e você só repassa. Vale-transporte, se houver, pode descontar até 6% do salário.</p>""",
                f"""<h2>Como registrar, passo a passo</h2>
  <ol class="lista">
    <li>Peça os documentos e faça o exame admissional.</li>
    <li>Entre no <a href="https://www.gov.br/esocial" rel="noopener">eSocial</a> com a conta gov.br, no módulo simplificado do MEI, e cadastre o empregado antes do primeiro dia de trabalho.</li>
    <li>Todo mês, feche a folha no eSocial. Ele gera uma guia única (DAE) com FGTS, INSS do patrão e INSS do empregado.</li>
    <li>Pague a guia até o dia 20 do mês seguinte. É separada do DAS do MEI.</li>
  </ol>
  <div class="aviso"><p>O segundo empregado só pode ser registrado a partir de 2027. Contratar antes, ou pagar acima do mínimo ou do piso, tira você do MEI.</p></div>""",
            ],
            "faq": [
                ("Quantos funcionários o MEI pode ter?", f"Um em {ANO}. A partir de 1º de janeiro de 2027, dois, pela Lei Complementar 238/2026."),
                ("Quanto o MEI pode pagar ao funcionário?", f"Só o salário mínimo ({brl(sal)} em {ANO}) ou o piso da categoria."),
                ("Quanto custa um funcionário pro MEI?", f"Com salário mínimo, uns {brl(custo)} por mês, contando FGTS, INSS do patrão e a reserva pro 13º e as férias."),
                ("O MEI paga o INSS do funcionário?", "Paga 3% de INSS patronal e repassa os 7,5% descontados do salário do empregado, na mesma guia do eSocial."),
                ("Sócio ou parente pode ser o empregado?", "Parente pode, registrado como qualquer empregado. Sócio não existe no MEI."),
            ],
            "fontes": [("Lei Complementar 238/2026", "https://www.planalto.gov.br/ccivil_03/leis/lcp/Lcp238.htm"),
                       ("eSocial", "https://www.gov.br/esocial")],
            "leia": ["/novo-limite-mei/", "/limite-mei/", "/beneficios-inss-mei/"],
        },
        {
            "url": "/beneficios-inss-mei/", "curto": "Benefícios do INSS",
            "title": "Benefícios do INSS pro MEI: aposentadoria, auxílio e maternidade",
            "desc": "O que o DAS do MEI garante no INSS: aposentadoria por idade, auxílio por incapacidade, salário-maternidade e pensão. Veja as carências e o que não cobre.",
            "chapeu": "Previdência", "h1": "Benefícios do INSS pro MEI: o que o DAS garante",
            "entrada": f"Dos {brl(INSS + 5)} do DAS, {brl(INSS)} vão pro INSS. Isso dá direito a aposentadoria, auxílio quando fica doente e salário-maternidade, sempre no valor de um salário mínimo.",
            "resumo": [("Valor do benefício", brl(sal), "Um salário mínimo"), ("Auxílio doença", "12 meses", "De contribuição"),
                       ("Maternidade", "120 dias", "Sem carência mínima"), ("Aposentadoria", "Por idade", "62 mulheres, 65 homens")],
            "secoes": [
                f"""<h2>O que o MEI tem</h2>
  <ul class="lista">
    <li><strong>Aposentadoria por idade:</strong> mulheres aos 62 anos com 15 anos de contribuição; homens aos 65 com 20 anos (15 pra quem já contribuía antes de 13/11/2019).</li>
    <li><strong>Auxílio por incapacidade temporária</strong> (o antigo auxílio-doença): depois de 12 meses de contribuição. Acidente dispensa a carência.</li>
    <li><strong>Aposentadoria por incapacidade permanente:</strong> também com 12 meses, depois de perícia.</li>
    <li><strong>Salário-maternidade:</strong> 120 dias, por parto ou adoção. Desde a decisão do STF de 2024, não exige número mínimo de contribuições: basta estar com a cobertura em dia.</li>
    <li><strong>Pensão por morte e auxílio-reclusão</strong> pra família.</li>
  </ul>""",
                f"""<h2>O que o MEI não tem</h2>
  <ul class="lista">
    <li><strong>Aposentadoria por tempo de contribuição</strong> e <strong>benefício acima do mínimo:</strong> o DAS cobre só o valor do salário mínimo.</li>
    <li>Quer contar esse tempo pra outra aposentadoria? Dá pra complementar com mais 15% do salário mínimo por mês, numa guia própria (GPS, código 1910).</li>
    <li><strong>Seguro-desemprego:</strong> o MEI não tem. E quem tem MEI com renda pode perder o seguro de um emprego anterior.</li>
  </ul>""",
                f"""<h2>O que derruba os benefícios</h2>
  <p>A cobertura depende do DAS pago. Ficar muitos meses sem pagar faz você perder a qualidade de segurado, e a contribuição paga com atraso nem sempre conta pra carência. Na prática: quem quer ter o auxílio quando precisar paga o DAS em dia, todo mês.</p>
  <p>Pede o benefício pelo aplicativo Meu INSS ou pelo telefone 135.</p>""",
            ],
            "faq": [
                ("MEI tem direito a aposentadoria?", "Tem, à aposentadoria por idade, no valor de um salário mínimo: mulheres aos 62 anos e homens aos 65, com o tempo mínimo de contribuição."),
                ("MEI tem direito a auxílio-doença?", "Tem, depois de 12 meses de contribuição. Em caso de acidente, não precisa de carência."),
                ("MEI tem salário-maternidade?", "Tem, por 120 dias, no valor de um salário mínimo. Desde 2024 não exige número mínimo de contribuições."),
                ("MEI tem seguro-desemprego?", "Não. O seguro-desemprego é pra quem perde emprego com carteira."),
                ("Como aposentar com mais que um salário mínimo sendo MEI?", "Só com contribuição a mais. A complementação de 15% conta o tempo, mas o valor depende do quanto e por quanto tempo você contribuiu. Vale conversar com um especialista em previdência."),
            ],
            "fontes": [("INSS", "https://www.gov.br/inss/pt-br"), ("Portal do Empreendedor", "https://www.gov.br/empresas-e-negocios/pt-br/empreendedor")],
            "leia": ["/das-atrasado-mei/", "/boleto-das-mei/", "/mei-pode-ter-funcionario/"],
        },
        {
            "url": "/como-dar-baixa-mei/", "curto": "Dar baixa no MEI",
            "title": "Como dar baixa no MEI: passo a passo, dívidas e declaração",
            "desc": "Como encerrar o MEI pelo gov.br de graça, o que acontece com as dívidas, o prazo da declaração de extinção e quando é melhor não fechar.",
            "chapeu": "Encerrar o CNPJ", "h1": "Como dar baixa no MEI sem deixar pendência",
            "entrada": "Fechar o MEI é grátis e sai na hora pelo gov.br. Mas as dívidas não somem, e ainda falta uma declaração depois. Veja a ordem certa.",
            "resumo": [("Custo", "Grátis", "Pela internet"), ("Tempo", "Na hora", "Sai o CCMEI baixado"),
                       ("Dívidas", "Continuam", "Com você"), ("Depois", "Declaração", "De extinção")],
            "secoes": [
                f"""<h2>Antes de fechar, confira</h2>
  <ul class="lista">
    <li><strong>Tem empregado?</strong> Faça a demissão e o acerto no eSocial antes.</li>
    <li><strong>Tem dívida antiga?</strong> O perdão da LC 238/2026 pede seis meses de DAS em dia, e com o MEI fechado não há DAS pra pagar. <a href="/perdao-dividas-mei/">Leia as regras</a> antes de decidir.</li>
    <li><strong>Passou do limite?</strong> Talvez o caso seja migrar pra microempresa, não fechar. <a href="/limite-mei/">Veja o limite</a>.</li>
    <li><strong>Vai continuar trabalhando?</strong> Sem o MEI, você perde a cobertura do INSS que o DAS garante.</li>
  </ul>""",
                f"""<h2>Passo a passo</h2>
  <ol class="lista">
    <li>Entre no {PORTAL} e escolha <strong>Já sou MEI</strong> e depois <strong>Solicitar baixa</strong>.</li>
    <li>Entre com a conta gov.br prata ou ouro.</li>
    <li>Confirme os dados e as declarações.</li>
    <li>Salve o certificado (CCMEI) com a situação de baixa. É o seu comprovante.</li>
  </ol>""",
                f"""<h2>Depois da baixa</h2>
  <ol class="lista">
    <li><strong>Entregue a declaração de extinção</strong> (DASN-SIMEI de situação especial). Baixou entre janeiro e abril: até 30 de junho. Entre maio e dezembro: até o último dia do mês seguinte.</li>
    <li><strong>Pague os DAS até o mês da baixa.</strong> Eles continuam valendo e podem ser parcelados.</li>
    <li><strong>Cancele</strong> débito automático, maquininha no CNPJ e contas que não vai mais usar.</li>
  </ol>
  <p>Quer voltar a ser MEI depois? Pode abrir de novo. Sai um CNPJ novo.</p>""",
            ],
            "faq": [
                ("Quanto custa dar baixa no MEI?", "Nada. É feito pelo Portal do Empreendedor, de graça."),
                ("Posso dar baixa no MEI com dívida?", "Pode. A dívida continua e precisa ser paga, e pode ir pra dívida ativa no seu nome."),
                ("Qual o prazo da declaração de extinção do MEI?", "Baixa entre janeiro e abril: até 30 de junho. Entre maio e dezembro: até o último dia do mês seguinte à baixa."),
                ("Depois de dar baixa posso abrir outro MEI?", "Pode. Você faz uma nova formalização e recebe um CNPJ novo."),
                ("Posso só deixar o MEI parado?", "Pode, mas continua devendo o DAS todo mês e a declaração anual. Se não vai usar, é melhor dar baixa."),
            ],
            "fontes": [("Portal do Empreendedor", "https://www.gov.br/empresas-e-negocios/pt-br/empreendedor"),
                       ("DASN-SIMEI no Portal do Simples Nacional", "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/dasnsimei.app/Identificacao")],
            "leia": ["/das-atrasado-mei/", "/declaracao-anual-mei/", "/perdao-dividas-mei/"],
        },
        {
            "url": "/boleto-das-mei/", "curto": "Boleto do DAS",
            "title": f"Boleto do DAS MEI {ANO}: como emitir, pagar no Pix e débito automático",
            "desc": f"Como emitir o boleto do DAS MEI {ANO} pelo PGMEI ou pelo aplicativo, pagar com Pix, ligar o débito automático e evitar o golpe do boleto falso.",
            "chapeu": "Guia do DAS", "h1": f"Boleto do DAS MEI {ANO}: emitir, pagar e não esquecer",
            "entrada": f"O DAS vence todo dia 20 e custa {brl(INSS + 5)} pra serviço e {brl(INSS + 1)} pra comércio em {ANO}. Você emite em um minuto, só com o CNPJ, e paga com Pix.",
            "resumo": [("Vencimento", "Dia 20", "Do mês seguinte"), ("Serviço", brl(INSS + 5), "Por mês"),
                       ("Comércio", brl(INSS + 1), "Por mês"), ("Precisa de", "Só o CNPJ", "No PGMEI")],
            "secoes": [
                f"""<h2>Como emitir pelo site</h2>
  <ol class="lista">
    <li>Entre no {PGMEI}, o site da Receita pra gerar o DAS.</li>
    <li>Digite o CNPJ. Não precisa de senha.</li>
    <li>Clique em <strong>Emitir guia de pagamento</strong> e escolha o ano.</li>
    <li>Marque o mês (ou vários meses de uma vez) e clique em <strong>Apurar / Gerar DAS</strong>.</li>
    <li>Baixe o PDF. A guia tem código de barras e QR code do Pix.</li>
  </ol>
  <p>Pelo celular, o aplicativo MEI, do governo, faz o mesmo e avisa quando vence.</p>""",
                f"""<h2>Como pagar</h2>
  <ul class="lista">
    <li><strong>Pix:</strong> leia o QR code da guia no app do banco. É o mais rápido.</li>
    <li><strong>Código de barras:</strong> no app do banco, na lotérica ou no caixa.</li>
    <li><strong>Débito automático:</strong> no próprio PGMEI, em <strong>Débito automático</strong>, escolha o banco. Daí em diante o DAS sai sozinho todo dia 20.</li>
  </ul>
  <p>O valor muda todo janeiro, junto com o salário mínimo. <a href="/calculadora-das-mei/">Confira o seu</a>.</p>""",
                f"""<h2>Cuidado com o boleto falso</h2>
  <div class="aviso"><p>O governo não manda DAS pelo correio, por e-mail ou por WhatsApp. Boletos de "taxa de registro", "contribuição sindical" ou "cadastro nacional" que chegam assim são golpe. Só pague a guia que você mesmo gerou no PGMEI ou no aplicativo MEI.</p></div>
  <p>Atrasou? A guia gerada hoje já vem com multa e juros. <a href="/das-atrasado-mei/">Veja como regularizar</a>.</p>""",
            ],
            "faq": [
                ("Como tirar o boleto do DAS MEI?", "No PGMEI, site da Receita, só com o CNPJ, ou pelo aplicativo MEI do governo."),
                ("Quando vence o DAS do MEI?", "Todo dia 20, sobre o mês anterior. Se cair em dia sem expediente bancário, vai pro dia útil seguinte."),
                ("Dá pra pagar o DAS com Pix?", "Dá. A guia tem QR code do Pix."),
                ("Dá pra emitir o DAS do ano inteiro?", "Dá. No PGMEI, marque os meses que quiser. Cada guia tem o seu vencimento."),
                (f"Quanto é o DAS do MEI em {ANO}?", f"{brl(INSS + 5)} pra serviço, {brl(INSS + 1)} pra comércio e {brl(INSS + 6)} pra quem faz os dois."),
            ],
            "fontes": [("PGMEI, Receita Federal", "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/Identificacao"),
                       ("Portal do Empreendedor", "https://www.gov.br/empresas-e-negocios/pt-br/empreendedor")],
            "leia": ["/calculadora-das-mei/", "/das-atrasado-mei/", "/declaracao-anual-mei/"],
        },
    ]


NOMES_LINK = {"/limite-mei/": "Limite de faturamento", "/calculadora-das-mei/": "Calculadora do DAS",
              "/novo-limite-mei/": "Novo limite do MEI", "/perdao-dividas-mei/": "Perdão de dívidas"}


def pagina_guia(g, nomes):
    mig, ld = migalha([("Início", "/"), (g["curto"], g["url"])])
    ld_faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in g["faq"]]}
    ld_art = {"@context": "https://schema.org", "@type": "Article", "headline": g["h1"],
              "datePublished": "2026-10-29", "dateModified": HOJE, "publisher": {"@type": "Organization", "name": "Guia do MEI"}}
    resumo = "".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}<small>{e(c)}</small></dd></div>" for a, b, c in g["resumo"])
    secoes = [f"<section>\n  {s}\n</section>" for s in g["secoes"]]
    secoes.insert(1, oferta("maquininha", g["url"].strip("/")))
    leia = "".join(f'<a href="{u}">{e(nomes[u])}</a>' for u in g["leia"])
    fontes = ", ".join(f'<a href="{u}" rel="noopener">{e(t)}</a>' for t, u in g["fontes"])
    corpo = f"""<main id="conteudo"><div class="w">
{mig}
<div class="titulo-pag">
  <p class="chapeu" style="color:#8A6400">{e(g["chapeu"])}</p>
  <h1>{e(g["h1"])}</h1>
  <p class="entrada">{e(g["entrada"])}</p>
</div>
<dl class="resumo">{resumo}</dl>
{"".join(secoes)}
{chamada_planilha(g["url"].strip("/"))}
<section>
  <h2>Perguntas frequentes</h2>
  {"".join(f'<details><summary>{e(q)}</summary><div><p>{e(a)}</p></div></details>' for q, a in g["faq"])}
</section>
<section>
  <h2>Leia também</h2>
  <div class="grade">{leia}</div>
</section>
<p class="fonte">Fontes: {fontes}. Atualizado em {HOJE_BR}. As regras mudam: confira sempre no Portal do Empreendedor antes de agir.</p>
</div></main>
"""
    return cabeca(g["title"], g["desc"], g["url"], [ld, ld_faq, ld_art]) + corpo + RODAPE


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
    gs = guias()
    nomes = dict(NOMES_LINK, **{g["url"]: g["curto"] for g in gs})
    for g in gs:
        escrever(g["url"], pagina_guia(g, nomes))
    urls[4:4] = ["/novo-limite-mei/", "/perdao-dividas-mei/"] + [g["url"] for g in gs]
    if PLANILHA["kiwify"]:
        urls.append("/planilha-mei/")

    urls += ["/crm/", "/crm/calculadora/", "/crm/dimensionamento/", "/crm/blog/", "/crm/blog/como-medir-crm/",
             "/crm/blog/metricas-de-crm/", "/crm/blog/o-que-e-incrementalidade/", "/privacidade/"]
    (RAIZ / "sitemap.xml").write_text(sitemap(urls), encoding="utf-8", newline="\n")
    print(f"{len(ocs)} ocupações, {len(urls)} urls no sitemap")


if __name__ == "__main__":
    main()
