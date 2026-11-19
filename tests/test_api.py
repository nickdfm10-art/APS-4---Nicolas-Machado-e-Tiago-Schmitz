"""Testes automatizados herdados da APS 3 (agora executados como ADMINISTRADOR).

Executar:  pytest -v
"""
import sqlite3

from tests.conftest import ARQUIVO_BANCO


# ---------------------------------------------------------------- auxiliares
def novo_evento(client, **extra):
    corpo = {
        "titulo": "Workshop de FastAPI",
        "descricao": "Aprenda a criar APIs modernas",
        "data": "2026-12-10",
        "horario": "14:00",
        "local": "Laboratório 3",
        "capacidade": 2,
        "categoria": "Workshop",
    }
    corpo.update(extra)
    return client.post("/eventos", json=corpo)


def novo_participante(client, **extra):
    corpo = {"nome": "Maria Souza", "email": "maria@email.com", "curso": "Engenharia de Software"}
    corpo.update(extra)
    return client.post("/participantes", json=corpo)


def inscrever(client, evento_id, participante_id):
    return client.post(f"/eventos/{evento_id}/inscricoes/{participante_id}")


# ------------------------------------------- 1. cadastro e consulta de eventos
def test_cadastrar_e_consultar_evento(client):
    r = novo_evento(client)
    assert r.status_code == 201
    evento = r.json()
    assert evento["id"] == 1
    assert evento["titulo"] == "Workshop de FastAPI"
    assert evento["categoria"] == "Workshop"

    assert client.get("/eventos/1").json()["titulo"] == "Workshop de FastAPI"
    lista = client.get("/eventos")
    assert lista.status_code == 200 and len(lista.json()) == 1


def test_consultar_evento_inexistente(client):
    r = client.get("/eventos/999")
    assert r.status_code == 404
    assert r.json() == {"detail": "Evento não encontrado."}


# ------------------------------------------- 2. cadastro e consulta de participantes
def test_cadastrar_e_consultar_participante(client):
    r = novo_participante(client)
    assert r.status_code == 201
    assert r.json()["id"] == 1
    assert client.get("/participantes/1").json()["email"] == "maria@email.com"
    assert len(client.get("/participantes").json()) == 1


def test_consultar_participante_inexistente(client):
    r = client.get("/participantes/999")
    assert r.status_code == 404
    assert r.json() == {"detail": "Participante não encontrado."}


# ------------------------------------------- validações (herdadas da APS 2)
def test_validacoes_de_evento(client):
    assert novo_evento(client, titulo="").status_code == 422
    assert novo_evento(client, titulo="   ").status_code == 422
    assert novo_evento(client, capacidade=0).status_code == 422
    assert novo_evento(client, capacidade=-5).status_code == 422
    assert novo_evento(client, data="2026-02-30").status_code == 422
    assert novo_evento(client, horario="25:99").status_code == 422
    assert novo_evento(client, categoria="Festa").status_code == 422
    assert client.post("/eventos", json={"titulo": "Só o título"}).status_code == 422
    assert client.get("/eventos").json() == []  # nada inválido foi salvo


def test_validacoes_de_participante(client):
    assert novo_participante(client, nome="").status_code == 422
    assert novo_participante(client, email="isto-nao-e-email").status_code == 422
    assert novo_participante(client, curso="  ").status_code == 422
    assert client.post("/participantes", json={"nome": "Sem e-mail"}).status_code == 422


def test_email_duplicado_retorna_409(client):
    assert novo_participante(client).status_code == 201
    r = novo_participante(client, nome="Outra Pessoa")
    assert r.status_code == 409
    assert r.json() == {"detail": "Já existe um participante cadastrado com este e-mail."}
    # a duplicidade ignora maiúsculas/minúsculas
    assert novo_participante(client, email="MARIA@EMAIL.COM").status_code == 409


def test_atualizar_participante_para_email_de_outro_retorna_409(client):
    novo_participante(client)
    novo_participante(client, nome="João", email="joao@email.com")
    r = client.put("/participantes/2", json={
        "nome": "João", "email": "maria@email.com", "curso": "Engenharia de Software"})
    assert r.status_code == 409
    # manter o próprio e-mail é permitido
    r = client.put("/participantes/2", json={
        "nome": "João Silva", "email": "joao@email.com", "curso": "Engenharia de Software"})
    assert r.status_code == 200 and r.json()["nome"] == "João Silva"


# ------------------------------------------- 3. atualização e exclusão
def test_atualizar_e_excluir_evento(client):
    novo_evento(client)
    r = client.put("/eventos/1", json={
        "titulo": "Novo título", "descricao": "Nova descrição", "data": "2026-12-11",
        "horario": "09:30", "local": "Sala 1", "capacidade": 10, "categoria": "Palestra"})
    assert r.status_code == 200
    assert r.json()["titulo"] == "Novo título" and r.json()["categoria"] == "Palestra"

    assert client.delete("/eventos/1").status_code == 204
    assert client.get("/eventos/1").status_code == 404
    assert client.delete("/eventos/1").status_code == 404


