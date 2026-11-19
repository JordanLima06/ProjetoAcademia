import re
from datetime import datetime, date
from typing import Tuple, Optional, Dict, Any
from app.models.trial_class import SolicitacaoAulaExperimental
from app.repositories.trial_repository import TrialRepository
from app.services.academy_service import AcademyService

class TrialService:
    """Regras de negócio e validações para o módulo de Aula Experimental."""

    EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

    @classmethod
    def solicitar_aula(cls, dados: Dict[str, Any]) -> Tuple[bool, str, Optional[SolicitacaoAulaExperimental]]:
        """
        Valida os dados recebidos no formulário e persiste a solicitação no PostgreSQL.
        Retorna (sucesso, mensagem, solicitacao_criada).
        """
        nome = (dados.get("nome") or "").strip()
        telefone = (dados.get("telefone") or "").strip()
        email = (dados.get("email") or "").strip()
        modalidade_raw = dados.get("modalidade_id")
        dia_raw = (dados.get("dia_preferido") or "").strip()
        periodo_raw = (dados.get("periodo_preferido") or "").strip().lower()
        objetivo = (dados.get("objetivo") or "").strip()

        # 1. Validação de Nome (Obrigatório, máx 100 caracteres)
        if not nome or len(nome) < 2:
            return False, "Informe seu nome completo (mínimo 2 caracteres).", None
        if len(nome) > 100:
            return False, "O nome não pode exceder 100 caracteres.", None

        # 2. Validação de WhatsApp / Telefone (Obrigatório, máx 20 caracteres)
        digitos_telefone = re.sub(r"\D", "", telefone)
        if not digitos_telefone or len(digitos_telefone) < 10:
            return False, "Informe um número de WhatsApp válido com DDD (mínimo 10 dígitos).", None
        if len(digitos_telefone) > 15 or len(telefone) > 20:
            return False, "O número de telefone informado é inválido.", None

        # 3. Validação de Modalidade (Obrigatório no formulário e validação de FK ativa)
        if not modalidade_raw:
            return False, "Selecione a modalidade desejada para a aula experimental.", None

        modalidade_id: Optional[int] = None
        try:
            modalidade_id = int(modalidade_raw)
        except (ValueError, TypeError):
            # Suporte amigável caso venha slug textual
            mod = AcademyService.get_modality(str(modalidade_raw))
            if mod and mod.id:
                modalidade_id = mod.id
            else:
                return False, "Modalidade inválida ou não encontrada.", None

        modalidade_existente = AcademyService.get_modality_by_id(modalidade_id)
        if not modalidade_existente:
            return False, "A modalidade selecionada não existe ou não está disponível.", None

        # 4. Validação de E-mail (Opcional, máx 150 caracteres)
        email_limpo: Optional[str] = None
        if email:
            if len(email) > 150:
                return False, "O e-mail não pode exceder 150 caracteres.", None
            if not cls.EMAIL_REGEX.match(email):
                return False, "Informe um endereço de e-mail válido.", None
            email_limpo = email.lower()

        # 5. Validação de Dia Preferido (Opcional, tipo DATE)
        dia_data: Optional[date] = None
        if dia_raw:
            try:
                dia_data = datetime.strptime(dia_raw, "%Y-%m-%d").date()
            except ValueError:
                return False, "Informe uma data válida no formato ano-mês-dia.", None

        # 6. Validação de Período Preferido (Opcional, restrito ao CHECK da tabela)
        periodo_limpo: Optional[str] = None
        if periodo_raw:
            if periodo_raw not in SolicitacaoAulaExperimental.PERIODOS_VALIDOS:
                return False, "Período inválido. Escolha entre manhã, tarde ou noite.", None
            periodo_limpo = periodo_raw

        # 7. Validação de Objetivo (Opcional, máx 255 caracteres)
        objetivo_limpo: Optional[str] = None
        if objetivo:
            if len(objetivo) > 255:
                return False, "O objetivo pessoal deve ter no máximo 255 caracteres.", None
            objetivo_limpo = objetivo

        # 8. Criação da Entidade com status inicial 'nova'
        solicitacao = SolicitacaoAulaExperimental(
            nome=nome,
            telefone=telefone,
            email=email_limpo,
            modalidade_id=modalidade_id,
            dia_preferido=dia_data,
            periodo_preferido=periodo_limpo,
            objetivo=objetivo_limpo,
            status="nova"
        )

        try:
            solicitacao_salva = TrialRepository.create(solicitacao)
            return True, "Solicitação de aula experimental enviada com sucesso! Nossa equipe entrará em contato pelo WhatsApp.", solicitacao_salva
        except Exception as e:
            return False, "Não foi possível registrar sua solicitação no momento. Tente novamente mais tarde.", None
