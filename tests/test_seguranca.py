"""Testes de autenticação e autorização da APS 4 (12 cenários do enunciado + extras).

Executar:  pytest -v
"""
import base64
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from database import SessionLocal
from exceptions import NaoAutenticadoError
from model import PerfilUsuario, Usuario
from security import security
from tests.conftest import ARQUIVO_BANCO, SENHA_TESTE, cabecalho_do_usuario, criar_usuario_no_banco

MSG_TOKEN = {"detail": "Não foi possível validar as credenciais."}
MSG_SEM_PERMISSAO = {"detail": "Você não possui permissão para executar esta operação."}
MSG_LOGIN = {"detail": "E-mail ou senha inválidos."}

EVENTO = {"titulo": "Workshop de FastAPI", "descricao": "Aprenda a criar APIs", "data": "2026-12-10",
          "horario": "14:00", "local": "Laboratório 3", "capacidade": 5, "categoria": "Workshop"}
PARTICIPANTE = {"nome": "Maria Souza", "email": "maria@email.com", "curso": "Engenharia de Software"}

# Rotas que exigem apenas AUTENTICAÇÃO (qualquer perfil).
ROTAS_AUTENTICADAS = [
    ("GET", "/eventos", None),
    ("GET", "/eventos/1", None),
    ("GET", "/participantes", None),
    ("GET", "/participantes/1", None),
    ("POST", "/participantes", PARTICIPANTE),
    ("POST", "/eventos/1/inscricoes/1", None),
    ("GET", "/auth/me", None),
]
# Rotas que exigem perfil ADMINISTRADOR.
ROTAS_ADMIN = [
    ("POST", "/eventos", EVENTO),
    ("PUT", "/eventos/1", EVENTO),
    ("DELETE", "/eventos/1", None),
    ("PUT", "/participantes/1", PARTICIPANTE),
    ("DELETE", "/participantes/1", None),
    ("GET", "/eventos/1/inscricoes", None),
    ("DELETE", "/eventos/1/inscricoes/1", None),
    ("GET", "/relatorios/eventos/ocupacao", None),
    ("GET", "/relatorios/eventos/categorias", None),
    ("GET", "/relatorios/participantes/cursos", None),
    ("GET", "/usuarios", None),
    ("PATCH", "/usuarios/1/perfil", {"perfil": "administrador"}),
]


def requisitar(cliente, metodo, caminho, corpo=None, **kwargs):
    return cliente.request(metodo, caminho, json=corpo, **kwargs)


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ===================== 1. cadastro de usuário e validações =====================
def test_cadastro_de_usuario(client_anonimo):
    r = client_anonimo.post("/usuarios", json={
        "nome": "Aluno Exemplo", "email": "aluno@exemplo.com", "senha": "senha_segura"})
    assert r.status_code == 201
    corpo = r.json()
    assert set(corpo) == {"id", "nome", "email", "perfil"}  # sem senha e sem hash
    assert corpo["perfil"] == "usuario"
    assert "senha" not in r.text and "hash" not in r.text


@pytest.mark.parametrize("corpo", [
    {"email": "a@exemplo.com", "senha": "senha_segura"},                      # sem nome
    {"nome": "A", "senha": "senha_segura"},                                    # sem e-mail
    {"nome": "", "email": "a@exemplo.com", "senha": "senha_segura"},          # nome vazio
    {"nome": "A", "email": "nao-e-email", "senha": "senha_segura"},           # e-mail inválido
    {"nome": "A", "email": "a@exemplo.com", "senha": ""},                      # senha vazia
    {"nome": "A", "email": "a@exemplo.com", "senha": "abc1"},                  # curta demais
    {"nome": "A", "email": "a@exemplo.com", "senha": "senhafraca"},           # só letras
    {"nome": "A", "email": "a@exemplo.com", "senha": "12345678"},              # só números
    {"nome": "A", "email": "a@exemplo.com"},                                    # sem senha
])
def test_validacoes_do_cadastro(client_anonimo, corpo):
    r = client_anonimo.post("/usuarios", json=corpo)
    assert r.status_code == 422
    assert client_anonimo.post("/auth/login", json={
        "email": corpo.get("email", "x@x.com"), "senha": corpo.get("senha") or "x"}).status_code == 401


