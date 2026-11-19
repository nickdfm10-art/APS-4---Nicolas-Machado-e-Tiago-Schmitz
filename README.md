# API de Eventos Acadêmicos — APS 4 (Autenticação e Segurança)

Equipe: Nicolas Machado e Tiago Schmitz

## 1. Descrição do projeto

API RESTful para gerenciar **eventos acadêmicos**, **participantes** e **inscrições**, com persistência em **SQLite + SQLAlchemy** e relatórios consolidados (APS 3).

Nesta versão (APS 4) a API ganhou **segurança**:

- cadastro de **usuários** com senha protegida por **hash Argon2** (biblioteca `pwdlib`);
- **login por e-mail e senha** que devolve um **token JWT** (biblioteca `PyJWT`, assinatura HS256, com prazo de validade);
- **proteção de rotas** por autenticação (token no cabeçalho `Authorization: Bearer ...`), centralizada em dependências do FastAPI;
- **autorização por perfil** (`administrador` e `usuario`), validada sempre no servidor;
- rota `GET /auth/me` com os dados do usuário autenticado.

Tecnologias: Python 3.10+, FastAPI, SQLAlchemy 2.x, SQLite, Pydantic v2, pwdlib (Argon2), PyJWT, python-dotenv, Uvicorn.

## 2. Instalação e execução

```bash
# 1) clonar e entrar na pasta
git clone <url-do-repositorio>
cd <pasta-do-projeto>

# 2) ambiente virtual
python -m venv venv
venv\Scripts\activate            # Windows (PowerShell: .\venv\Scripts\Activate)
source venv/bin/activate         # Linux / macOS

# 3) dependências
pip install -r requirements.txt

# 4) configurar a chave secreta (seção 4)
copy .env.example .env           # Windows   (Linux/macOS: cp .env.example .env)
#    edite o .env e coloque uma chave gerada

# 5) criar o primeiro administrador (seção 6)
python criar_admin.py

# 6) subir a API
uvicorn main:app --reload
```

- Swagger: http://127.0.0.1:8000/docs
- A API **não inicia** se `JWT_SECRET_KEY` estiver ausente ou fraca (mensagem de erro explica como corrigir).
- Dados de exemplo (eventos, participantes, inscrições): `python seed.py`.
- Se você já tinha um `eventos.db` da APS 3, ele continua válido: a tabela `usuarios` é criada automaticamente ao iniciar.

## 3. Estrutura do projeto

```
├── main.py                    # app, routers e tratadores de erro (401/403/404/409/422/500)
├── database.py                # conexão SQLite, sessões e criação das tabelas
├── exceptions.py              # exceções de negócio (401, 403, 404, 409)
├── criar_admin.py             # procedimento controlado para criar o 1º administrador
├── seed.py                    # dados de exemplo (eventos/participantes/inscrições)
├── controller/                # ROTAS HTTP
│   ├── auth_controller.py     #   /auth/login, /auth/me
│   ├── usuario_controller.py  #   /usuarios
│   ├── evento_controller.py, participante_controller.py,
│   ├── inscricao_controller.py, relatorio_controller.py
│   └── respostas.py           #   respostas 401/403 para a documentação
├── model/                     # ENTIDADES (SQLAlchemy): evento, participante, inscricao, usuario
├── schema/                    # VALIDAÇÃO e respostas (Pydantic): ..., usuario_schema, auth_schema
├── service/                   # REGRAS DE NEGÓCIO: ..., usuario_service, auth_service
├── security/                  # SEGURANÇA
│   ├── security.py            #   hash de senha, criação/validação de JWT, configuração
│   └── dependencies.py        #   get_usuario_atual, exigir_perfil, apenas_administrador
├── tests/                     # testes automatizados (pytest)
├── requirements.txt / requirements-dev.txt / .env.example
├── TESTES.md                  # roteiro de testes no Swagger
└── README.md
```

| Camada | Responsabilidade |
|---|---|
| Controller | Rotas; apenas declara o que exige (`Depends`). Sem lógica de autenticação. |
| Model | Tabelas (inclui `usuarios`). |
| Schema | Validação de entrada e formato das respostas (nunca inclui senha/hash). |
| Service | Regras de negócio: cadastro de usuário, verificação de credenciais, perfis. |
| Security | Hash, JWT e dependências que identificam o usuário e checam o perfil. |
| Database | Conexão e sessões. |

## 4. Chave secreta (JWT)

A chave que assina os tokens **não está no código**. Ela vem da variável de ambiente `JWT_SECRET_KEY`, que pode ser definida no sistema ou em um arquivo `.env` na raiz (arquivo **ignorado pelo Git**; só o modelo `.env.example` é versionado).

