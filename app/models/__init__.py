from app.models.user import User, Aluno
from app.models.academy import Plano, Modalidade, OpcaoPagamento
from app.models.trial_class import SolicitacaoAulaExperimental
from app.models.enrollment import Matricula, MatriculaModalidade
from app.models.payment import Pagamento

__all__ = [
    "User",
    "Aluno",
    "Plano",
    "Modalidade",
    "OpcaoPagamento",
    "SolicitacaoAulaExperimental",
    "Matricula",
    "MatriculaModalidade",
    "Pagamento"
]