def test_erro_de_validacao_nao_ecoa_a_senha(client_anonimo):
    r = client_anonimo.post("/usuarios", json={
        "nome": "A", "email": "a@exemplo.com", "senha": "senhafraca"})
    assert r.status_code == 422
    assert "senhafraca" not in r.text


def test_nao_e_possivel_se_cadastrar_como_administrador(client_anonimo):
    r = client_anonimo.post("/usuarios", json={
        "nome": "Invasor", "email": "invasor@exemplo.com", "senha": "senha_segura",
        "perfil": "administrador"})
    assert r.status_code == 422
    # e nada foi criado:
    assert client_anonimo.post("/auth/login", json={
        "email": "invasor@exemplo.com", "senha": "senha_segura"}).status_code == 401


# ===================== 2. senha armazenada como hash =====================
def test_senha_e_armazenada_como_hash(client_anonimo):
    senha = "senha_segura"
    r = client_anonimo.post("/usuarios", json={
        "nome": "Aluno", "email": "aluno@exemplo.com", "senha": senha})
    usuario_id = r.json()["id"]

    db = SessionLocal()
    try:
        usuario = db.get(Usuario, usuario_id)
        assert usuario.senha_hash != senha
        assert senha not in usuario.senha_hash
        assert usuario.senha_hash.startswith("$argon2")
        assert security.verificar_senha(senha, usuario.senha_hash)
        assert not security.verificar_senha("outra_senha1", usuario.senha_hash)
    finally:
        db.close()

    # leitura direta do arquivo .db, sem passar pela aplicação
    con = sqlite3.connect(ARQUIVO_BANCO)
    gravado = con.execute("SELECT senha_hash FROM usuarios WHERE id=?", (usuario_id,)).fetchone()[0]
    con.close()
    assert gravado.startswith("$argon2") and senha not in gravado


def test_mesma_senha_gera_hashes_diferentes():
    assert security.gerar_hash_senha("Senha123!") != security.gerar_hash_senha("Senha123!")


# ===================== 3. e-mail duplicado =====================
def test_email_duplicado(client_anonimo):
    corpo = {"nome": "Aluno", "email": "aluno@exemplo.com", "senha": "senha_segura"}
    assert client_anonimo.post("/usuarios", json=corpo).status_code == 201
    r = client_anonimo.post("/usuarios", json=corpo)
    assert r.status_code == 409
    assert r.json() == {"detail": "Já existe um usuário cadastrado com este e-mail."}
    # a comparação ignora maiúsculas/minúsculas
    assert client_anonimo.post("/usuarios", json={**corpo, "email": "ALUNO@exemplo.com"}).status_code == 409


# ===================== 4. login válido =====================
def test_login_valido_retorna_token_jwt(client_anonimo):
    usuario_id = criar_usuario_no_banco("ana@exemplo.com")
    r = client_anonimo.post("/auth/login", json={"email": "ana@exemplo.com", "senha": SENHA_TESTE})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["token_type"] == "bearer"
    assert security.validar_token(corpo["access_token"]) == usuario_id
    # o e-mail do login não diferencia maiúsculas/minúsculas
    assert client_anonimo.post("/auth/login", json={
        "email": "ANA@Exemplo.com", "senha": SENHA_TESTE}).status_code == 200


def test_token_tem_sub_iat_e_exp_e_nao_carrega_perfil():
    usuario_id = criar_usuario_no_banco("ana@exemplo.com", PerfilUsuario.administrador)
    token = security.criar_token(usuario_id)
    payload = jwt.decode(token, security.obter_chave_secreta(), algorithms=["HS256"])
    assert set(payload) == {"sub", "iat", "exp"}
    assert payload["sub"] == str(usuario_id)
    assert payload["exp"] - payload["iat"] == 30 * 60  # validade configurada (30 min)


