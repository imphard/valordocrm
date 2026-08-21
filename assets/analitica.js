/* Medição de audiência do site.

   Usa Cloudflare Web Analytics: gratuito, sem cookie, sem identificar
   ninguém, e por isso sem necessidade de banner de consentimento.

   Enquanto TOKEN estiver vazio, nada é carregado: o site não chama
   servidor nenhum e não coleta nada. */
(function () {
  var TOKEN = "";  // token do Cloudflare Web Analytics

  if (!TOKEN) return;

  var s = document.createElement("script");
  s.defer = true;
  s.src = "https://static.cloudflareinsights.com/beacon.min.js";
  s.setAttribute("data-cf-beacon", JSON.stringify({ token: TOKEN }));
  document.head.appendChild(s);
})();
