from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, Any

@dataclass
class User:
    """Representa a entidade de Usuário da FightAcademy no PostgreSQL (tabela usuarios)."""
    nome: str
    email: str
    senha: str
    tipo: str = "aluno"
    id: Optional[int] = None
    criado_em: Optional[datetime] = None
    ativo: bool = True

    @property
    def senha_hash(self) -> str:
        """Alias de compatibilidade para código que referencie senha_hash."""
        return self.senha

    @senha_hash.setter
    def senha_hash(self, val: str):
        self.senha = val

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "tipo": self.tipo,
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None
        }

@dataclass
class Aluno:
    """Representa a entidade Aluno vinculada a um Usuário (tabela alunos)."""
    usuario_id: int
    data_nascimento: Optional[date] = None
    telefone: str = ""
    objetivo: Optional[str] = None
    id: Optional[int] = None
    data_cadastro: Optional[date] = None
    usuario: Optional[User] = None

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "data_nascimento": self.data_nascimento.isoformat() if self.data_nascimento else None,
            "telefone": self.telefone,
            "objetivo": self.objetivo,
            "data_cadastro": self.data_cadastro.isoformat() if self.data_cadastro else None,
            "usuario": self.usuario.to_dict() if self.usuario else None
        }
