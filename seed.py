"""Popula o banco com dados de exemplo para demonstrar a API e os relatórios.

Uso:  python seed.py
Só insere dados se o banco estiver vazio (para não duplicar registros).
"""
from datetime import date, time

from database import SessionLocal, criar_tabelas
from schema.evento_schema import EventoCreate
from schema.participante_schema import ParticipanteCreate
from service import evento_service, inscricao_service, participante_service

EVENTOS = [
    ("Introdução à Inteligência Artificial", "Panorama de IA e aplicações.", date(2026, 12, 3), time(19, 0), "Auditório Central", 100, "Palestra"),
    ("Workshop de Python", "Prática de Python do zero.", date(2026, 12, 5), time(14, 0), "Laboratório 2", 3, "Workshop"),
    ("Workshop de FastAPI", "Criando APIs com FastAPI.", date(2026, 12, 6), time(14, 0), "Laboratório 3", 5, "Workshop"),
    ("Minicurso de SQL", "Consultas e agregações em SQL.", date(2026, 12, 9), time(9, 0), "Laboratório 1", 20, "Minicurso"),
    ("Seminário de Engenharia de Software", "Boas práticas e arquitetura.", date(2026, 12, 12), time(10, 0), "Sala 201", 50, "Seminário"),
    ("Maratona de Programação", "Competição em equipes.", date(2026, 12, 15), time(8, 0), "Laboratório 4", 30, "Competição"),
]

PARTICIPANTES = [
    ("Ana Lima", "ana.lima@email.com", "Engenharia de Software"),
    ("Bruno Costa", "bruno.costa@email.com", "Engenharia de Software"),
    ("Carla Dias", "carla.dias@email.com", "Engenharia de Software"),
    ("Diego Alves", "diego.alves@email.com", "Análise e Desenvolvimento de Sistemas"),
    ("Elisa Rocha", "elisa.rocha@email.com", "Análise e Desenvolvimento de Sistemas"),
    ("Felipe Nunes", "felipe.nunes@email.com", "Ciência da Computação"),
    ("Gabriela Melo", "gabriela.melo@email.com", "Ciência da Computação"),
    ("Henrique Paz", "henrique.paz@email.com", "Sistemas de Informação"),
]

# (índice do evento, índices dos participantes inscritos) — começando em 0
INSCRICOES = {
    0: [0, 1, 2, 3, 4, 5],
    1: [0, 3, 5],          # Workshop de Python: capacidade 3 -> lotado
    2: [0, 1, 6],
    3: [2, 4, 7],
    4: [1, 2, 3, 5, 6],
    # índice 5 (Maratona) fica sem inscrições, de propósito
}


def main() -> None:
    criar_tabelas()
    db = SessionLocal()
    try:
        if evento_service.listar(db) or participante_service.listar(db):
            print("O banco já possui dados; nada foi inserido.")
            return

        eventos = [
            evento_service.criar(db, EventoCreate(
                titulo=t, descricao=d, data=dt, horario=h, local=l, capacidade=c, categoria=cat))
            for t, d, dt, h, l, c, cat in EVENTOS
        ]
        participantes = [
            participante_service.criar(db, ParticipanteCreate(nome=n, email=e, curso=c))
            for n, e, c in PARTICIPANTES
        ]
        for i_evento, lista in INSCRICOES.items():
            for i_part in lista:
                inscricao_service.inscrever(db, eventos[i_evento].id, participantes[i_part].id)

        print(f"{len(eventos)} eventos, {len(participantes)} participantes e "
              f"{sum(len(v) for v in INSCRICOES.values())} inscrições inseridos.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
