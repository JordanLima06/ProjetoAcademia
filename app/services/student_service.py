import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.user import User, Aluno
from app.repositories.user_repository import UserRepository
from app.services.enrollment_service import EnrollmentService
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

class StudentService:
    """
    Camada de serviço responsável pelo Dashboard, Perfil e Segurança da Área do Aluno (Fase 4).
    Orquestra as regras sem duplicar lógicas de EnrollmentService ou PaymentService.
    """

    @classmethod
    def obter_dashboard_aluno(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Reúne os dados consolidados para o painel do aluno:
        - Dados cadastrais do aluno e usuário.
        - Matrícula atual (ativa, pendente ou ausente).
        - Modalidades liberadas (apenas liberadas se a matrícula for 'ativa').
        - Resumo financeiro demonstrativo (parcelas pendentes, pagas e próximo vencimento).
        """
        if not user_id:
            return None

        user = UserRepository.find_by_id(user_id)
        aluno = UserRepository.find_aluno_by_user_id(user_id)
        if not user or not aluno:
            return None

        # Matrícula atual vigente (prioriza ativa, depois pendente)
        matricula = EnrollmentService.obter_matricula_atual(aluno.id)

        # Regra obrigatória: Matrícula pendente NÃO libera modalidades.
        # Matrícula ativa libera as modalidades previstas no plano.
        modalidades_liberadas = []
        if matricula and matricula.status == "ativa":
            modalidades_liberadas = matricula.modalidades or []

        # Parcelas e resumo financeiro demonstrativo
        pagamentos = []
        parcelas_pagas = []
        parcelas_pendentes = []
        proximo_vencimento = None
        total_pago = Decimal("0.00")
        total_pendente = Decimal("0.00")

        if matricula:
            pagamentos = PaymentService.listar_pagamentos_por_matricula(matricula.id)
            for p in pagamentos:
                if p.status == "pago":
                    parcelas_pagas.append(p)
                    total_pago += p.valor
                elif p.status == "pendente":
                    parcelas_pendentes.append(p)
                    total_pendente += p.valor

            # Ordena pendentes por vencimento para identificar a próxima
            if parcelas_pendentes:
                pendentes_ordenadas = sorted(parcelas_pendentes, key=lambda x: x.vencimento)
                proximo_vencimento = pendentes_ordenadas[0].vencimento

        return {
            "user": user,
            "aluno": aluno,
            "matricula": matricula,
            "modalidades_liberadas": modalidades_liberadas,
            "pagamentos": pagamentos,
            "parcelas_pagas": parcelas_pagas,
            "parcelas_pendentes": parcelas_pendentes,
            "proximo_vencimento": proximo_vencimento,
            "total_pago": total_pago,
            "total_pendente": total_pendente
        }

    @classmethod
    def normalizar_telefone(cls, raw_telefone: str) -> Tuple[bool, str]:
        """
        Valida e normaliza o número de telefone no servidor.
        Aceita 10 ou 11 dígitos com DDD.
        """
        if not raw_telefone:
            return False, "Telefone é obrigatório."

        digitos = re.sub(r"\D", "", str(raw_telefone).strip())
        if len(digitos) not in (10, 11):
            return False, "Telefone inválido. Informe o DDD e o número com 10 ou 11 dígitos."

        # Não permite DDD com zero inicial (ex: 01, 00)
        if digitos.startswith("0"):
            return False, "DDD inválido."

        if len(digitos) == 11:
            formatado = f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
        else:
            formatado = f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"

        return True, formatado

    @classmethod
    def atualizar_perfil(cls, user_id: int, dados: dict) -> Tuple[bool, str, Optional[Aluno]]:
        """
        Atualiza dados cadastrais do aluno autenticado (telefone, objetivo, data de nascimento).
        O aluno_id é obtido estritamente através do vínculo real no banco (nunca do formulário).
        Não altera permissões, tipo de usuário ou nome nesta etapa.
        """
        aluno = UserRepository.find_aluno_by_user_id(user_id)
        if not aluno:
            return False, "Perfil de aluno não localizado.", None

        # 1. Validação e normalização do telefone
        raw_telefone = dados.get("telefone", "")
        valido_tel, telefone_normalizado = cls.normalizar_telefone(raw_telefone)
        if not valido_tel:
            return False, telefone_normalizado, None

        # 2. Validação da data de nascimento
        raw_data = dados.get("data_nascimento")
        data_nasc: Optional[date] = None
        if raw_data:
            if isinstance(raw_data, (date, datetime)):
                data_nasc = raw_data if isinstance(raw_data, date) else raw_data.date()
            elif isinstance(raw_data, str) and raw_data.strip():
                try:
                    data_nasc = date.fromisoformat(raw_data.strip())
                except ValueError:
                    return False, "Data de nascimento inválida. Use o formato AAAA-MM-DD.", None

        if data_nasc:
            hoje = date.today()
            if data_nasc > hoje:
                return False, "A data de nascimento não pode ser no futuro.", None
            if hoje.year - data_nasc.year > 120:
                return False, "Data de nascimento inválida.", None

        # 3. Objetivo de treino
        objetivo = dados.get("objetivo")
        if objetivo is not None:
            objetivo = str(objetivo).strip() or None

        # 4. Atualização segura no repositório
        sucesso = UserRepository.update_aluno_profile(
            aluno_id=aluno.id,
            telefone=telefone_normalizado,
            objetivo=objetivo,
            data_nascimento=data_nasc
        )

        if sucesso:
            aluno.telefone = telefone_normalizado
            aluno.objetivo = objetivo
            aluno.data_nascimento = data_nasc
            logger.info(f"Perfil do aluno id={aluno.id} atualizado com sucesso.")
            return True, "Perfil atualizado com sucesso!", aluno

        return False, "Falha ao salvar as alterações no banco de dados.", None

    @classmethod
    def alterar_senha(cls, user_id: int, senha_atual: str, nova_senha: str, confirmar_senha: str) -> Tuple[bool, str]:
        """
        Altera a senha do aluno autenticado com validação rigorosa de segurança:
        - Confere senha atual com check_password_hash.
        - Exige nova senha com no mínimo 6 caracteres.
        - Exige confirmação idêntica.
        - Rejeita nova senha idêntica à senha atual.
        - Gera novo hash com generate_password_hash e atualiza no banco.
        """
        user = UserRepository.find_by_id(user_id)
        if not user or not user.ativo:
            return False, "Usuário não localizado ou inativo."

        if not senha_atual:
            return False, "Informe a senha atual."

        if not check_password_hash(user.senha, senha_atual):
            return False, "A senha atual informada está incorreta."

        if not nova_senha or len(nova_senha) < 6:
            return False, "A nova senha deve possuir pelo menos 6 caracteres."

        if nova_senha != confirmar_senha:
            return False, "A confirmação da nova senha não confere."

        if check_password_hash(user.senha, nova_senha):
            return False, "A nova senha deve ser diferente da senha atual."

        novo_hash = generate_password_hash(nova_senha)
        sucesso = UserRepository.update_password(user_id, novo_hash)
        if sucesso:
            user.senha = novo_hash
            logger.info(f"Senha do usuário id={user_id} alterada com sucesso.")
            return True, "Senha alterada com sucesso!"

        return False, "Falha ao atualizar a senha no banco de dados."
