"""Cria o PRIMEIRO administrador (ou promove um usuário existente) de forma controlada.

Uso:
    python criar_admin.py
    python criar_admin.py --nome "Administrador" --email admin@exemplo.com

A senha é pedida no terminal (não aparece na tela, não vai para histórico de comandos
nem para arquivos do projeto). O script grava direto no banco local, por isso só quem
tem acesso à máquina/servidor consegue criar administradores por aqui. Depois de existir
um administrador, ele pode promover outros usuários pela API (PATCH /usuarios/{id}/perfil).
"""
import argparse
import sys
from getpass import getpass

from pydantic import ValidationError

from database import SessionLocal, criar_tabelas
from exceptions import ServiceError
from model import PerfilUsuario
from schema.usuario_schema import UsuarioCreate
from service import usuario_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria um usuário administrador.")
    parser.add_argument("--nome", help="Nome do administrador")
    parser.add_argument("--email", help="E-mail do administrador")
    args = parser.parse_args()

    nome = args.nome or input("Nome: ").strip()
    email = args.email or input("E-mail: ").strip()
    senha = getpass("Senha: ")
    if getpass("Confirme a senha: ") != senha:
        print("As senhas não conferem.")
        return 1

    try:
        dados = UsuarioCreate(nome=nome, email=email, senha=senha)
    except ValidationError as erro:
        print("Dados inválidos:")
        for e in erro.errors():
            print(f" - {'.'.join(str(p) for p in e['loc'])}: {e['msg']}")
        return 1

    criar_tabelas()
    db = SessionLocal()
    try:
        existente = usuario_service.obter_por_email(db, dados.email)
        if existente is None:
            usuario_service.criar(db, dados, perfil=PerfilUsuario.administrador)
            print(f"Administrador criado: {dados.email}")
        elif existente.perfil == PerfilUsuario.administrador.value:
            print(f"{dados.email} já é administrador. Nada foi alterado.")
        else:
            usuario_service.alterar_perfil(db, existente.id, PerfilUsuario.administrador)
            print(f"{dados.email} já existia e foi promovido a administrador "
                  "(a senha dele NÃO foi alterada).")
        return 0
    except ServiceError as erro:
        print(f"Erro: {erro.detail}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
