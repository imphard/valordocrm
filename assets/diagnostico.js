/* Monta uma folha de diagnóstico com os números que a pessoa colocou na
   calculadora e a entrega como PDF pela impressão do navegador.

   Por que impressão e não uma biblioteca de PDF: assim a folha sai com a
   Appetite Pro e as cores da marca, sem carregar mais nada na página. A
   folha vive no HTML, escondida na tela e visível só no papel. */
(function () {
  var pega = function (id) {
    var el = document.getElementById(id);
    if (!el) return "";
    return (el.value !== undefined && el.tagName === "INPUT") ? el.value : el.textContent.trim();
  };
  var mil = function (v) {
    return String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  };

  // ---------- estilo, só para impressão ----------
  var css = document.createElement("style");
  css.textContent = [
    ".folha{display:none}",
    "@media print{",
    "  body>*:not(.folha){display:none !important}",
    "  .folha{display:block;font-family:'Appetite Pro',Georgia,serif;color:#1A1523;",
"    background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact}",
    "  @page{size:A4;margin:13mm 15mm}",
    "  .folha .topo{border-bottom:3px solid #C2185B;padding-bottom:5mm;margin-bottom:7mm}",
    "  .folha .eb{font-size:8pt;letter-spacing:.22em;text-transform:uppercase;color:#E8590C;font-weight:700}",
    "  .folha h1{font-size:21pt;font-weight:900;color:#3D0A5B;margin:3mm 0 2mm;line-height:1.15}",
    "  .folha .sub{font-size:9.5pt;color:#7A6B82}",
    "  .folha h2{font-size:11.5pt;font-weight:900;color:#C2185B;margin:5.5mm 0 2mm}",
    "  .folha table{width:100%;border-collapse:collapse;font-size:10pt;margin-bottom:3mm}",
    "  .folha td{padding:1.9mm 0;border-bottom:1px solid #EFD9E5}",
    "  .folha td:last-child{text-align:right;font-weight:700}",
    "  .folha .veredito{background:#FFF6E4;border:1px solid #EFD9E5;border-left:4pt solid #E8590C;",
"    padding:4mm;margin:4mm 0}",
    "  .folha .veredito .g{font-size:15pt;font-weight:900;color:#3D0A5B;line-height:1.2}",
    "  .folha .veredito p{font-size:9.5pt;color:#4A3D52;margin:2.5mm 0 0}",
    "  .folha .grade{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;margin:4mm 0}",
    "  .folha .cx{background:#FDF0F5;border:1px solid #EFD9E5;border-radius:2mm;padding:3.5mm;min-width:0}",
    "  .folha .cx .n{font-size:13.5pt;font-weight:900;color:#C2185B;line-height:1}",
    "  .folha .cx .l{font-size:8pt;color:#7A6B82;margin-top:1.5mm}",
    "  .folha .nota{font-size:9pt;color:#4A3D52;line-height:1.45;margin:0}",
    "  .folha .rod{border-top:1px solid #EFD9E5;margin-top:6mm;padding-top:2.5mm;",
    "    font-size:8pt;color:#7A6B82;display:flex;justify-content:space-between}",
    "  .folha .rod b{color:#C2185B}",
    "}"
  ].join("");
  document.head.appendChild(css);

  var folha = document.createElement("div");
  folha.className = "folha";
  document.body.appendChild(folha);

  function montar() {
    var hoje = new Date().toLocaleDateString("pt-BR");
    var base = +pega("base") || 0;
    var conv = +pega("conv") || 0;
    var taxaCampanha = base ? (conv / base * 100).toFixed(2).replace(".", ",") : ", ";

    folha.innerHTML =
      '<div class="topo">' +
      '  <div class="eb">Diagnóstico de incrementalidade</div>' +
      '  <h1>O que a sua campanha realmente causou</h1>' +
      '  <div class="sub">Gerado em ' + hoje + ' · valordocrm.com.br</div>' +
      '</div>' +

      '<h2>Os números que você informou</h2>' +
      '<table>' +
      '  <tr><td>Base impactada</td><td>' + mil(base) + '</td></tr>' +
      '  <tr><td>Conversões atribuídas</td><td>' + mil(conv) + '</td></tr>' +
      '  <tr><td>Receita atribuída</td><td>R$ ' + mil(+pega("rec") || 0) + '</td></tr>' +
      '  <tr><td>Custo da campanha</td><td>R$ ' + mil(+pega("custo") || 0) + '</td></tr>' +
      '  <tr><td>Taxa de conversão observada</td><td>' + taxaCampanha + '%</td></tr>' +
      '  <tr><td>Taxa de compra natural assumida</td><td>' + pega("taxaVal").replace(/%*$/, "") + '%</td></tr>' +
      '</table>' +

      '<div class="veredito">' +
      '  <div class="g">' + pega("vBig") + '</div>' +
      '  <p>' + pega("vWhy") + '</p>' +
      '</div>' +

      '<div class="grade">' +
      '  <div class="cx"><div class="n">' + pega("mInc") + '</div><div class="l">conversões incrementais</div></div>' +
      '  <div class="cx"><div class="n">' + pega("mRec") + '</div><div class="l">receita incremental</div></div>' +
      '  <div class="cx"><div class="n">' + pega("mRoiRep") + '</div><div class="l">ROI no report</div></div>' +
      '  <div class="cx"><div class="n">' + pega("mRoiReal") + '</div><div class="l">ROI real</div></div>' +
      '</div>' +

      '<h2>O ponto de virada</h2>' +
      '<p class="nota">' + (pega("flipT") || ", ") + ' ' + (pega("flipP") || "") + '</p>' +

      '<h2>O que este número ainda não é</h2>' +
      '<p class="nota">A taxa de compra natural usada aqui é uma <b>premissa</b>, não uma medição: ' +
      'ela foi escolhida por você, não observada. Para transformar esta estimativa em prova, ' +
      'a taxa precisa vir de um grupo de controle sorteado antes do disparo e isolado da campanha. ' +
      'Enquanto isso não existir, este diagnóstico serve para dimensionar o risco de estar ' +
      'creditando à campanha um resultado que aconteceria de qualquer forma.</p>' +

      '<h2>Próximo passo</h2>' +
      '<p class="nota">Verifique se a sua base comporta o efeito que você espera medir, em ' +
      'valordocrm.com.br/dimensionamento, antes de reservar o grupo de controle. Base pequena ' +
      'só enxerga efeito grande, e descobrir isso depois do teste custa um trimestre.</p>' +

      '<div class="rod">' +
      '  <span>Provando Valor do CRM · <b>valordocrm.com.br</b></span>' +
      '  <span>Números fictícios ou reais, contas reais</span>' +
      '</div>';
  }

  // mantém a folha em dia com o que está na tela
  ["input", "change", "click"].forEach(function (ev) {
    document.addEventListener(ev, function () { setTimeout(montar, 60); }, true);
  });
  montar();

  // ---------- botão ----------
  var alvo = document.getElementById("copiar");
  if (!alvo) return;
  var b = document.createElement("button");
  b.className = alvo.className;
  b.type = "button";
  b.textContent = "Baixar o diagnóstico em PDF";
  b.addEventListener("click", function () { montar(); window.print(); });
  alvo.parentNode.insertBefore(b, alvo);
})();
