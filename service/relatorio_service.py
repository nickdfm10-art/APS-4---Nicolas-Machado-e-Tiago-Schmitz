"""Consultas de consolidação (relatórios).

Todos os valores são calculados dinamicamente a partir do banco, com SQLAlchemy
(outer join + group by + count/sum). Nenhum valor é fixado no código.

Observação importante: nos relatórios por categoria e por curso, as inscrições são
primeiro agrupadas em uma subconsulta (uma linha por evento/participante) e só depois
ligadas à tabela principal. Se fizéssemos o JOIN direto com as inscrições, a capacidade
do evento (ou o participante) seria contada várias vezes, inflando os totais.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from model import Evento, Inscricao, Participante


def ocupacao_eventos(db: Session) -> list[dict]:
    # OUTER JOIN: eventos sem nenhuma inscrição também aparecem (total_inscritos = 0).
    consulta = (
        select(
            Evento.id.label("evento_id"),
            Evento.titulo.label("titulo"),
            Evento.capacidade.label("capacidade"),
            func.count(Inscricao.id).label("total_inscritos"),
        )
        .outerjoin(Inscricao, Inscricao.evento_id == Evento.id)
        .group_by(Evento.id, Evento.titulo, Evento.capacidade)
        .order_by(Evento.id)
    )

    resultado = []
    for linha in db.execute(consulta):
        vagas = max(linha.capacidade - linha.total_inscritos, 0)
        # Proteção contra divisão por zero (a capacidade é validada como > 0, mas
        # o cálculo continua seguro mesmo que um dado inválido chegue ao banco).
        percentual = (
            round(linha.total_inscritos / linha.capacidade * 100, 2)
            if linha.capacidade
            else 0.0
        )
        resultado.append(
            {
                "evento_id": linha.evento_id,
                "titulo": linha.titulo,
                "capacidade": linha.capacidade,
                "total_inscritos": linha.total_inscritos,
                "vagas_disponiveis": vagas,
                "percentual_ocupacao": percentual,
            }
        )
    return resultado


def eventos_por_categoria(db: Session) -> list[dict]:
    inscricoes_por_evento = (
        select(
            Inscricao.evento_id.label("evento_id"),
            func.count(Inscricao.id).label("total"),
        )
        .group_by(Inscricao.evento_id)
        .subquery()
    )

    consulta = (
        select(
            Evento.categoria.label("categoria"),
            func.count(Evento.id).label("total_eventos"),
            func.coalesce(func.sum(Evento.capacidade), 0).label("capacidade_total"),
            func.coalesce(func.sum(inscricoes_por_evento.c.total), 0).label("total_inscricoes"),
        )
        .outerjoin(inscricoes_por_evento, inscricoes_por_evento.c.evento_id == Evento.id)
        .group_by(Evento.categoria)
        .order_by(Evento.categoria)
    )

    return [
        {
            "categoria": linha.categoria,
            "total_eventos": linha.total_eventos,
            "capacidade_total": int(linha.capacidade_total),
            "total_inscricoes": int(linha.total_inscricoes),
        }
        for linha in db.execute(consulta)
    ]


def participacao_por_curso(db: Session) -> list[dict]:
    inscricoes_por_participante = (
        select(
            Inscricao.participante_id.label("participante_id"),
            func.count(Inscricao.id).label("total"),
        )
        .group_by(Inscricao.participante_id)
        .subquery()
    )

    consulta = (
        select(
            Participante.curso.label("curso"),
            # Cada participante é uma linha única na subconsulta, então nunca é contado
            # duas vezes, mesmo que tenha várias inscrições.
            func.count(Participante.id).label("total_participantes"),
            func.coalesce(func.sum(inscricoes_por_participante.c.total), 0).label(
                "total_inscricoes"
            ),
        )
        .outerjoin(
            inscricoes_por_participante,
            inscricoes_por_participante.c.participante_id == Participante.id,
        )
        .group_by(Participante.curso)
        .order_by(Participante.curso)
    )

    return [
        {
            "curso": linha.curso,
            "total_participantes": linha.total_participantes,
            "total_inscricoes": int(linha.total_inscricoes),
        }
        for linha in db.execute(consulta)
    ]
