/**
 * FightAcademy — Validações e Interações da Página de Aula Experimental
 */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("aula-form");
  if (!form) return;

  const nome = document.getElementById("nome");
  const telefone = document.getElementById("telefone");
  const email = document.getElementById("email");
  const modalidadeSelect = document.getElementById("modalidade_id");
  const diaPreferido = document.getElementById("dia_preferido");
  const periodoPreferido = document.getElementById("periodo_preferido");
  const objetivo = document.getElementById("objetivo");
  const statusEl = document.getElementById("aula-status");
  const btnSubmit = document.getElementById("btn-submit");

  /* -----------------------------------------------------------
     1. Pré-seleção da Modalidade a partir da URL (?modalidade= ou ?modalidade_id=)
  ----------------------------------------------------------- */
  function sincronizarModalidadeUrl() {
    if (!modalidadeSelect) return;

    const urlParams = new URLSearchParams(window.location.search);
    const param = (urlParams.get("modalidade") || urlParams.get("modalidade_id") || "").trim().toLowerCase();
    if (!param) return;

    // Busca primeiro por ID (value)
    let opcaoAlvo = modalidadeSelect.querySelector(`option[value="${CSS.escape(param)}"]`);

    // Se não encontrou por ID, busca por Slug (data-slug)
    if (!opcaoAlvo) {
      opcaoAlvo = modalidadeSelect.querySelector(`option[data-slug="${CSS.escape(param)}"]`);
    }

    if (opcaoAlvo) {
      modalidadeSelect.value = opcaoAlvo.value;
      modalidadeSelect.setAttribute("aria-invalid", "false");
      const erroEl = document.getElementById("modalidade-erro");
      if (erroEl) erroEl.textContent = "";
    }
  }

  sincronizarModalidadeUrl();

  /* -----------------------------------------------------------
     2. Máscara de Telefone / WhatsApp: (XX) XXXXX-XXXX
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
     3. Regras de Validação no Cliente
  ----------------------------------------------------------- */
  function validarCampo(campo) {
    if (!campo) return true;

    let erro = "";
    const valor = campo.value.trim();

    if (campo === nome) {
      if (!valor) {
        erro = "Informe seu nome completo.";
      } else if (valor.length < 2) {
        erro = "O nome deve ter pelo menos 2 caracteres.";
      } else if (valor.length > 100) {
        erro = "O nome não pode exceder 100 caracteres.";
      }
    } else if (campo === telefone) {
      const digitos = valor.replace(/\D/g, "");
      if (!valor) {
        erro = "Informe seu número de WhatsApp.";
      } else if (digitos.length < 10) {
        erro = "Informe um WhatsApp válido com DDD (mínimo 10 dígitos).";
      }
    } else if (campo === modalidadeSelect) {
      if (!valor) {
        erro = "Selecione uma modalidade para a aula experimental.";
      }
    } else if (campo === email && valor) {
      if (valor.length > 150) {
        erro = "O e-mail não pode exceder 150 caracteres.";
      } else if (!/^[\w\.-]+@[\w\.-]+\.\w+$/.test(valor)) {
        erro = "Informe um endereço de e-mail válido.";
      }
    } else if (campo === objetivo && valor) {
      if (valor.length > 255) {
        erro = "O objetivo deve ter no máximo 255 caracteres.";
      }
    }

    campo.setAttribute("aria-invalid", String(Boolean(erro)));

    const idMsg = `${campo.id.replace("_", "-")}-erro`;
    const msgEl = document.getElementById(idMsg) || document.getElementById(`${campo.id}-erro`);
    if (msgEl) {
      msgEl.textContent = erro;
    }

    return erro === "";
  }

  const camposObrigatorios = [nome, telefone, modalidadeSelect].filter(Boolean);
  const camposOpcionais = [email, diaPreferido, periodoPreferido, objetivo].filter(Boolean);
  const todosOsCampos = [...camposObrigatorios, ...camposOpcionais];

  todosOsCampos.forEach((campo) => {
    const evento = campo.tagName === "SELECT" ? "change" : "input";
    campo.addEventListener(evento, () => {
      if (statusEl) statusEl.textContent = "";
      if (campo.getAttribute("aria-invalid") === "true") {
        validarCampo(campo);
      }
    });

    campo.addEventListener("blur", () => {
      if (campo.value.trim() || camposObrigatorios.includes(campo)) {
        validarCampo(campo);
      }
    });
  });

  /* -----------------------------------------------------------
     4. Envio do Formulário
  ----------------------------------------------------------- */
  form.addEventListener("submit", (e) => {
    // Verificação de Honeypot anti-spam
    const hp = document.getElementById("website_hp");
    if (hp && hp.value.trim() !== "") {
      e.preventDefault();
      return;
    }

    let formularioValido = true;
    let primeiroInvalido = null;

    todosOsCampos.forEach((campo) => {
      const valido = validarCampo(campo);
      if (!valido && formularioValido) {
        formularioValido = false;
        primeiroInvalido = campo;
      }
    });

    if (!formularioValido) {
      e.preventDefault();
      if (statusEl) {
        statusEl.textContent = "Por favor, corrija os campos destacados antes de prosseguir.";
      }
      if (primeiroInvalido) {
        primeiroInvalido.focus();
      }
      return;
    }

    // Estado visual de envio no botão
    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnSubmit.textContent = "ENVIANDO SOLICITAÇÃO...";
    }
  });
});