def test_atualizar_e_excluir_participante(client):
    novo_participante(client)
    r = client.put("/participantes/1", json={
        "nome": "Maria S.", "email": "maria@email.com", "curso": "Sistemas de Informação"})
    assert r.status_code == 200 and r.json()["curso"] == "Sistemas de Informação"
    assert client.delete("/participantes/1").status_code == 204
    assert client.get("/participantes/1").status_code == 404


# ------------------------------------------- 4 a 7. inscrições
def test_inscrever_participante(client):
    novo_evento(client)
    novo_participante(client)
    r = inscrever(client, 1, 1)
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["evento_id"] == 1 and corpo["participante_id"] == 1
    assert "data_inscricao" in corpo

    inscritos = client.get("/eventos/1/inscricoes")
    assert inscritos.status_code == 200
    assert len(inscritos.json()) == 1
    assert inscritos.json()[0]["participante"]["email"] == "maria@email.com"


def test_inscricao_duplicada(client):
    novo_evento(client)
    novo_participante(client)
    inscrever(client, 1, 1)
    r = inscrever(client, 1, 1)
    assert r.status_code == 409
    assert r.json() == {"detail": "Participante já está inscrito neste evento."}
    assert len(client.get("/eventos/1/inscricoes").json()) == 1


def test_inscricao_em_evento_ou_participante_inexistente(client):
    novo_evento(client)
    novo_participante(client)
    r = inscrever(client, 999, 1)
    assert r.status_code == 404 and r.json() == {"detail": "Evento não encontrado."}
    r = inscrever(client, 1, 999)
    assert r.status_code == 404 and r.json() == {"detail": "Participante não encontrado."}
    assert client.get("/eventos/999/inscricoes").status_code == 404


def test_inscricao_sem_vagas(client):
    novo_evento(client, capacidade=1)
    novo_participante(client)
    novo_participante(client, nome="João", email="joao@email.com")
    assert inscrever(client, 1, 1).status_code == 201
    r = inscrever(client, 1, 2)
    assert r.status_code == 409
    assert r.json() == {"detail": "Não existem vagas disponíveis para este evento."}


# ------------------------------------------- integridade
def test_nao_exclui_evento_nem_participante_com_inscricoes(client):
    novo_evento(client)
    novo_participante(client)
    inscrever(client, 1, 1)

    assert client.delete("/eventos/1").status_code == 409
    assert client.delete("/participantes/1").status_code == 409
    assert client.get("/eventos/1").status_code == 200  # continuam existindo

    # depois de cancelar a inscrição, a exclusão é permitida
    assert client.delete("/eventos/1/inscricoes/1").status_code == 204
    assert client.delete("/eventos/1").status_code == 204
    assert client.delete("/participantes/1").status_code == 204


def test_cancelar_inscricao_inexistente(client):
    novo_evento(client)
    novo_participante(client)
    r = client.delete("/eventos/1/inscricoes/1")
    assert r.status_code == 404 and r.json() == {"detail": "Inscrição não encontrada."}


def test_capacidade_nao_pode_ficar_menor_que_inscritos(client):
    novo_evento(client, capacidade=2)
    novo_participante(client)
    novo_participante(client, nome="João", email="joao@email.com")
    inscrever(client, 1, 1)
    inscrever(client, 1, 2)
    r = client.put("/eventos/1", json={
        "titulo": "Workshop", "descricao": "x", "data": "2026-12-10", "horario": "14:00",
        "local": "Lab", "capacidade": 1, "categoria": "Workshop"})
    assert r.status_code == 409


# ------------------------------------------- 8. persistência após reinicialização
def test_dados_persistem_apos_reinicializacao(client):
    from database import engine
    from main import app
    from fastapi.testclient import TestClient

    novo_evento(client)
    novo_participante(client)
    inscrever(client, 1, 1)

    # "Desliga" a aplicação: fecha todas as conexões do pool.
    engine.dispose()

    # O arquivo .db tem os dados (leitura direta, sem passar pela API)...
    con = sqlite3.connect(ARQUIVO_BANCO)
    assert con.execute("SELECT COUNT(*) FROM eventos").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM participantes").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM inscricoes").fetchone()[0] == 1
    con.close()

    # ...e uma "nova execução" da aplicação enxerga os mesmos dados.
    cabecalho = {"Authorization": client.headers["Authorization"]}
    with TestClient(app, headers=cabecalho) as novo_client:
        assert novo_client.get("/eventos/1").json()["titulo"] == "Workshop de FastAPI"
        assert len(novo_client.get("/eventos/1/inscricoes").json()) == 1


