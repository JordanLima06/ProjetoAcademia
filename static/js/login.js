/* Demonstração local: não envia, salva nem autentica credenciais. */
const form = document.getElementById('login-form');
const email = document.getElementById('email');
const senha = document.getElementById('senha');
const statusLogin = document.getElementById('login-status');
const entrar = document.getElementById('entrar');
const mostrar = document.getElementById('mostrar-senha');
// Sem JS, mantém a validação nativa. Com JS, usa mensagens associadas aos campos.
form.noValidate = true;
function validar(campo, erroId) {
  let mensagem = '';
  if (!campo.value.trim()) mensagem = 'Erro: preencha este campo.';
  else if (campo.type === 'email' && campo.validity.typeMismatch) mensagem = 'Erro: use um e-mail no formato nome@exemplo.com.';
  document.getElementById(erroId).textContent = mensagem;
  campo.setAttribute('aria-invalid', mensagem ? 'true' : 'false');
  return mensagem === '';
}
mostrar.addEventListener('click', () => {
  const visivel = senha.type === 'password';

  senha.type = visivel ? 'text' : 'password';

  mostrar.setAttribute('aria-pressed', String(visivel));
});
form.addEventListener('submit', (evento) => {
  evento.preventDefault();
  if (entrar.disabled) return;
  const emailOk = validar(email, 'email-erro');
  const senhaOk = validar(senha, 'senha-erro');
  if (!emailOk || !senhaOk) {
    statusLogin.textContent = 'Confira os campos indicados antes de continuar.';
    (!emailOk ? email : senha).focus();
    return;
  }
  entrar.disabled = true;
  entrar.textContent = 'Verificando…';
  form.setAttribute('aria-busy', 'true');
  statusLogin.textContent = 'Verificando o preenchimento…';
  window.setTimeout(() => {
    statusLogin.textContent = 'Preenchimento válido! Demonstração concluída. Nenhuma conta foi autenticada.';
    entrar.disabled = false;
    entrar.textContent = 'Entrar';
    form.removeAttribute('aria-busy');
  }, 700);
});
const esqueci = document.getElementById('esqueci');
const recuperacao = document.getElementById('recuperacao');
const recuperarEmail = document.getElementById('recuperar-email');
function fecharRecuperacao() {
  recuperacao.hidden = true;
  esqueci.setAttribute('aria-expanded', 'false');
  esqueci.focus();
}
esqueci.addEventListener('click', () => {
  if (!recuperacao.hidden) { fecharRecuperacao(); return; }
  recuperacao.hidden = false;
  esqueci.setAttribute('aria-expanded', 'true');
  recuperarEmail.focus();
});
document.getElementById('cancelar').addEventListener('click', fecharRecuperacao);
recuperacao.addEventListener('keydown', (e) => { if (e.key === 'Escape') fecharRecuperacao(); });
const recuperarForm = document.getElementById('recuperar-form');
recuperarForm.noValidate = true;
recuperarForm.addEventListener('submit', (evento) => {
  evento.preventDefault();
  if (!validar(recuperarEmail, 'recuperar-erro')) { recuperarEmail.focus(); return; }
  document.getElementById('recuperar-status').textContent = 'Solicitação simulada com sucesso. Nenhum e-mail foi enviado.';
});
document.getElementById('google').addEventListener('click', () => {
  document.getElementById('google-status').textContent = 'O acesso com Google ainda não está conectado neste protótipo. Use o formulário com dados fictícios para testar.';
});
for (const [campo, erro] of [[email, 'email-erro'], [senha, 'senha-erro'], [recuperarEmail, 'recuperar-erro']]) {
  campo.addEventListener('input', () => {
    if (campo.getAttribute('aria-invalid') === 'true') validar(campo, erro);
    if (campo === recuperarEmail) document.getElementById('recuperar-status').textContent = '';
    else statusLogin.textContent = '';
  });
}
