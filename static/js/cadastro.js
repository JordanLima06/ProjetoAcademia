
const form = document.getElementById("cadastro-form");

if (form) {
    const nome = document.getElementById("nome");
    const email = document.getElementById("email");
    const senha = document.getElementById("senha");
    const confirmar = document.getElementById("confirmar");

    const campos = [nome, email, senha, confirmar];
    const statusCadastro = document.getElementById("cadastro-status");
    const botaoEnviar = document.getElementById("cadastrar");
    const botaoGoogle = document.getElementById("google");
    const statusGoogle = document.getElementById("google-status");

    function validar(campo) {
        let erro = "";

        if (!campo.value.trim()) {
            erro = "Preencha este campo.";
        } else if (campo === nome && campo.value.trim().length < 2) {
            erro = "Informe seu nome completo.";
        } else if (campo === email && campo.validity.typeMismatch) {
            erro = "Informe um endereço de e-mail válido.";
        } else if (campo === senha && campo.value.length < 8) {
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

        if (mensagemErro) {
            mensagemErro.textContent = erro;
        }

        return erro === "";
    }

    // Valida novamente quando o usuário altera os campos.
    campos.forEach((campo) => {
        campo.addEventListener("input", () => {
            statusCadastro.textContent = "";

            if (campo.getAttribute("aria-invalid") === "true") {
                validar(campo);
            }

            if (campo === senha && confirmar.value) {
                validar(confirmar);
            }

            if (campo === confirmar && confirmar.value) {
                validar(confirmar);
            }
        });
    });

    // Mostrar ou ocultar as senhas.
    document.querySelectorAll(".toggle-senha").forEach((botao) => {
        botao.addEventListener("click", () => {
            const campoId = botao.getAttribute("aria-controls");
            const campo = document.getElementById(campoId);

            if (!campo) return;

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

    // Validação do formulário demonstrativo.
    form.addEventListener("submit", (evento) => {
        evento.preventDefault();

        const resultados = campos.map(validar);
        const primeiroErro = resultados.indexOf(false);

        if (primeiroErro !== -1) {
            statusCadastro.textContent =
                "Existem campos que precisam ser corrigidos.";

            campos[primeiroErro].focus();
            return;
        }

        statusCadastro.textContent =
            "Dados validados. Este cadastro é demonstrativo: " +
            "nenhuma conta foi criada ou dado foi salvo.";
    });

    // O cadastro com Google ainda não está integrado.
    if (botaoGoogle && statusGoogle) {
        botaoGoogle.addEventListener("click", () => {
            statusGoogle.textContent =
                "O cadastro com Google ainda não está conectado.";
        });
    }
}
