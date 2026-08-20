/* Propaga a origem da visita até o checkout da Kiwify.
   Um artigo linka para a home como  /?ref=artigo-como-medir-crm .
   Este script guarda esse "ref" e o injeta como UTM em qualquer link de
   checkout da página, para o painel da Kiwify mostrar o que converteu.
   Se não houver ref, nada acontece. */
(function () {
  var ref = null;
  try {
    var p = new URLSearchParams(location.search);
    ref = p.get("ref") || p.get("utm_content");
    if (ref) sessionStorage.setItem("origem_crm", ref);
    else ref = sessionStorage.getItem("origem_crm");
  } catch (e) { /* navegador sem sessionStorage: segue sem rastreio */ }
  if (!ref) return;

  document.querySelectorAll('a[href*="kiwify"]').forEach(function (a) {
    try {
      var u = new URL(a.href, location.href);
      u.searchParams.set("utm_source", "site");
      u.searchParams.set("utm_medium", "organico");
      u.searchParams.set("utm_content", ref);
      a.href = u.toString();
    } catch (e) { /* href inválido: deixa como está */ }
  });
})();
