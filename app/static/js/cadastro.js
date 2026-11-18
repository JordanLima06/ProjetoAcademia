/**
 * FightAcademy — Validações e Interações da Página de Cadastro
 */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("cadastro-form");
  if (!form) return;

  const nome = document.getElementById("nome");
  const email = document.getElementById("email");
  const telefone = document.getElementById("telefone");
  const dataNascimento = document.getElementById("data_nascimento");
  const plano = document.getElementById("plano");
  const senha = document.getElementById("senha");
  const confirmar = document.getElementById("confirmar");
  const modalidade = document.getElementById("modalidade");

  const campos = [
    nome,
    email,
    telefone,
    dataNascimento,
    plano,
    senha,
    confirmar,
    modalidade
  ].filter(Boolean);

  const statusCadastro = document.getElementById("cadastro-status");
  const botaoGoogle = document.getElementById("google");
  const statusGoogle = document.getElementById("google-status");

  /* -----------------------------------------------------------
     1. Pré-seleção inteligente via Parâmetros de URL
  ----------------------------------------------------------- */
  const urlParams = new URLSearchParams(window.location.search);
  const planoParam = urlParams.get("plano");
  const modalidadeParam = urlParams.get("modalidade");

  if (planoParam && plano) {
    const optPlano = plano.querySelector(`option[value="${CSS.escape(planoParam)}"]`);
    if (optPlano) {
      plano.value = planoParam;
    }
  }

  if (modalidadeParam && modalidade) {
    const optMod = modalidade.querySelector(`option[value="${CSS.escape(modalidadeParam)}"]`);
    if (optMod) {
      modalidade.value = modalidadeParam;
    }
  }

  /* -----------------------------------------------------------
     2. Máscara de Telefone: (XX) XXXXX-XXXX
  ----------------------------------------------------------- */
  if (telefone) {
    telefone.addEventListener("input", (e) => {
      let valor = e.target.value.replace(/\D/g, "");
      if (valor.length > 11) valor = valor.slice(0, 11);

      if (valor.length > 10) {
        valor = valor.replace(/^(\d{2})(\d{5})(\d{4})$/, "($1) $2-$3");
      } else if (valor.length > 6) {
        valor = valor.replace(/^(\d{2})(\d{4})(\d{0,4})$/, "($1) $2-$3");
      } else if (valor.length > 2) {
        valor = valor.replace(/^(\d{2})(\d{0,5})$/, "($1) $2");
      } else if (valor.length > 0) {
        valor = valor.replace(/^(\d*)$/, "($1");
      }

      e.target.value = valor;
    });
  }

  /* -----------------------------------------------------------
     3. Regras de Validação de Campos
  ----------------------------------------------------------- */
  function validar(campo) {
    if (!campo) return false;

    let erro = "";
    const valor = campo.value.trim();

    if (!valor) {
      erro = "Preencha este campo.";
    } else if (campo === nome && valor.length < 2) {
      erro = "Informe seu nome completo.";
    } else if (campo === email && (campo.validity.typeMismatch || !/^[\w\.-]+@[\w\.-]+\.\w+$/.test(valor))) {
      erro = "Informe um e-mail válido.";
    } else if (campo === telefone) {
      const digitos = valor.replace(/\D/g, "");
      if (digitos.length < 10) {
        erro = "Informe um telefone válido com DDD.";
      }
    } else if (campo === dataNascimento) {
      const data = new Date(valor);
      const ano = data.getFullYear();
      const anoAtual = new Date().getFullYear();
      if (isNaN(data.getTime()) || ano < 1900 || ano > anoAtual) {
        erro = "Informe uma data de nascimento válida.";
      }
    } else if (campo === plano && !valor) {
      erro = "Selecione um plano.";
    } else if (campo === modalidade && !valor) {
      erro = "Selecione uma modalidade.";
    } else if (campo === senha && valor.length < 8) {
      erro = "A senha precisa ter pelo menos 8 caracteres.";
    } else if (campo === confirmar && valor !== senha.value) {
      erro = "As senhas não são iguais.";
    }

    campo.setAttribute("aria-invalid", String(Boolean(erro)));

    // Elemento para renderizar mensagem de erro associada
    const idMensagem = `${campo.id.replace("_", "-")}-erro`;
    const mensagemErro = document.getElementById(idMensagem) || document.getElementById(`${campo.id}-erro`);
    if (mensagemErro) {
      mensagemErro.textContent = erro;
    }

    return erro === "";
  }

  // Validação em tempo real ao interagir
  campos.forEach((campo) => {
    const eventoTipo = campo.tagName === "SELECT" ? "change" : "input";

    campo.addEventListener(eventoTipo, () => {
      if (statusCadastro) statusCadastro.textContent = "";

      if (campo.getAttribute("aria-invalid") === "true") {
        validar(campo);
      }

      if (campo === senha && confirmar && confirmar.value) {
        validar(confirmar);
      }
      if (campo === confirmar && confirmar.value) {
        validar(confirmar);
      }
    });

    campo.addEventListener("blur", () => {
      if (campo.value.trim()) {
        validar(campo);
      }
    });
  });

  /* -----------------------------------------------------------
     4. Mostrar e Ocultar Senha (Acessível via aria-controls)
  ----------------------------------------------------------- */
  document.querySelectorAll(".toggle-senha").forEach((botao) => {
    botao.addEventListener("click", () => {
      const campoId = botao.getAttribute("aria-controls");
      const campo = document.getElementById(campoId);

      if (!campo) return;

      const mostrar = campo.type === "password";
      campo.type = mostrar ? "text" : "password";

      botao.setAttribute("aria-pressed", String(mostrar));
      botao.setAttribute("aria-label", mostrar ? "Ocultar senha" : "Mostrar senha");
      botao.textContent = mostrar ? "Ocultar" : "Mostrar";
    });
  });

  /* -----------------------------------------------------------
     5. Envio do Formulário (Validação Completa)
  ----------------------------------------------------------- */
  form.addEventListener("submit", (evento) => {
    evento.preventDefault();

    const resultados = campos.map(validar);
    const primeiroErro = resultados.indexOf(false);

    if (primeiroErro !== -1) {
      if (statusCadastro) {
        statusCadastro.textContent = "Existem campos que precisam ser corrigidos.";
      }
      campos[primeiroErro].focus();
      return;
    }

    if (statusCadastro) {
      statusCadastro.textContent =
        "Dados validados. Este cadastro é demonstrativo: nenhuma conta foi criada ou dado foi salvo.";
    }
  });

  /* -----------------------------------------------------------
     6. Botão Google Demonstrativo
  ----------------------------------------------------------- */
  if (botaoGoogle && statusGoogle) {
    botaoGoogle.addEventListener("click", () => {
      statusGoogle.textContent = "O cadastro com Google ainda não está conectado.";
    });
  }
});
