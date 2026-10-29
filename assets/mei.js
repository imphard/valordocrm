/* Guia do MEI: busca de ocupações e calculadoras. Tudo roda no navegador. */
(function () {
  var brl = function (v) {
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  };
  var semAcento = function (s) {
    return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  };

  // Valores de 2026: salário mínimo R$ 1.621
  var MINIMO = 1621;
  var INSS = Math.round(MINIMO * 0.05 * 100) / 100;
  var INSS_CAMINHONEIRO = Math.round(MINIMO * 0.12 * 100) / 100;
  var TIPOS = {
    servico: { inss: INSS, icms: 0, iss: 5, nome: "Serviços" },
    comercio: { inss: INSS, icms: 1, iss: 0, nome: "Comércio ou indústria" },
    ambos: { inss: INSS, icms: 1, iss: 5, nome: "Comércio e serviços" },
    locacao: { inss: INSS, icms: 0, iss: 0, nome: "Aluguel de bens" },
    caminhoneiro: { inss: INSS_CAMINHONEIRO, icms: 1, iss: 0, nome: "Caminhoneiro" },
    caminhoneiro_iss: { inss: INSS_CAMINHONEIRO, icms: 1, iss: 5, nome: "Caminhoneiro com serviço" }
  };

  // Busca da home
  var campo = document.getElementById("busca-ocupacao");
  var lista = document.getElementById("busca-resultados");
  if (campo && lista && window.OCUPACOES) {
    var itens = window.OCUPACOES.map(function (o) {
      return { n: o[0], s: o[1], c: o[2], k: semAcento(o[0] + " " + o[2] + " " + (o[3] || "")) };
    });
    // "confeiteira" acha "confeiteiro(a)", "eletricistas" acha "eletricista"
    var raiz = function (p) { return p.length > 4 ? p.replace(/(as|os|es|a|o|s)$/, "") : p; };
    campo.addEventListener("input", function () {
      var q = semAcento(campo.value.trim());
      lista.innerHTML = "";
      if (q.length < 2) return;
      var partes = q.split(/\s+/).filter(function (p) { return p.length > 2; }).map(raiz);
      if (!partes.length) return;
      var achados = itens.filter(function (i) {
        return partes.every(function (p) { return i.k.indexOf(p) >= 0; });
      }).slice(0, 8);
      if (!achados.length) {
        lista.innerHTML = '<li><a href="/mei/">Nada com esse nome. Ver a lista completa</a></li>';
        return;
      }
      lista.innerHTML = achados.map(function (i) {
        return '<li><a href="/mei/' + i.s + '/">' + i.n + "<small>CNAE " + i.c + "</small></a></li>";
      }).join("");
    });
  }

  // Calculadora do DAS
  var fDas = document.getElementById("calc-das");
  if (fDas) {
    var calcDas = function () {
      var t = TIPOS[fDas.tipo.value];
      var mes = t.inss + t.icms + t.iss;
      var atraso = Math.max(0, parseInt(fDas.atraso.value || "0", 10));
      var multa = Math.min(mes * 0.0033 * atraso, mes * 0.2);
      document.getElementById("das-mes").textContent = brl(mes);
      document.getElementById("das-detalhe").textContent =
        "INSS " + brl(t.inss) + (t.icms ? " + ICMS " + brl(t.icms) : "") + (t.iss ? " + ISS " + brl(t.iss) : "") +
        ". No ano, " + brl(mes * 12) + ".";
      document.getElementById("das-atraso").textContent = atraso
        ? "Com " + atraso + " dia(s) de atraso, a multa fica em " + brl(multa) +
          " (0,33% por dia, no máximo 20%). Os juros pela Selic entram à parte e aparecem na guia emitida no dia."
        : "Pagando até o dia 20, não tem multa nem juros.";
    };
    fDas.addEventListener("input", calcDas);
    calcDas();
  }

  // Calculadora do limite de faturamento
  var fLim = document.getElementById("calc-limite");
  if (fLim) {
    var calcLim = function () {
      var anual = fLim.tipo.value === "caminhoneiro" ? 251600 : 81000;
      var abertura = parseInt(fLim.abertura.value, 10); // 0 = aberto antes deste ano
      var meses = abertura ? 13 - abertura : 12;
      var limite = (anual / 12) * meses;
      var fat = parseFloat(String(fLim.faturado.value).replace(/\./g, "").replace(",", ".")) || 0;
      var mesAtual = new Date().getMonth() + 1;
      var restantes = Math.max(1, 12 - mesAtual + 1);
      var falta = limite - fat;
      var saida = document.getElementById("lim-saida");
      saida.className = "saida";
      document.getElementById("lim-limite").textContent = "Seu limite em " + new Date().getFullYear() + ": " + brl(limite) +
        (abertura ? " (" + meses + " meses de atividade)" : "");
      if (fat <= limite) {
        document.getElementById("lim-grande").textContent = "Faltam " + brl(falta);
        document.getElementById("lim-texto").textContent =
          "Dá pra faturar em média " + brl(falta / restantes) + " por mês até dezembro sem passar do limite.";
        if (falta < limite * 0.1) saida.className = "saida amarelo";
      } else if (fat <= limite * 1.2) {
        saida.className = "saida amarelo";
        document.getElementById("lim-grande").textContent = "Passou " + brl(fat - limite);
        document.getElementById("lim-texto").textContent =
          "Ficou até 20% acima. Você continua MEI até dezembro, paga um DAS complementar sobre o que passou e vira microempresa em janeiro.";
      } else {
        saida.className = "saida alerta";
        document.getElementById("lim-grande").textContent = "Passou " + brl(fat - limite);
        document.getElementById("lim-texto").textContent =
          "Ficou mais de 20% acima. O desenquadramento volta a janeiro (ou ao mês de abertura) e os impostos do ano são recalculados como microempresa. Procure um contador agora.";
      }
    };
    fLim.addEventListener("input", calcLim);
    calcLim();
  }
})();