def test_fluxo_completo_cadastro_login_me(client_anonimo):
    client_anonimo.post("/usuarios", json={
        "nome": "Aluno Exemplo", "email": "aluno@exemplo.com", "senha": "senha_segura"})
    token = client_anonimo.post("/auth/login", json={
        "email": "aluno@exemplo.com", "senha": "senha_segura"}).json()["access_token"]
    r = client_anonimo.get("/auth/me", headers=bearer(token))
    assert r.status_code == 200
    assert r.json()["email"] == "aluno@exemplo.com" and r.json()["perfil"] == "usuario"


# ===================== 5. login inválido =====================
def test_login_invalido_nao_revela_se_foi_o_email_ou_a_senha(client_anonimo):
    criar_usuario_no_banco("ana@exemplo.com")
    senha_errada = client_anonimo.post("/auth/login", json={"email": "ana@exemplo.com", "senha": "errada123"})
    email_inexistente = client_anonimo.post("/auth/login", json={"email": "ninguem@exemplo.com", "senha": SENHA_TESTE})
    assert senha_errada.status_code == email_inexistente.status_code == 401
    assert senha_errada.json() == email_inexistente.json() == MSG_LOGIN


# ===================== 6. rota protegida sem token =====================
@pytest.mark.parametrize("metodo,caminho,corpo", ROTAS_AUTENTICADAS + ROTAS_ADMIN)
def test_acesso_sem_token_retorna_401(client_anonimo, metodo, caminho, corpo):
    r = requisitar(client_anonimo, metodo, caminho, corpo)
    assert r.status_code == 401
    assert r.json() == MSG_TOKEN
    assert r.headers["www-authenticate"] == "Bearer"


def test_rotas_publicas_nao_exigem_token(client_anonimo):
    assert client_anonimo.post("/usuarios", json={
        "nome": "A", "email": "a@exemplo.com", "senha": "senha_segura"}).status_code == 201
    assert client_anonimo.post("/auth/login", json={
        "email": "a@exemplo.com", "senha": "senha_segura"}).status_code == 200
    assert client_anonimo.get("/docs").status_code == 200
    assert client_anonimo.get("/openapi.json").status_code == 200


# ===================== 7. token válido =====================
def test_acesso_com_token_valido(client_usuario):
    assert client_usuario.get("/eventos").status_code == 200
    assert client_usuario.get("/participantes").status_code == 200
    assert client_usuario.get("/auth/me").status_code == 200


# ===================== 8. token inválido, adulterado, expirado =====================
def _adulterar_payload(token: str, **alteracoes) -> str:
    cabecalho, payload, assinatura = token.split(".")
    dados = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    dados.update(alteracoes)
    novo = base64.urlsafe_b64encode(json.dumps(dados).encode()).rstrip(b"=").decode()
    return f"{cabecalho}.{novo}.{assinatura}"  # assinatura antiga: não confere mais


def _tokens_invalidos(usuario_id: int) -> dict:
    agora = datetime.now(timezone.utc)
    valido = security.criar_token(usuario_id)
    return {
        "lixo": "abc.def.ghi",
        "texto_qualquer": "isto-nao-e-um-jwt",
        "adulterado": _adulterar_payload(valido, sub="999"),
        "expirado": security.criar_token(usuario_id, expira_em=timedelta(minutes=-1)),
        "outra_chave": jwt.encode(
            {"sub": str(usuario_id), "iat": agora, "exp": agora + timedelta(minutes=5)},
            "uma-outra-chave-secreta-totalmente-diferente-123456", algorithm="HS256"),
        "sem_exp": jwt.encode({"sub": str(usuario_id)}, security.obter_chave_secreta(), algorithm="HS256"),
        "sem_sub": jwt.encode({"exp": agora + timedelta(minutes=5)}, security.obter_chave_secreta(), algorithm="HS256"),
    }


@pytest.mark.parametrize("tipo", ["lixo", "texto_qualquer", "adulterado", "expirado",
                                   "outra_chave", "sem_exp", "sem_sub"])
def test_tokens_invalidos_sao_rejeitados(client_anonimo, tipo):
    usuario_id = criar_usuario_no_banco("ana@exemplo.com", PerfilUsuario.administrador)
    token = _tokens_invalidos(usuario_id)[tipo]
    r = client_anonimo.get("/eventos", headers=bearer(token))
    assert r.status_code == 401
    assert r.json() == MSG_TOKEN


