
/* Demonstração: não cria conta nem armazena dados. */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("cadastro-form");

  if (!form) return;

  const nome = document.getElementById("nome");
  const email = document.getElementById("email");
  const senha = document.getElementById("senha");
  const confirmar = document.getElementById("confirmar");

  const campos = [nome, email, senha, confirmar].filter(Boolean);
  const statusCadastro = document.getElementById("cadastro-status");
  const botaoGoogle = document.getElementById("google");
  const statusGoogle = document.getElementById("google-status");

  function validar(campo) {
    if (!campo) return false;

    let erro = "";

    if (!campo.value.trim()) {
      erro = "Preencha este campo.";
    } else if (
      campo === nome &&
      campo.value.trim().length < 2
    ) {
      erro = "Informe seu nome completo.";
    } else if (
      campo === email &&
      campo.validity.typeMismatch
    ) {
      erro = "Informe um e-mail válido.";
    } else if (
      campo === senha &&
      campo.value.length < 8
    ) {
      erro = "A senha precisa ter pelo menos 8 caracteres.";
    } else if (
      campo === confirmar &&
      campo.value !== senha.value
    ) {
      erro = "As senhas não são iguais.";
    }

    campo.setAttribute("aria-invalid", String(Boolean(erro)));

    const mensagemErro = document.getElementById(
      `${campo.id}-erro`
    );

    if (mensagemErro) mensagemErro.textContent = erro;

    return erro === "";
  }

  campos.forEach((campo) => {
    campo.addEventListener("input", () => {
      if (statusCadastro) statusCadastro.textContent = "";

      if (campo.getAttribute("aria-invalid") === "true") {
        validar(campo);
      }

      if (campo === senha && confirmar?.value) {
        validar(confirmar);
      }

      if (campo === confirmar && confirmar.value) {
        validar(confirmar);
      }
    });
  });

  // Mostrar ou ocultar senha.
  document.querySelectorAll(".toggle-senha").forEach((botao) => {
    botao.addEventListener("click", () => {
      const campoId = botao.getAttribute("aria-controls");
      const campo = document.getElementById(campoId);

      if (!campo) {
        console.error("Campo de senha não encontrado:", campoId);
        return;
      }

      const mostrar = campo.type === "password";

      campo.type = mostrar ? "text" : "password";
      botao.setAttribute("aria-pressed", String(mostrar));
      botao.setAttribute(
        "aria-label",
        mostrar ? "Ocultar senha" : "Mostrar senha"
      );

      botao.textContent = mostrar ? "Ocultar" : "Mostrar";
    });
  });

  form.addEventListener("submit", (evento) => {
    evento.preventDefault();

    const resultados = campos.map(validar);
    const primeiroErro = resultados.indexOf(false);

    if (primeiroErro !== -1) {
      if (statusCadastro) {
        statusCadastro.textContent =
          "Existem campos que precisam ser corrigidos.";
      }

      campos[primeiroErro].focus();
      return;
    }

    if (statusCadastro) {
      statusCadastro.textContent =
        "Dados validados. Este cadastro é demonstrativo: " +
        "nenhuma conta foi criada ou dado foi salvo.";
    }
  });

  if (botaoGoogle && statusGoogle) {
    botaoGoogle.addEventListener("click", () => {
      statusGoogle.textContent =
        "O cadastro com Google ainda não está conectado.";
    });
  }
});
