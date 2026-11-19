import logging
from typing import List, Optional, Tuple
from datetime import date, timedelta
from decimal import Decimal
from flask import current_app, has_app_context
from app.db import get_db_connection
from app.models.enrollment import Matricula, MatriculaModalidade
from app.models.academy import Plano, Modalidade, OpcaoPagamento
from app.models.payment import Pagamento
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.modality_repository import ModalityRepository
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

class EnrollmentService:
    """
    Camada de serviço responsável pelo gerenciamento de matrículas e contratação demonstrativa.
    Garante:
    - Validação de regras comerciais e integridade relacional.
    - Impedimento de duplicidade de matrícula ativa vigente por aluno.
    - Atomicidade transacional PostgreSQL: Matrícula + Modalidades Liberadas + Parcelas Demonstrativas.
    - Rollback integral em qualquer falha de gravação.
    """

    @classmethod
    def _is_testing(cls) -> bool:
        return has_app_context() and bool(current_app.config.get("TESTING"))

    @classmethod
    def contratar_plano_demonstrativo(
        cls,
        aluno_id: int,
        plano_slug: str,
        opcao_pagamento_id: int,
        forma_pagamento: str
    ) -> Tuple[bool, Optional[Matricula], str]:
        """
        Orquestra a contratação demonstrativa de um plano por um aluno em transação atômica única.

        Retorna: (sucesso: bool, matricula: Optional[Matricula], mensagem: str)
        """
        if not aluno_id:
            return False, None, "Aluno não informado ou não autenticado."

        # 1. Regra de matrícula única vigente: impede contratação simultânea de matrícula ativa ou pendente
        matricula_existente = EnrollmentRepository.find_current_by_aluno_id(aluno_id)
        if matricula_existente and matricula_existente.status in ("ativa", "pendente") and matricula_existente.data_fim >= date.today():
            status_desc = "ativa" if matricula_existente.status == "ativa" else "pendente de pagamento"
            return (
                False,
                None,
                f"Você já possui uma matrícula {status_desc} e vigente. "
                "Para contratar outro plano, consulte sua matrícula atual."
            )

        # 2. Validação do plano
        plano = PlanRepository.get_by_slug(plano_slug)
        if not plano or not plano.ativo:
            return False, None, "Plano selecionado não encontrado ou inativo."

        # 3. Validação da opção de pagamento e cobrança
        opcao = PlanRepository.get_payment_option_by_id(opcao_pagamento_id)
        if not opcao or not opcao.ativo or (opcao.plano_id is not None and opcao.plano_id != plano.id):
            return False, None, "Opção de pagamento inválida para o plano selecionado."

        # 4. Validação da forma de pagamento perante as constraints do banco
        if not PaymentService.validar_forma_pagamento(forma_pagamento):
            return (
                False,
                None,
                f"Forma de pagamento '{forma_pagamento}' não permitida. "
                f"Valores válidos: {', '.join(Pagamento.FORMAS_PAGAMENTO_PERMITIDAS)}"
            )

        # 5. Recuperação das modalidades vinculadas ao plano
        modalidades = ModalityRepository.get_by_plan_id(plano.id, only_active=True)
        modality_ids = [m.id for m in modalidades if m.id is not None]

        # 6. Cálculo das datas de vigência
        data_inicio = date.today()
        duracao_dias = plano.duracao_dias or 30
        data_fim = data_inicio + timedelta(days=duracao_dias)

        # 7. Definição dos valores comerciais com precisão Decimal
        if opcao.valor_total_contratado is not None:
            valor_total = Decimal(str(opcao.valor_total_contratado)).quantize(Decimal("0.01"))
        else:
            qtd = opcao.quantidade_parcelas or 1
            valor_total = (Decimal(str(opcao.valor_cobranca)) * Decimal(qtd)).quantize(Decimal("0.01"))

        valor_cobranca = Decimal(str(opcao.valor_cobranca)).quantize(Decimal("0.01"))
        quantidade_parcelas = opcao.quantidade_parcelas or 1
        tipo_cobranca = opcao.tipo_cobranca

        matricula = Matricula(
            aluno_id=aluno_id,
            plano_id=plano.id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            status="ativa",
            opcao_pagamento_id=opcao.id,
            tipo_cobranca=tipo_cobranca,
            valor_cobranca=valor_cobranca,
            valor_total_contratado=valor_total,
            quantidade_parcelas=quantidade_parcelas
        )

        # 8. Execução Transacional Atômica
        conn = get_db_connection()
        if not conn:
            if cls._is_testing():
                # Modo de teste isolado em memória
                return cls._contratar_em_memoria_teste(
                    matricula=matricula,
                    plano=plano,
                    modalidades=modalidades,
                    modality_ids=modality_ids,
                    valor_total=valor_total,
                    quantidade_parcelas=quantidade_parcelas,
                    forma_pagamento=forma_pagamento,
                    data_inicio=data_inicio,
                    valor_cobranca=valor_cobranca
                )
            logger.error("Falha de conexão com PostgreSQL durante contratação de matrícula.")
            return False, None, "Erro ao conectar com o banco de dados. Tente novamente mais tarde."

        try:
            with conn:  # Context manager atômico do PostgreSQL (COMMIT automático ou ROLLBACK na exceção)
                with conn.cursor() as cursor:
                    # Bloqueio transacional por linha de aluno (SELECT ... FOR UPDATE) contra requisições simultâneas
                    existente_lock = EnrollmentRepository.lock_student_and_check_existing_matricula(cursor, aluno_id)
                    if existente_lock and existente_lock.status in ("ativa", "pendente") and existente_lock.data_fim >= date.today():
                        raise ValueError(f"O aluno já possui uma matrícula {existente_lock.status} vigente.")

                    # Passo 1: Inserir matrícula e associar modalidades liberadas (matricula_id, plano_id, modalidade_id)
                    matricula_salva = EnrollmentRepository.create_transactional(cursor, matricula, modality_ids)

                    # Passo 2: Gerar parcelas demonstrativas (status='pendente', pagamento_data=None)
                    parcelas = PaymentService.gerar_parcelas_demonstrativas(
                        matricula_id=matricula_salva.id,
                        valor_total=valor_total,
                        quantidade_parcelas=quantidade_parcelas,
                        forma_pagamento=forma_pagamento,
                        data_base_vencimento=data_inicio,
                        valor_cobranca=valor_cobranca
                    )

                    # Passo 3: Gravar as parcelas individuais na tabela pagamentos dentro da mesma transação
                    PaymentService.salvar_parcelas_transacional(cursor, parcelas)

            matricula_salva.plano = plano
            matricula_salva.modalidades = modalidades
            logger.info(
                f"Matrícula id={matricula_salva.id} contratada com sucesso para aluno_id={aluno_id} "
                f"no plano '{plano.nome}' ({len(parcelas)} parcelas demonstrativas registradas)."
            )
            return True, matricula_salva, "Matrícula contratada com sucesso em modo demonstrativo!"

        except Exception as e:
            logger.error(f"Erro transacional ao contratar matrícula para aluno {aluno_id}: {e}", exc_info=True)
            return False, None, f"Falha ao registrar matrícula e pagamentos: {str(e)}"

    @classmethod
    def _contratar_em_memoria_teste(
        cls,
        matricula: Matricula,
        plano: Plano,
        modalidades: List[Modalidade],
        modality_ids: List[int],
        valor_total: Decimal,
        quantidade_parcelas: int,
        forma_pagamento: str,
        data_inicio: date,
        valor_cobranca: Decimal
    ) -> Tuple[bool, Matricula, str]:
        """Auxiliar de teste para simulação transacional segura quando sem banco ativo."""
        mat_id = EnrollmentRepository._TEST_ID_SEQ
        EnrollmentRepository._TEST_ID_SEQ += 1
        matricula.id = mat_id
        EnrollmentRepository._TEST_MATRICULAS[mat_id] = matricula

        # Modalidades
        vms = [
            MatriculaModalidade(matricula_id=mat_id, plano_id=matricula.plano_id, modalidade_id=mid)
            for mid in modality_ids
        ]
        EnrollmentRepository._TEST_MATRICULA_MODALIDADES[mat_id] = vms

        # Pagamentos
        parcelas = PaymentService.gerar_parcelas_demonstrativas(
            matricula_id=mat_id,
            valor_total=valor_total,
            quantidade_parcelas=quantidade_parcelas,
            forma_pagamento=forma_pagamento,
            data_base_vencimento=data_inicio,
            valor_cobranca=valor_cobranca
        )
        for p in parcelas:
            p.id = PaymentRepository._TEST_ID_SEQ
            PaymentRepository._TEST_ID_SEQ += 1
            PaymentRepository._TEST_PAGAMENTOS[p.id] = p

        matricula.plano = plano
        matricula.modalidades = modalidades
        return True, matricula, "Matrícula contratada com sucesso em modo demonstrativo!"

    @classmethod
    def obter_matricula_ativa(cls, aluno_id: int) -> Optional[Matricula]:
        """
        Recupera a matrícula ativa vigente do aluno com plano e modalidades hidratados.
        """
        if not aluno_id:
            return None

        matricula = EnrollmentRepository.find_active_by_aluno_id(aluno_id)
        if matricula:
            matricula.plano = PlanRepository.get_by_id(matricula.plano_id)
            if not matricula.modalidades:
                matricula.modalidades = EnrollmentRepository.get_modalities_by_matricula_id(matricula.id)
        return matricula

    @classmethod
    def obter_matricula_atual(cls, aluno_id: int) -> Optional[Matricula]:
        """
        Recupera a matrícula atual do aluno (priorizando 'ativa' e depois 'pendente')
        com plano e modalidades liberadas hidratados.
        """
        if not aluno_id:
            return None

        matricula = EnrollmentRepository.find_current_by_aluno_id(aluno_id)
        if matricula:
            matricula.plano = PlanRepository.get_by_id(matricula.plano_id)
            if not matricula.modalidades:
                matricula.modalidades = EnrollmentRepository.get_modalities_by_matricula_id(matricula.id)
        return matricula

    @classmethod
    def obter_historico_matriculas(cls, aluno_id: int) -> List[Matricula]:
        """Retorna o histórico completo de matrículas do aluno."""
        if not aluno_id:
            return []

        matriculas = EnrollmentRepository.list_by_aluno_id(aluno_id)
        for m in matriculas:
            m.plano = PlanRepository.get_by_id(m.plano_id)
            if not m.modalidades:
                m.modalidades = EnrollmentRepository.get_modalities_by_matricula_id(m.id)
        return matriculas

    @classmethod
    def obter_detalhes_matricula(cls, aluno_id: int, matricula_id: int) -> Optional[Matricula]:
        """
        Recupera uma matrícula específica garantindo que pertença ao aluno solicitante.
        """
        matricula = EnrollmentRepository.find_by_id(matricula_id)
        if not matricula or matricula.aluno_id != aluno_id:
            return None

        matricula.plano = PlanRepository.get_by_id(matricula.plano_id)
        if not matricula.modalidades:
            matricula.modalidades = EnrollmentRepository.get_modalities_by_matricula_id(matricula.id)
        return matricula

    @classmethod
    def cancelar_matricula(cls, aluno_id: int, matricula_id: int) -> Tuple[bool, str]:
        """
        Cancela uma matrícula (ativa ou pendente) pertencente ao aluno e atualiza
        atomicamente todas as suas parcelas pendentes para 'cancelado'.
        """
        matricula = EnrollmentRepository.find_by_id(matricula_id)
        if not matricula or matricula.aluno_id != aluno_id:
            return False, "Matrícula não encontrada ou não pertence a este aluno."

        if matricula.status not in ("ativa", "pendente"):
            return False, f"Apenas matrículas com status 'ativa' ou 'pendente' podem ser canceladas. Status atual: {matricula.status}"

        conn = get_db_connection()
        if not conn:
            if cls._is_testing():
                if matricula_id in EnrollmentRepository._TEST_MATRICULAS:
                    EnrollmentRepository._TEST_MATRICULAS[matricula_id].status = "cancelada"
                PaymentRepository.cancel_pending_by_matricula_id(None, matricula_id)
                return True, "Matrícula e parcelas pendentes canceladas com sucesso."
            return False, "Erro ao conectar com o banco de dados."

        try:
            with conn:
                with conn.cursor() as cursor:
                    # 1. Atualizar status da matrícula para 'cancelada'
                    cursor.execute(
                        "UPDATE matriculas SET status = %s WHERE id = %s",
                        ("cancelada", matricula_id)
                    )
                    # 2. Cancelar atomicamente todas as parcelas pendentes vinculadas
                    PaymentRepository.cancel_pending_by_matricula_id(cursor, matricula_id)

            logger.info(f"Matrícula id={matricula_id} e parcelas pendentes canceladas com sucesso pelo aluno_id={aluno_id}.")
            return True, "Matrícula e parcelas pendentes canceladas com sucesso."
        except Exception as e:
            logger.error(f"Erro transacional ao cancelar matrícula {matricula_id}: {e}", exc_info=True)
            return False, f"Falha ao cancelar matrícula e pagamentos: {str(e)}"