def test_esquema_de_autorizacao_diferente_de_bearer_e_rejeitado(client_anonimo):
    usuario_id = criar_usuario_no_banco("ana@exemplo.com")
    token = security.criar_token(usuario_id)
    assert client_anonimo.get("/eventos", headers={"Authorization": f"Basic {token}"}).status_code == 401
    assert client_anonimo.get("/eventos", headers={"Authorization": token}).status_code == 401


def test_token_de_usuario_inexistente_e_rejeitado(client_anonimo):
    token = security.criar_token(99999)
    assert client_anonimo.get("/eventos", headers=bearer(token)).status_code == 401


def test_validar_token_levanta_excecao_para_lixo():
    with pytest.raises(NaoAutenticadoError):
        security.validar_token("abc.def.ghi")


# ===================== 9. usuário comum x operações administrativas =====================
@pytest.mark.parametrize("metodo,caminho,corpo", ROTAS_ADMIN)
def test_usuario_comum_recebe_403_nas_rotas_administrativas(client_usuario, metodo, caminho, corpo):
    r = requisitar(client_usuario, metodo, caminho, corpo)
    assert r.status_code == 403
    assert r.json() == MSG_SEM_PERMISSAO


@pytest.mark.parametrize("metodo,caminho,corpo", ROTAS_AUTENTICADAS)
def test_usuario_comum_acessa_as_rotas_autenticadas(client_usuario, metodo, caminho, corpo):
    r = requisitar(client_usuario, metodo, caminho, corpo)
    assert r.status_code not in (401, 403)


def test_perfil_enviado_no_token_nao_concede_privilegios(client_anonimo):
    """A permissão é checada no servidor, com o perfil do BANCO, não com o que vem no token."""
    usuario_id = criar_usuario_no_banco("comum@exemplo.com", PerfilUsuario.usuario)
    agora = datetime.now(timezone.utc)
    token_forjado = jwt.encode(
        {"sub": str(usuario_id), "iat": agora, "exp": agora + timedelta(minutes=5),
         "perfil": "administrador"},
        security.obter_chave_secreta(), algorithm="HS256")
    r = client_anonimo.post("/eventos", json=EVENTO, headers=bearer(token_forjado))
    assert r.status_code == 403


def test_perfil_enviado_em_cabecalho_ou_query_e_ignorado(client_usuario):
    r = client_usuario.post("/eventos?perfil=administrador", json=EVENTO,
                            headers={"X-Perfil": "administrador"})
    assert r.status_code == 403


# ===================== 10. administrador executa operações administrativas =====================
def test_administrador_executa_operacoes_administrativas(client):
    r = client.post("/eventos", json=EVENTO)
    assert r.status_code == 201
    evento_id = r.json()["id"]
    assert client.put(f"/eventos/{evento_id}", json={**EVENTO, "capacidade": 9}).status_code == 200
    assert client.get("/relatorios/eventos/ocupacao").status_code == 200
    assert client.get("/relatorios/eventos/categorias").status_code == 200
    assert client.get("/relatorios/participantes/cursos").status_code == 200
    assert client.get(f"/eventos/{evento_id}/inscricoes").status_code == 200
    assert client.delete(f"/eventos/{evento_id}").status_code == 204


# ===================== 11. /auth/me =====================
def test_auth_me_retorna_o_usuario_do_token(client_anonimo):
    id_a = criar_usuario_no_banco("a@exemplo.com", nome="Pessoa A")
    id_b = criar_usuario_no_banco("b@exemplo.com", PerfilUsuario.administrador, nome="Pessoa B")
    r = client_anonimo.get("/auth/me", headers=cabecalho_do_usuario(id_a))
    assert r.status_code == 200
    assert r.json() == {"id": id_a, "nome": "Pessoa A", "email": "a@exemplo.com", "perfil": "usuario"}
    r = client_anonimo.get("/auth/me", headers=cabecalho_do_usuario(id_b))
    assert r.json()["perfil"] == "administrador"
    # um id enviado pelo cliente é ignorado: o usuário vem sempre do token
    r = client_anonimo.get(f"/auth/me?id={id_b}&usuario_id={id_b}", headers=cabecalho_do_usuario(id_a))
    assert r.json()["id"] == id_a


