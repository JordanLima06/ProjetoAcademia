from dataclasses import dataclass, field
from typing import List, Any, Optional

@dataclass
class OpcaoPagamento:
    """Representa uma opção de pagamento e cobrança vinculada a um plano."""
    codigo: str
    nome: str
    tipo_cobranca: str
    valor_cobranca: float
    id: Optional[int] = None
    plano_id: Optional[int] = None
    valor_total_contratado: Optional[float] = None
    quantidade_parcelas: Optional[int] = None
    periodicidade: str = "mensal"
    ativo: bool = True

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def calcular_parcelas_detalhadas(self) -> List[float]:
        """
        Retorna a lista exata com o valor de cada parcela.
        Garante que a soma de todas as parcelas seja estritamente igual ao valor_total_contratado.
        Exemplo: 12 parcelas para R$ 1.399,90 resultam em 11 parcelas de R$ 116,66
        e a 12ª parcela de R$ 116,64.
        """
        if not self.quantidade_parcelas or self.quantidade_parcelas <= 1:
            total = self.valor_total_contratado if self.valor_total_contratado is not None else self.valor_cobranca
            return [round(total, 2)]

        total = self.valor_total_contratado if self.valor_total_contratado is not None else round(self.valor_cobranca * self.quantidade_parcelas, 2)
        n = self.quantidade_parcelas
        parcela_base = self.valor_cobranca if self.valor_cobranca > 0 else round(total / n, 2)

        parcelas = [round(parcela_base, 2)] * (n - 1)
        soma_anteriores = sum(parcelas)
        ultima_parcela = round(total - soma_anteriores, 2)
        parcelas.append(ultima_parcela)
        return parcelas

    def to_dict(self):
        return {
            "id": self.id,
            "plano_id": self.plano_id,
            "codigo": self.codigo,
            "nome": self.nome,
            "tipo_cobranca": self.tipo_cobranca,
            "valor_cobranca": self.valor_cobranca,
            "valor_total_contratado": self.valor_total_contratado,
            "quantidade_parcelas": self.quantidade_parcelas,
            "periodicidade": self.periodicidade,
            "ativo": self.ativo
        }

@dataclass
class Plano:
    """Representa a entidade de Plano de treinamento."""
    slug: str
    nome: str
    preco: float
    beneficios: List[str] = field(default_factory=list)
    id: Optional[int] = None
    descricao: str = ""
    duracao_dias: int = 30
    ativo: bool = True
    opcoes_pagamento: List[OpcaoPagamento] = field(default_factory=list)

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "nome": self.nome,
            "preco": self.preco,
            "descricao": self.descricao,
            "duracao_dias": self.duracao_dias,
            "ativo": self.ativo,
            "beneficios": self.beneficios,
            "opcoes_pagamento": [op.to_dict() for op in self.opcoes_pagamento]
        }

@dataclass
class Modalidade:
    """Representa a entidade de Modalidade esportiva."""
    slug: str
    nome: str
    descricao: str
    imagem: str = ""
    tag: str = ""
    id: Optional[int] = None
    ativo: bool = True

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "nome": self.nome,
            "descricao": self.descricao,
            "imagem": self.imagem,
            "tag": self.tag,
            "ativo": self.ativo
        }
