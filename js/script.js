document.addEventListener("DOMContentLoaded", () => {
  // Atualiza automaticamente o ano do rodapé.
  const currentYear = document.querySelector("#current-year");

  if (currentYear) {
    currentYear.textContent = new Date().getFullYear();
  }

  // Fecha o menu mobile após selecionar um link.
  const menu = document.querySelector("#menu");

  if (menu && window.bootstrap) {
    menu.querySelectorAll('a[href^="#"]').forEach((link) => {
      link.addEventListener("click", () => {
        if (
          window.innerWidth < 992 &&
          menu.classList.contains("show")
        ) {
          window.bootstrap.Collapse
            .getOrCreateInstance(menu)
            .hide();
        }
      });
    });
  }
});