# ------------------------------------------- 9 a 12. relatórios
def test_relatorios_sem_registros_retornam_lista_vazia(client):
    for rota in ("/relatorios/eventos/ocupacao",
                 "/relatorios/eventos/categorias",
                 "/relatorios/participantes/cursos"):
        r = client.get(rota)
        assert r.status_code == 200 and r.json() == []


def _montar_cenario(client):
    """3 eventos, 3 participantes, 3 inscrições."""
    novo_evento(client, titulo="Workshop A", capacidade=2, categoria="Workshop")     # id 1
    novo_evento(client, titulo="Workshop B", capacidade=3, categoria="Workshop")     # id 2
    novo_evento(client, titulo="Palestra C", capacidade=100, categoria="Palestra")   # id 3 (sem inscritos)
    novo_participante(client, nome="Ana", email="ana@email.com", curso="Engenharia de Software")             # 1
    novo_participante(client, nome="Bia", email="bia@email.com", curso="Engenharia de Software")             # 2
    novo_participante(client, nome="Caio", email="caio@email.com", curso="Análise e Desenvolvimento de Sistemas")  # 3
    inscrever(client, 1, 1)
    inscrever(client, 1, 2)
    inscrever(client, 2, 1)


def test_relatorio_de_ocupacao(client):
    _montar_cenario(client)
    r = client.get("/relatorios/eventos/ocupacao")
    assert r.status_code == 200
    assert r.json() == [
        {"evento_id": 1, "titulo": "Workshop A", "capacidade": 2, "total_inscritos": 2,
         "vagas_disponiveis": 0, "percentual_ocupacao": 100.0},
        {"evento_id": 2, "titulo": "Workshop B", "capacidade": 3, "total_inscritos": 1,
         "vagas_disponiveis": 2, "percentual_ocupacao": 33.33},
        {"evento_id": 3, "titulo": "Palestra C", "capacidade": 100, "total_inscritos": 0,
         "vagas_disponiveis": 100, "percentual_ocupacao": 0.0},
    ]


def test_relatorio_por_categoria(client):
    _montar_cenario(client)
    r = client.get("/relatorios/eventos/categorias")
    assert r.status_code == 200
    assert r.json() == [
        {"categoria": "Palestra", "total_eventos": 1, "capacidade_total": 100, "total_inscricoes": 0},
        {"categoria": "Workshop", "total_eventos": 2, "capacidade_total": 5, "total_inscricoes": 3},
    ]


def test_relatorio_por_curso_nao_conta_participante_duas_vezes(client):
    _montar_cenario(client)  # Ana tem 2 inscrições; mesmo assim conta 1 participante
    r = client.get("/relatorios/participantes/cursos")
    assert r.status_code == 200
    assert r.json() == [
        {"curso": "Análise e Desenvolvimento de Sistemas", "total_participantes": 1, "total_inscricoes": 0},
        {"curso": "Engenharia de Software", "total_participantes": 2, "total_inscricoes": 3},
    ]


def test_relatorios_acompanham_alteracoes_nos_dados(client):
    _montar_cenario(client)

    # nova inscrição -> ocupação, categoria e curso mudam
    inscrever(client, 2, 3)
    ocupacao = {e["evento_id"]: e for e in client.get("/relatorios/eventos/ocupacao").json()}
    assert ocupacao[2]["total_inscritos"] == 2 and ocupacao[2]["percentual_ocupacao"] == 66.67
    workshop = next(c for c in client.get("/relatorios/eventos/categorias").json()
                    if c["categoria"] == "Workshop")
    assert workshop["total_inscricoes"] == 4
    ads = next(c for c in client.get("/relatorios/participantes/cursos").json()
               if c["curso"].startswith("Análise"))
    assert ads["total_inscricoes"] == 1

    # cancelar inscrição -> volta a diminuir
    client.delete("/eventos/2/inscricoes/3")
    ocupacao = {e["evento_id"]: e for e in client.get("/relatorios/eventos/ocupacao").json()}
    assert ocupacao[2]["total_inscritos"] == 1

    # atualizar capacidade -> percentual recalculado
    client.put("/eventos/2", json={
        "titulo": "Workshop B", "descricao": "x", "data": "2026-12-10", "horario": "14:00",
        "local": "Lab", "capacidade": 4, "categoria": "Workshop"})
    ocupacao = {e["evento_id"]: e for e in client.get("/relatorios/eventos/ocupacao").json()}
    assert ocupacao[2]["vagas_disponiveis"] == 3 and ocupacao[2]["percentual_ocupacao"] == 25.0

    # excluir evento sem inscrições -> some do relatório
    client.delete("/eventos/3")
    ids = [e["evento_id"] for e in client.get("/relatorios/eventos/ocupacao").json()]
    assert ids == [1, 2]
    categorias = [c["categoria"] for c in client.get("/relatorios/eventos/categorias").json()]
    assert categorias == ["Workshop"]
