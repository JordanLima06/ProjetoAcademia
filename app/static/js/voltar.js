/**
 * FightAcademy — Navegação Padronizada do Botão "Voltar"
 * 
 * Regras:
 * 1. Valida se document.referrer pertence à mesma origem e é diferente da URL atual.
 * 2. Em caso positivo, aciona window.history.back().
 * 3. Em caso negativo (acesso direto, referrer vazio ou externo), redireciona para o fallback (data-fallback ou '/').
 */
document.addEventListener("DOMContentLoaded", () => {
  const botoesVoltar = document.querySelectorAll("[data-action='voltar']");

  botoesVoltar.forEach((botao) => {
    botao.addEventListener("click", (evento) => {
      evento.preventDefault();

      const fallbackUrl = botao.getAttribute("data-fallback") || "/";
      const referrer = document.referrer;

      // Validação estrita: referrer presente, mesma origem e diferente da URL atual
      const isInternalReferrer =
        Boolean(referrer) &&
        referrer.startsWith(window.location.origin) &&
        referrer !== window.location.href;

      if (isInternalReferrer) {
        window.history.back();
      } else {
        window.location.href = fallbackUrl;
      }
    });
  });
});