1. Gere uma chave aleatória:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```
2. Copie `.env.example` para `.env` e cole a chave:
   ```
   JWT_SECRET_KEY=<chave gerada>
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```
3. Alternativa sem arquivo (PowerShell): `$env:JWT_SECRET_KEY="<chave>"`; (Linux/macOS): `export JWT_SECRET_KEY="<chave>"`.

Regras: mínimo de 32 caracteres; variáveis do sistema têm prioridade sobre o `.env`; nunca publique uma chave real. Trocar a chave invalida todos os tokens já emitidos.

## 5. Segurança: o que foi implementado

| Requisito | Como foi feito |
|---|---|
| Hash de senha | `pwdlib` com **Argon2** (hash com salt aleatório). Só o hash é gravado em `usuarios.senha_hash`. Nenhum algoritmo foi implementado à mão; não há MD5/SHA-1. |
| Verificação | `verificar_senha()` usa a função de verificação da biblioteca. |
| Senha nunca exposta | Os schemas de resposta não têm campo de senha/hash; erros 422 também **não devolvem o valor enviado** (evita ecoar a senha). |
| Política de senha | 8 a 128 caracteres, com pelo menos uma letra e um número ou símbolo. |
| Login | `POST /auth/login`; falha → 401 com a **mesma mensagem** para e-mail inexistente e senha errada, e com tempo de resposta equivalente. |
| JWT | HS256; claims `sub` (id do usuário), `iat` e `exp`; validade configurável (padrão 30 min). A validação confere assinatura, algoritmo e expiração e exige `sub` e `exp`. |
| Perfil fora do token | O token **não carrega o perfil**: ele é lido do banco a cada requisição. Assim o cliente não consegue "escolher" privilégios e mudanças de perfil valem na hora. |
| Perfil no cadastro | `POST /usuarios` não aceita `perfil` (qualquer campo extra gera 422); todo cadastro público é `usuario`. |
| Autorização | Dependências do FastAPI (`get_usuario_atual`, `apenas_administrador`) aplicadas nas rotas; sem permissão → **403**. |

## 6. Como criar usuários, administradores e obter tokens

**Usuário comum (público):** `POST /usuarios`
```json
{"nome": "Aluno Exemplo", "email": "aluno@exemplo.com", "senha": "senha_segura"}
```
Resposta `201`: `{"id": 1, "nome": "Aluno Exemplo", "email": "aluno@exemplo.com", "perfil": "usuario"}`

**Primeiro administrador (procedimento controlado):** não existe rota pública para criar administradores. Rode no terminal do servidor:
```bash
python criar_admin.py
```
O script pede nome, e-mail e senha (a senha não aparece na tela nem fica em arquivos). Se o e-mail já existir como usuário comum, ele é promovido. Depois, um administrador pode promover outros pela API: `PATCH /usuarios/{id}/perfil` com `{"perfil": "administrador"}` (o último administrador não pode ser rebaixado).

**Obter o token:** `POST /auth/login`
```json
{"email": "aluno@exemplo.com", "senha": "senha_segura"}
```
Resposta `200`: `{"access_token": "<jwt>", "token_type": "bearer"}`

**Usar o token:** envie `Authorization: Bearer <jwt>`. No Swagger, clique em **Authorize** e cole apenas o `access_token`.

## 7. Rotas: públicas e protegidas

| Método | Rota | Acesso |
|---|---|---|
| POST | `/usuarios` | **Público** |
| POST | `/auth/login` | **Público** |
| GET | `/docs`, `/openapi.json` | Público |
| GET | `/auth/me` | Autenticado |
| GET | `/eventos`, `/eventos/{id}` | Autenticado (qualquer perfil) |
| POST / PUT / DELETE | `/eventos`, `/eventos/{id}` | **Administrador** |
| GET | `/participantes`, `/participantes/{id}` | Autenticado (qualquer perfil) |
| POST | `/participantes` | Autenticado (qualquer perfil) |
| PUT / DELETE | `/participantes/{id}` | **Administrador** |
| POST | `/eventos/{evento_id}/inscricoes/{participante_id}` | Autenticado (qualquer perfil) |
| GET | `/eventos/{evento_id}/inscricoes` | **Administrador** |
| DELETE | `/eventos/{evento_id}/inscricoes/{participante_id}` | **Administrador** |
| GET | `/relatorios/eventos/ocupacao` | **Administrador** |
| GET | `/relatorios/eventos/categorias` | **Administrador** |
| GET | `/relatorios/participantes/cursos` | **Administrador** |
| GET | `/usuarios` | **Administrador** |
| PATCH | `/usuarios/{id}/perfil` | **Administrador** |

## 8. Perfis e permissões

| Operação | administrador | usuario |
|---|:---:|:---:|
| Cadastrar-se e fazer login | ✔ | ✔ |
| Consultar os próprios dados (`/auth/me`) | ✔ | ✔ |
| Consultar eventos e participantes | ✔ | ✔ |
| Cadastrar participante | ✔ | ✔ |
| Inscrever participante em evento | ✔ | ✔ |
| Cadastrar / atualizar / excluir **eventos** | ✔ | ✘ (403) |
| Atualizar / excluir **participantes** | ✔ | ✘ (403) |
| Consultar inscritos de um evento e cancelar inscrição | ✔ | ✘ (403) |
| Relatórios consolidados | ✔ | ✘ (403) |
| Listar usuários e alterar perfis | ✔ | ✘ (403) |

**Regras adicionais definidas pela equipe:**
- Todas as rotas, exceto cadastro de usuário e login, exigem token.
- Um usuário comum cadastra participantes para poder inscrevê-los; alterar ou remover participantes é ação administrativa.
- Inscrições, consulta de inscritos e relatórios mantêm as regras de negócio da APS 3 (vagas, duplicidade, etc.).
- Limitação conhecida: o usuário não está vinculado a um participante, então um usuário comum pode inscrever qualquer participante já cadastrado.

## 9. Erros

| Situação | HTTP | `detail` |
|---|---|---|
| E-mail ou senha incorretos no login | 401 | `E-mail ou senha inválidos.` |
| Token ausente, inválido, adulterado ou expirado | 401 (+ `WWW-Authenticate: Bearer`) | `Não foi possível validar as credenciais.` |
| Autenticado sem permissão | 403 | `Você não possui permissão para executar esta operação.` |
| E-mail de usuário já cadastrado | 409 | `Já existe um usuário cadastrado com este e-mail.` |
| Remover o último administrador | 409 | `Não é possível remover o perfil do último administrador.` |
| Dados inválidos (inclui `perfil` no cadastro) | 422 | lista de erros (sem o valor enviado) |

Os erros das APS anteriores (404, 409 de inscrição/vagas/exclusão, 500 genérico de banco) continuam iguais.

## 10. Exemplos de utilização

```bash
# cadastrar
curl -X POST http://127.0.0.1:8000/usuarios -H "Content-Type: application/json" \
  -d '{"nome":"Aluno Exemplo","email":"aluno@exemplo.com","senha":"senha_segura"}'

