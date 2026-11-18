from dataclasses import dataclass
from typing import List, Any

@dataclass
class Plano:
    """Representa a entidade de Plano de treinamento."""
    slug: str
    nome: str
    preco: float
    beneficios: List[str]

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self):
        return {
            "slug": self.slug,
            "nome": self.nome,
            "preco": self.preco,
            "beneficios": self.beneficios
        }

@dataclass
class Modalidade:
    """Representa a entidade de Modalidade esportiva."""
    slug: str
    nome: str
    descricao: str
    imagem: str
    tag: str

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self):
        return {
            "slug": self.slug,
            "nome": self.nome,
            "descricao": self.descricao,
            "imagem": self.imagem,
            "tag": self.tag
        }
