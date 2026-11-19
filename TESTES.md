# Roteiro de testes — Swagger (`/docs`)

## Preparação

1. Configure a chave secreta (`.env`, ver README seção 4) e comece com banco limpo (apague `eventos.db` com a API parada).
2. Crie o administrador: `python criar_admin.py` (ex.: `admin@exemplo.com` / `admin_segura1`).
3. (Opcional) `python seed.py` para ter eventos e participantes.
4. `uvicorn main:app --reload` e abra http://127.0.0.1:8000/docs.

**Como autenticar no Swagger:** faça `POST /auth/login`, copie o `access_token`, clique em **Authorize** (cadeado), cole só o token e confirme. Para trocar de usuário: **Authorize → Logout** e repita. Tire um *print* de cada requisição e resposta.

## Os 12 cenários do enunciado

| # | Cenário | Como fazer | Resultado esperado |
|---|---|---|---|
| 1 | Cadastro de usuário | `POST /usuarios` `{"nome":"Aluno Exemplo","email":"aluno@exemplo.com","senha":"senha_segura"}` | `201` com `id`, `nome`, `email`, `perfil: "usuario"`, **sem senha nem hash** |
| 2 | Senha armazenada como hash | Com a API parada ou ligada, rode: `python -c "import sqlite3; print(sqlite3.connect('eventos.db').execute('select id,email,perfil,senha_hash from usuarios').fetchall())"` | `senha_hash` começa com `$argon2` e **não contém** `senha_segura` |
| 3 | E-mail duplicado | Repetir o `POST /usuarios` do cenário 1 | `409` `{"detail":"Já existe um usuário cadastrado com este e-mail."}` |
| 4 | Login válido | `POST /auth/login` `{"email":"aluno@exemplo.com","senha":"senha_segura"}` | `200` `{"access_token":"...","token_type":"bearer"}` |
| 5 | Login inválido | (a) senha errada; (b) e-mail inexistente | `401` nos dois, **mesma** mensagem `{"detail":"E-mail ou senha inválidos."}` |
| 6 | Rota protegida sem token | Sem Authorize (ou Logout): `GET /eventos` | `401` `{"detail":"Não foi possível validar as credenciais."}` |
| 7 | Token válido | Authorize com o token do cenário 4: `GET /eventos` | `200` |
| 8a | Token inválido | Authorize com `abc.def.ghi` e `GET /eventos` | `401` mesma mensagem |
| 8b | Token adulterado | Troque um caractere do **meio** do token válido e `GET /eventos` | `401` |
| 8c | Token expirado | Gere um expirado: `python -c "from datetime import timedelta; from security.security import criar_token; print(criar_token(1, timedelta(minutes=-1)))"` (ou defina `ACCESS_TOKEN_EXPIRE_MINUTES=1`, faça login e espere 1 min) | `401` |
| 9 | Usuário comum em operação administrativa | Token do usuário comum: `POST /eventos` (corpo válido) | `403` `{"detail":"Você não possui permissão para executar esta operação."}` |
| 10 | Administrador em operação administrativa | Login como `admin@exemplo.com` e `POST /eventos` | `201` com o evento criado |
| 11 | `/auth/me` | `GET /auth/me` com cada token (comum e admin) | `200` com os dados **do dono do token** (`perfil` `usuario` / `administrador`), sem senha/hash |
| 12 | APS 3 sob as regras de acesso | Veja a tabela abaixo | conforme a tabela |

### Cenário 12 — funcionalidades e relatórios da APS 3

| Ator | Requisição | Esperado |
|---|---|---|
| Usuário comum | `GET /eventos`, `GET /participantes` | `200` |
| Usuário comum | `POST /participantes` | `201` |
| Usuário comum | `POST /eventos/{id}/inscricoes/{participante_id}` | `201` |
| Usuário comum | repetir a inscrição | `409` `Participante já está inscrito neste evento.` |
| Usuário comum | `POST /eventos/999/inscricoes/1` | `404` `Evento não encontrado.` |
| Usuário comum | `GET /relatorios/eventos/ocupacao` | `403` |
| Usuário comum | `GET /eventos/{id}/inscricoes` | `403` |
| Administrador | `GET /eventos/{id}/inscricoes` | `200` com os inscritos |
| Administrador | `GET /relatorios/eventos/ocupacao`, `/relatorios/eventos/categorias`, `/relatorios/participantes/cursos` | `200` com os valores consolidados (com o `seed.py`, os mesmos da APS 3) |
| Administrador | `PUT /eventos/{id}`, `DELETE /eventos/{id}` | `200` / `204` (ou `409` se houver inscrições) |

## Evidências de que a segurança é verificada no servidor

- **Cadastro como administrador:** `POST /usuarios` com `"perfil":"administrador"` no corpo → `422` e o usuário **não** é criado.
- **Perfil só vale se estiver no banco:** o token não carrega o perfil. Promova o usuário comum com `PATCH /usuarios/{id}/perfil` (como administrador) e repita `POST /eventos` com o **mesmo token** dele → passa de `403` para `201`.
- **Último administrador:** `PATCH /usuarios/{id_do_unico_admin}/perfil` com `{"perfil":"usuario"}` → `409`.
- **Senha/hash nunca aparecem:** confira as respostas de `POST /usuarios`, `GET /usuarios`, `GET /auth/me` e os erros `422` (que também não devolvem o valor enviado).

## Testes automatizados

```bash
pip install -r requirements-dev.txt
pytest -v
```
