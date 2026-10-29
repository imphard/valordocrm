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

# Links de parceiros. Bloco só aparece quando a url estiver preenchida.
OFERTAS = {
    "contabilidade": {
        "url": "",
        "rotulo": "Parceiro",
        "texto": "Prefere que alguém cuide do DAS, da declaração e das notas por você? Uma contabilidade online resolve tudo pelo celular.",
        "botao": "Ver contabilidade online",
    },
    "maquininha": {
        "url": "",
        "rotulo": "Parceiro",
        "texto": "Recebe no cartão ou no Pix? Uma maquininha sem mensalidade, com o dinheiro na conta no mesmo dia, ajuda a separar o dinheiro do negócio do pessoal.",
        "botao": "Ver a maquininha",
    },
}

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


def oferta(chave, ref):
    o = OFERTAS[chave]
    if not o["url"]:
        return ""
    sep = "&" if "?" in o["url"] else "?"
    return (f'<aside class="oferta"><p><span class="rot">{e(o["rotulo"])}</span>{e(o["texto"])}</p>'
            f'<a class="btn" rel="sponsored noopener" target="_blank" href="{e(o["url"])}{sep}utm_source=guiadomei&amp;utm_content={e(ref)}">{e(o["botao"])}</a></aside>')


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
<link rel="stylesheet" href="/assets/mei.css">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#0B6B48">
{lds}
</head>
<body>
<a class="pular" href="#conteudo">Pular para o conteúdo</a>
<header class="topo"><div class="w">
  <a class="marca" href="/">Guia do <b>MEI</b></a>
  <nav class="nav">
    <a href="/mei/">Todas as profissões</a>
    <a href="/calculadora-das-mei/">Calculadora do DAS</a>
    <a href="/limite-mei/">Limite de faturamento</a>
  </nav>
</div></header>
"""


RODAPE = f"""<footer class="rodape"><div class="w">
  <div>Guia do MEI · informação independente, sem ligação com o governo. Abrir MEI no Portal do Empreendedor é grátis.</div>
  <div><a href="/mei/">Profissões</a> · <a href="/calculadora-das-mei/">DAS</a> · <a href="/limite-mei/">Limite</a> · <a href="/privacidade/">Privacidade</a> · <a href="/crm/">Provando o valor do CRM</a></div>
