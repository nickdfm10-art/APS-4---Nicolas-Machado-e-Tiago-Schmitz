from sqlalchemy import func, select
from sqlalchemy.orm import Session

from exceptions import ConflitoError, NaoEncontradoError
from model import PerfilUsuario, Usuario
from schema.usuario_schema import UsuarioCreate
from security.security import gerar_hash_senha
from service.persistencia import confirmar

MSG_NAO_ENCONTRADO = "Usuário não encontrado."
MSG_EMAIL_DUPLICADO = "Já existe um usuário cadastrado com este e-mail."
MSG_ULTIMO_ADMIN = "Não é possível remover o perfil do último administrador."


def obter_por_id(db: Session, usuario_id: int) -> Usuario | None:
    return db.get(Usuario, usuario_id)


def obter_por_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.email == email))


def obter_ou_404(db: Session, usuario_id: int) -> Usuario:
    usuario = obter_por_id(db, usuario_id)
    if usuario is None:
        raise NaoEncontradoError(MSG_NAO_ENCONTRADO)
    return usuario


def listar(db: Session) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.id)))


def criar(
    db: Session,
    dados: UsuarioCreate,
    perfil: PerfilUsuario = PerfilUsuario.usuario,
) -> Usuario:
    """Cadastra um usuário guardando apenas o hash da senha.

    O parâmetro 'perfil' é de uso interno (ex.: script criar_admin.py). A rota pública
    POST /usuarios nunca o repassa, então ele sempre vale 'usuario' pela API.
    """
    if obter_por_email(db, dados.email) is not None:
        raise ConflitoError(MSG_EMAIL_DUPLICADO)

    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=gerar_hash_senha(dados.senha),
        perfil=PerfilUsuario(perfil).value,
    )
    db.add(usuario)
    confirmar(db, MSG_EMAIL_DUPLICADO)  # UNIQUE do banco como garantia final
    db.refresh(usuario)
    return usuario


def alterar_perfil(db: Session, usuario_id: int, perfil: PerfilUsuario | str) -> Usuario:
    usuario = obter_ou_404(db, usuario_id)
    novo_perfil = PerfilUsuario(perfil).value
    admin = PerfilUsuario.administrador.value

    # Nunca deixar o sistema sem nenhum administrador.
    if usuario.perfil == admin and novo_perfil != admin:
        total_admins = db.scalar(
            select(func.count(Usuario.id)).where(Usuario.perfil == admin)
        )
        if (total_admins or 0) <= 1:
            raise ConflitoError(MSG_ULTIMO_ADMIN)

    usuario.perfil = novo_perfil
    confirmar(db, "Não foi possível alterar o perfil do usuário.")
    db.refresh(usuario)
    return usuario
