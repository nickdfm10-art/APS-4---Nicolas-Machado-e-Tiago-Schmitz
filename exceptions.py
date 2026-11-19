"""Exceções de negócio. Os services as levantam e o main.py as converte em JSON."""


class ServiceError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NaoAutenticadoError(ServiceError):
    """Credenciais ausentes, inválidas ou expiradas -> HTTP 401."""

    status_code = 401


class AcessoNegadoError(ServiceError):
    """Usuário autenticado, mas sem permissão para a operação -> HTTP 403."""

    status_code = 403


class NaoEncontradoError(ServiceError):
    """Recurso inexistente -> HTTP 404."""

    status_code = 404


class ConflitoError(ServiceError):
    """Conflito com o estado atual dos dados -> HTTP 409."""

    status_code = 409