</div></footer>
<script src="/assets/mei.js" defer></script>
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
                 f"com limite de {brl(limite)[:-3]} por ano. Veja nota fiscal, obrigações e como abrir de graça.")
    inclui = {(True, True): "o INSS, o ICMS e o ISS", (False, True): "o INSS e o ISS",
              (True, False): "o INSS e o ICMS", (False, False): "só o INSS"}[(bool(icms), bool(iss))]
    mig, ld_mig = migalha([("Início", "/"), ("Profissões", "/mei/"), (nome, caminho)])
    faq = [
        (f"Qual o CNAE do MEI {nome.lower()}?",
         f"O CNAE é {o['cnae']}, {o['desc']}. Na hora de abrir o MEI, a ocupação aparece na lista como \"{o['ocupacao']}\"."),
        (f"Quanto o MEI {nome.lower()} paga por mês em {ANO}?",
         f"{brl(mes)} por mês no DAS, que vence todo dia 20. Esse valor já inclui {inclui}."),
        (f"Quanto o MEI {nome.lower()} pode faturar?",
         f"Até {brl(limite)[:-3]} por ano. No ano em que abre, o limite é proporcional: {brl(limite / 12)[:-3]} por mês de atividade."),
        ("Pode ter funcionário?", "Pode ter um empregado, que receba o salário mínimo ou o piso da categoria."),
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
  <div><dt>Limite por ano</dt><dd>{brl(limite)[:-3]}<small>{brl(limite / 12)[:-3]} por mês, em média</small></dd></div>
</dl>

<section>
  <h2>Quanto o MEI {e(nome.lower())} paga de DAS</h2>
  <p>O DAS é a guia única do MEI. Ele junta a contribuição pro INSS com o imposto da sua atividade, num valor fixo que não muda com o quanto você fatura. Vence todo dia 20, referente ao mês anterior.</p>
  {tabela_das(t)}
  <p>Pagando em dia você conta tempo pra aposentadoria por idade e tem direito a auxílio-doença e salário-maternidade, depois das carências do INSS. <a href="/calculadora-das-mei/?tipo={TIPO_CALC[t]}">Simular o DAS, inclusive com atraso</a>.</p>
</section>

{oferta("maquininha", s)}

<section>
  <h2>Pode ser MEI? As condições</h2>
  <ul class="lista">
    <li><strong>Faturar até {brl(limite)[:-3]} por ano</strong>, somando tudo que entrar pelo CNPJ.</li>
    <li><strong>Não ser sócio, dono ou administrador de outra empresa.</strong></li>
    <li><strong>Ter no máximo um empregado</strong>, com salário mínimo ou piso da categoria.</li>
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
  <h1>Tudo do MEI, explicado pra sua profissão</h1>
  <p>Digite o que você faz e veja o CNAE certo, quanto paga por mês, se precisa de nota e como abrir de graça.</p>
  <div class="busca">
    <label for="busca-ocupacao" class="pular">Sua profissão</label>
    <input id="busca-ocupacao" type="search" placeholder="Ex.: manicure, eletricista, confeiteira" autocomplete="off">
    <ul id="busca-resultados" class="resultados"></ul>
  </div>
</div></div>

<div class="w">
<section>
  <h2>As profissões mais procuradas</h2>
  <div class="grade">{pop}</div>
  <p style="margin-top:14px"><a href="/mei/">Ver as {len(ocs)} ocupações permitidas, de A a Z</a></p>
</section>

<section>
  <h2>Quanto o MEI paga em {ANO}</h2>
  <p>O DAS subiu junto com o salário mínimo, que foi pra R$ 1.621. O INSS é 5% disso ({brl(INSS)}), e o caminhoneiro paga 12% ({brl(INSS_CAMINHONEIRO)}).</p>
  <div class="rolagem"><table><thead><tr><th>Atividade</th><th class="num">DAS por mês</th></tr></thead><tbody>{tab}</tbody></table></div>
  <p><a class="btn" href="/calculadora-das-mei/">Calcular o meu DAS</a></p>
</section>

<section>
  <h2>O limite continua R$ 81 mil</h2>
  <p>O projeto que sobe o limite pra R$ 130 mil (PLP 108/2021) passou no Senado e teve urgência aprovada na Câmara, mas ainda não foi votado nem sancionado. Até lá, vale R$ 81 mil por ano, ou R$ 6.750 por mês no ano em que o MEI é aberto.</p>
  <p><a class="btn sec" href="/limite-mei/">Ver quanto ainda dá pra faturar</a></p>
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
    opts = '<option value="0">Antes deste ano</option>' + "".join(f'<option value="{i}">Em {m} deste ano</option>' for i, m in enumerate(meses, 1))
    corpo = f"""<main id="conteudo"><div class="w">
{mig}
<div class="titulo-pag">
  <h1>Limite do MEI {ANO}: quanto ainda dá pra faturar</h1>
  <p class="entrada">Coloque o que já faturou no ano e veja quanto falta, a média por mês até dezembro e o que acontece se passar.</p>
</div>
<form id="calc-limite" class="calc" onsubmit="return false">
  <div><label for="tipo">Tipo de MEI</label>
  <select id="tipo" name="tipo"><option value="geral">MEI comum (R$ 81 mil)</option><option value="caminhoneiro">Caminhoneiro (R$ 251,6 mil)</option></select></div>
  <div><label for="abertura">Quando o MEI foi aberto</label><select id="abertura" name="abertura">{opts}</select></div>
  <div><label for="faturado">Quanto já faturou este ano (R$)</label>
  <input id="faturado" name="faturado" inputmode="decimal" placeholder="Ex.: 42.000" value=""></div>
</form>
<div class="saida" id="lim-saida"><div class="grande" id="lim-grande"></div><p id="lim-texto"></p><p id="lim-limite"></p></div>
<section>
  <h2>Como funciona o limite</h2>
  <ul class="lista">
    <li><strong>R$ 81 mil por ano</strong> pro MEI comum e R$ 251,6 mil pro caminhoneiro.</li>
    <li><strong>No ano de abertura, é proporcional:</strong> R$ 6.750 por mês de atividade, contando o mês em que abriu.</li>
    <li><strong>Passou até 20%:</strong> continua MEI até dezembro, paga um DAS complementar sobre o excesso e vira microempresa em janeiro.</li>
    <li><strong>Passou mais de 20%:</strong> o desenquadramento volta pro começo do ano (ou pra data de abertura), com os impostos recalculados.</li>
  </ul>
  <p>O projeto que subiria o limite pra R$ 130 mil ainda não foi aprovado pela Câmara. Se mudar, esta página muda junto.</p>
</section>
{oferta("contabilidade", "limite")}
</div></main>
"""
    return cabeca(f"Limite MEI {ANO}: calculadora de quanto ainda dá pra faturar",
                  "O limite do MEI segue R$ 81 mil por ano. Calcule quanto ainda pode faturar, a média por mês e o que acontece se passar.",
                  "/limite-mei/", [ld]) + corpo + RODAPE


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

    urls += ["/crm/", "/crm/calculadora/", "/crm/dimensionamento/", "/crm/blog/", "/crm/blog/como-medir-crm/",
             "/crm/blog/metricas-de-crm/", "/crm/blog/o-que-e-incrementalidade/", "/privacidade/"]
    (RAIZ / "sitemap.xml").write_text(sitemap(urls), encoding="utf-8", newline="\n")
    print(f"{len(ocs)} ocupações, {len(urls)} urls no sitemap")


if __name__ == "__main__":
    main()
