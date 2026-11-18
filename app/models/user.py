from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    """Representa a entidade de Usuário / Aluno da FightAcademy."""
    nome: str
    email: str
    senha_hash: str
    id: Optional[int] = None
    criado_em: Optional[datetime] = None
    ativo: bool = True

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None
        }
