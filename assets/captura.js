/* Captura de e-mail em troca do checklist dos falsos controles.
   Injeta o formulario em qualquer <div id="captura"></div> da pagina.

   Para funcionar, ENDPOINT precisa apontar para um servico de formulario
   (Formspree, Tally, Getform). Enquanto estiver vazio, o bloco nao aparece
   — melhor nada do que um formulario que engole o e-mail de quem confiou. */
(function () {
  var ENDPOINT = "https://formspree.io/f/xwleybzz";
  var ARQUIVO = "/checklist-falsos-controles.pdf";

  var alvo = document.getElementById("captura");
  if (!alvo || !ENDPOINT) return;

  var css = document.createElement("style");
  css.textContent = [
    ".cap{background:#fff;border:1px solid #EFD9E5;border-radius:14px;padding:30px;",
    "  box-shadow:0 10px 40px rgba(61,10,91,.08);max-width:640px;margin:0 auto}",
    ".cap .k{font-size:11.5px;letter-spacing:.18em;text-transform:uppercase;",
    "  color:#E8590C;font-weight:700;margin-bottom:10px}",
    ".cap h3{font-size:22px;font-weight:900;color:#3D0A5B;line-height:1.22;margin:0 0 8px}",
    ".cap p{font-size:15.5px;color:#4A3D52;margin:0 0 18px;line-height:1.5}",
    ".cap form{display:flex;gap:10px;flex-wrap:wrap}",
    ".cap input[type=email]{flex:1 1 240px;font:inherit;font-size:16px;padding:13px 14px;",
    "  border:1.5px solid #EFD9E5;border-radius:9px;background:#FDF0F5;color:#1A1523}",
    ".cap input[type=email]:focus{outline:3px solid rgba(232,89,12,.35);outline-offset:1px;",
    "  border-color:#E8590C;background:#fff}",
    ".cap button{font:inherit;font-size:16px;font-weight:700;padding:13px 26px;border:0;",
    "  border-radius:9px;background:#C2185B;color:#fff;cursor:pointer}",
    ".cap button:disabled{opacity:.6;cursor:progress}",
    ".cap .aviso{font-size:12.5px;color:#7A6B82;margin:12px 0 0;line-height:1.45}",
    ".cap .ok{background:#E8F5EF;border-left:5px solid #0F7B5A;padding:18px 20px;border-radius:0 10px 10px 0}",
    ".cap .ok b{color:#0F7B5A;display:block;margin-bottom:6px;font-size:17px}",
    ".cap .ok a{color:#C2185B;font-weight:700}",
    ".cap .erro{color:#C2185B;font-size:14px;margin:10px 0 0}"
  ].join("");
  document.head.appendChild(css);

  alvo.innerHTML =
    '<div class="cap">' +
    '  <div class="k">Material gratuito</div>' +
    '  <h3>O checklist dos falsos controles</h3>' +
    '  <p>Duas páginas para conferir, antes da reunião, se o resultado que você tem em mãos prova o que afirma provar: os seis falsos controles mais comuns, as três armadilhas que se disfarçam de boa notícia e os erros de cálculo que invalidam o número.</p>' +
    '  <form novalidate>' +
    '    <input type="email" name="email" required autocomplete="email" placeholder="seu e-mail de trabalho" aria-label="Seu e-mail">' +
    '    <button type="submit">Receber o checklist</button>' +
    '  </form>' +
    '  <p class="aviso">Você recebe o checklist na hora. Depois, no máximo um e-mail por semana sobre mensuração de CRM, e o link para sair fica em todos eles. Seu endereço não é vendido nem repassado — <a href="/privacidade/">política de privacidade</a>.</p>' +
    '</div>';

  var form = alvo.querySelector("form");
  var botao = form.querySelector("button");
  var campo = form.querySelector("input");

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var email = campo.value.trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email)) {
      mostrarErro("Confira o endereço: parece que falta alguma coisa.");
      return;
    }
    botao.disabled = true;
    botao.textContent = "Enviando...";

    var dados = new FormData();
    dados.append("email", email);
    dados.append("origem", location.pathname);

    fetch(ENDPOINT, { method: "POST", body: dados, headers: { Accept: "application/json" } })
      .then(function (r) {
        if (!r.ok) throw new Error("falha no envio");
        alvo.querySelector(".cap").innerHTML =
          '<div class="ok"><b>Pronto.</b>' +
          'O checklist está aqui: <a href="' + ARQUIVO + '" download>baixar o PDF</a>.' +
          ' Ele também vale como referência rápida antes de qualquer apresentação.</div>';
      })
      .catch(function () {
        botao.disabled = false;
        botao.textContent = "Receber o checklist";
        mostrarErro("Não consegui enviar agora. Tente de novo em instantes.");
      });
  });

  function mostrarErro(texto) {
    var antigo = alvo.querySelector(".erro");
    if (antigo) antigo.remove();
    var p = document.createElement("p");
    p.className = "erro";
    p.textContent = texto;
    form.parentNode.insertBefore(p, form.nextSibling);
  }
})();