def test_respostas_nunca_expoem_senha_nem_hash(client, client_usuario):
    textos = [
        client.get("/usuarios").text,
        client.get("/auth/me").text,
        client_usuario.get("/auth/me").text,
    ]
    for texto in textos:
        assert "senha" not in texto.lower()
        assert "argon2" not in texto
    assert "senha_hash" not in client.get("/openapi.json").text


# ===================== 12. funcionalidades da APS 3 sob as regras de acesso =====================
def test_fluxo_da_aps3_como_usuario_comum_e_administrador(client, client_usuario):
    evento_id = client.post("/eventos", json=EVENTO).json()["id"]  # admin cria

    # usuário comum: consulta eventos, cadastra participante e se inscreve
    assert client_usuario.get(f"/eventos/{evento_id}").status_code == 200
    participante_id = client_usuario.post("/participantes", json=PARTICIPANTE).json()["id"]
    assert client_usuario.post(f"/eventos/{evento_id}/inscricoes/{participante_id}").status_code == 201
    # regras de negócio da APS 3 continuam valendo
    r = client_usuario.post(f"/eventos/{evento_id}/inscricoes/{participante_id}")
    assert r.status_code == 409 and r.json() == {"detail": "Participante já está inscrito neste evento."}
    assert client_usuario.post("/eventos/999/inscricoes/1").status_code == 404

    # usuário comum não vê relatórios nem a lista de inscritos
    assert client_usuario.get("/relatorios/eventos/ocupacao").status_code == 403
    assert client_usuario.get(f"/eventos/{evento_id}/inscricoes").status_code == 403

    # administrador enxerga tudo, com os números consolidados corretos
    inscritos = client.get(f"/eventos/{evento_id}/inscricoes").json()
    assert len(inscritos) == 1 and inscritos[0]["participante"]["email"] == "maria@email.com"
    ocupacao = client.get("/relatorios/eventos/ocupacao").json()
    assert ocupacao[0]["total_inscritos"] == 1 and ocupacao[0]["percentual_ocupacao"] == 20.0
    assert client.get("/relatorios/eventos/categorias").json()[0]["total_inscricoes"] == 1
    assert client.get("/relatorios/participantes/cursos").json()[0]["total_participantes"] == 1


# ===================== extras: gestão de perfis =====================
def test_administrador_promove_usuario_e_vale_na_proxima_requisicao(client, client_usuario):
    usuario_id = client_usuario.get("/auth/me").json()["id"]
    assert client_usuario.post("/eventos", json=EVENTO).status_code == 403

    r = client.patch(f"/usuarios/{usuario_id}/perfil", json={"perfil": "administrador"})
    assert r.status_code == 200 and r.json()["perfil"] == "administrador"

    # mesmo token de antes: o perfil novo vale imediatamente (lido do banco)
    assert client_usuario.post("/eventos", json=EVENTO).status_code == 201


def test_nao_e_possivel_remover_o_ultimo_administrador(client):
    admin_id = client.get("/auth/me").json()["id"]
    r = client.patch(f"/usuarios/{admin_id}/perfil", json={"perfil": "usuario"})
    assert r.status_code == 409
    assert client.get("/auth/me").json()["perfil"] == "administrador"


def test_alterar_perfil_valida_dados(client):
    assert client.patch("/usuarios/999/perfil", json={"perfil": "administrador"}).status_code == 404
    assert client.patch("/usuarios/1/perfil", json={"perfil": "super"}).status_code == 422


# ===================== configuração da chave secreta =====================
def test_sem_chave_secreta_a_configuracao_falha(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        security.validar_configuracao()


def test_chave_secreta_curta_e_rejeitada(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "curta")
    with pytest.raises(RuntimeError):
        security.obter_chave_secreta()


def test_expiracao_invalida_e_rejeitada(monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "abc")
    with pytest.raises(RuntimeError):
        security.obter_minutos_expiracao()
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "0")
    with pytest.raises(RuntimeError):
        security.obter_minutos_expiracao()
