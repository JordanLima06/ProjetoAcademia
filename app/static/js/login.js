
/* Demonstração: não autentica nem armazena credenciais. */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("login-form");

  if (!form) return;

  const email = document.getElementById("email");
  const senha = document.getElementById("senha");
  const statusLogin = document.getElementById("login-status");
  const entrar = document.getElementById("entrar");
  const mostrar = document.getElementById("mostrar-senha");

  form.noValidate = true;

  function validar(campo, erroId) {
    if (!campo) return false;

    let mensagem = "";

    if (!campo.value.trim()) {
      mensagem = "Preencha este campo.";
    } else if (
      campo.type === "email" &&
      campo.validity.typeMismatch
    ) {
      mensagem = "Informe um e-mail válido.";
    }

    const erro = document.getElementById(erroId);

    if (erro) erro.textContent = mensagem;

    campo.setAttribute("aria-invalid", String(Boolean(mensagem)));

    return mensagem === "";
  }

  // Mostrar ou ocultar senha.
  if (mostrar && senha) {
    mostrar.addEventListener("click", () => {
      const visivel = senha.type === "password";

      senha.type = visivel ? "text" : "password";

      mostrar.setAttribute("aria-pressed", String(visivel));
      mostrar.setAttribute(
        "aria-label",
        visivel ? "Ocultar senha" : "Mostrar senha"
      );

      // Atualiza o ícone do olho.
      const icone = mostrar.querySelector("svg");

      if (icone) {
        icone.innerHTML = visivel
          ? '<path d="M3 3l18 18"/><path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.9 5.2A11 11 0 0 1 12 5c6.5 0 10 7 10 7a16 16 0 0 1-3.1 3.9"/><path d="M6.6 6.6C3.6 8.4 2 12 2 12s3.5 7 10 7a10 10 0 0 0 3-.5"/>'
          : '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>';
      }
    });
  }

  // Validação demonstrativa do login.
  form.addEventListener("submit", (evento) => {
    evento.preventDefault();

    const emailOk = validar(email, "email-erro");
    const senhaOk = validar(senha, "senha-erro");

    if (!emailOk || !senhaOk) {
      if (statusLogin) {
        statusLogin.textContent =
          "Confira os campos indicados antes de continuar.";
      }

      (!emailOk ? email : senha)?.focus();
      return;
    }

    if (!entrar) return;

    entrar.disabled = true;
    entrar.textContent = "Verificando…";
    form.setAttribute("aria-busy", "true");

    if (statusLogin) {
      statusLogin.textContent = "Verificando o preenchimento…";
    }

    window.setTimeout(() => {
      if (statusLogin) {
        statusLogin.textContent =
          "Preenchimento válido. Nenhuma conta foi autenticada.";
      }

      entrar.disabled = false;
      entrar.textContent = "Entrar";
      form.removeAttribute("aria-busy");
    }, 700);
  });

  // Recuperação de senha demonstrativa.
  const esqueci = document.getElementById("esqueci");
  const recuperacao = document.getElementById("recuperacao");
  const recuperarEmail = document.getElementById("recuperar-email");
  const cancelar = document.getElementById("cancelar");
  const recuperarForm = document.getElementById("recuperar-form");

  function fecharRecuperacao() {
    if (!recuperacao || !esqueci) return;

    recuperacao.hidden = true;
    esqueci.setAttribute("aria-expanded", "false");
    esqueci.focus();
  }

  if (esqueci && recuperacao && recuperarEmail) {
    esqueci.addEventListener("click", () => {
      const abrir = recuperacao.hidden;

      recuperacao.hidden = !abrir;
      esqueci.setAttribute("aria-expanded", String(abrir));

      if (abrir) recuperarEmail.focus();
    });
  }

  cancelar?.addEventListener("click", fecharRecuperacao);

  recuperacao?.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape") fecharRecuperacao();
  });

  if (recuperarForm && recuperarEmail) {
    recuperarForm.noValidate = true;

    recuperarForm.addEventListener("submit", (evento) => {
      evento.preventDefault();

      if (!validar(recuperarEmail, "recuperar-erro")) {
        recuperarEmail.focus();
        return;
      }

      const status = document.getElementById("recuperar-status");

      if (status) {
        status.textContent =
          "Solicitação simulada. Nenhum e-mail foi enviado.";
      }
    });
  }

  // Acesso com Google ainda não integrado.
  document.getElementById("google")?.addEventListener("click", () => {
    const status = document.getElementById("google-status");

    if (status) {
      status.textContent =
        "O acesso com Google ainda não está conectado.";
    }
  });

  // Limpa mensagens enquanto o usuário corrige os campos.
  [
    [email, "email-erro"],
    [senha, "senha-erro"],
    [recuperarEmail, "recuperar-erro"]
  ].forEach(([campo, erroId]) => {
    campo?.addEventListener("input", () => {
      if (campo.getAttribute("aria-invalid") === "true") {
        validar(campo, erroId);
      }

      if (campo === recuperarEmail) {
        const status = document.getElementById("recuperar-status");
        if (status) status.textContent = "";
      } else if (statusLogin) {
        statusLogin.textContent = "";
      }
    });
  });
});
