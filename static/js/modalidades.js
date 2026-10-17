// Elementos da página
var formBusca = document.getElementById('form-busca');
var campoBusca = document.getElementById('campo-busca');
var botaoLimpar = document.getElementById('btn-limpar');
var botaoVerTodas = document.getElementById('btn-ver-todas');
var statusBusca = document.getElementById('status-busca');
var estadoVazio = document.getElementById('estado-vazio');
var textoVazio = document.getElementById('texto-vazio');
var cartoes = document.querySelectorAll('.card');
var botoesInteresse = document.querySelectorAll('.btn-interesse');

// Deixa o texto "simples" para comparar.
// Ex.: "Jiu-jítsu" e "jiu jitsu" viram os dois "jiujitsu".
function simplificar(texto) {
  return texto
    .toLowerCase()
    .normalize('NFD')                  // separa a letra do acento
    .replace(/[\u0300-\u036f]/g, '')   // tira os acentos (bloco Unicode U+0300 a U+036F)
    .replace(/[^a-z0-9]/g, '');        // tira espaços, hífens e símbolos
}

// Mostra só os cartões que combinam com o que foi digitado
function filtrar() {
  var digitado = campoBusca.value.trim();
  var busca = simplificar(digitado);
  var encontrados = 0;

  for (var i = 0; i < cartoes.length; i++) {
    var cartao = cartoes[i];
    // Procuramos no título, na descrição e na etiqueta do cartão
    var texto = cartao.querySelector('h3').textContent + ' ' +
                cartao.querySelector('.card-texto').textContent + ' ' +
                cartao.querySelector('.tag').textContent;

    var combina = true;
    if (digitado !== '') {
      combina = busca !== '' && simplificar(texto).indexOf(busca) !== -1;
    }

    cartao.hidden = !combina;
    if (combina) {
      encontrados = encontrados + 1;
    }
  }

  atualizarMensagens(digitado, encontrados);
}

// Atualiza a mensagem de resultado e o estado vazio
function atualizarMensagens(digitado, encontrados) {
  if (encontrados === 0) {
    statusBusca.className = 'status status-erro';
    statusBusca.textContent = 'Aviso: nenhuma modalidade encontrada para “' + digitado + '”.';
    textoVazio.textContent = 'Não encontramos “' + digitado + '”. Confira a digitação ou tente outra palavra, como boxe, força ou técnica.';
    estadoVazio.hidden = false;
  } else {
    estadoVazio.hidden = true;
    statusBusca.className = 'status';
    if (digitado === '') {
      statusBusca.textContent = 'Mostrando todas as ' + encontrados + ' modalidades.';
    } else if (encontrados === 1) {
      statusBusca.textContent = '1 modalidade encontrada para “' + digitado + '”.';
    } else {
      statusBusca.textContent = encontrados + ' modalidades encontradas para “' + digitado + '”.';
    }
  }
}

function limparBusca() {
  campoBusca.value = '';
  filtrar();
  campoBusca.focus();
}

// Botão "Tenho interesse": marca, desmarca e avisa
function aoClicarInteresse(evento) {
  var botao = evento.currentTarget;
  var nome = botao.getAttribute('data-modalidade');
  var mensagem = botao.parentNode.querySelector('.mensagem');

  if (botao.getAttribute('aria-pressed') === 'true') {
    botao.setAttribute('aria-pressed', 'false');
    mensagem.textContent = 'Interesse em ' + nome + ' removido.';
  } else {
    botao.setAttribute('aria-pressed', 'true');
    mensagem.textContent = '✓ Você marcou interesse em ' + nome + '. Esta marcação fica só nesta tela e não é salva. Para continuar, faça seu cadastro.';
  }
}

// Liga cada ação ao seu elemento
campoBusca.addEventListener('input', filtrar);
formBusca.addEventListener('submit', function (evento) {
  evento.preventDefault();   // evita recarregar a página
  filtrar();
});
botaoLimpar.addEventListener('click', limparBusca);
botaoVerTodas.addEventListener('click', limparBusca);

for (var i = 0; i < botoesInteresse.length; i++) {
  botoesInteresse[i].addEventListener('click', aoClicarInteresse);
}