# login (guarde o access_token)
curl -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" \
  -d '{"email":"aluno@exemplo.com","senha":"senha_segura"}'

# usar o token
curl http://127.0.0.1:8000/auth/me -H "Authorization: Bearer <access_token>"
curl http://127.0.0.1:8000/eventos -H "Authorization: Bearer <access_token>"

# usuário comum tentando operação de administrador -> 403
curl -X POST http://127.0.0.1:8000/eventos -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" -d '{...}'
```

Sem token: `GET /eventos` → `401 {"detail": "Não foi possível validar as credenciais."}`.

## 11. Como reproduzir os testes

**Automatizados (pytest)** — usam banco temporário e uma chave JWT própria dos testes:
```bash
pip install -r requirements-dev.txt
pytest -v
```
Cobrem os 12 cenários do enunciado (cadastro, hash, e-mail duplicado, login válido/inválido, sem token, token válido/inválido/adulterado/expirado, 403 para usuário comum, operações do administrador, `/auth/me`, relatórios e funcionalidades da APS 3 sob as regras de acesso), além de validações, gestão de perfis e configuração da chave.

**Manuais no Swagger:** siga o roteiro de [`TESTES.md`](TESTES.md).

## 12. Evolução em relação à APS 3

| APS 3 | APS 4 |
|---|---|
| Todas as rotas públicas | Rotas protegidas por JWT; apenas cadastro de usuário e login são públicos |
| Sem usuários | Tabela `usuarios` com `senha_hash` (Argon2) e `perfil` |
| Sem controle de permissão | Perfis `administrador` e `usuario`, com 403 no servidor |
| — | `POST /auth/login`, `GET /auth/me`, `POST/GET /usuarios`, `PATCH /usuarios/{id}/perfil` |
| — | Camada `security/` (hash, JWT, dependências) e `criar_admin.py` |
| Erros 404/409/422/500 | + 401 e 403; 422 sem ecoar valores enviados |

