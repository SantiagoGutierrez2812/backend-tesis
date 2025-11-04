from ...models.token.token import Token
from ...database import db
from ...services.log.log_service import LogService
from datetime import datetime, timedelta, timezone


class TokenService:

    @staticmethod
    def getAllTokens():
        return Token.query.all()

    @staticmethod
    def create(token):

        new_token = Token(
            token=token["token"],
            app_user_id=token["app_user_id"],
            type=token["type"],
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )

        db.session.add(new_token)
        db.session.commit()

        return new_token

    @staticmethod
    def findValidToken(app_user_id, token):

        token = Token.query.filter(
            Token.app_user_id == app_user_id,
            Token.token == token,
            Token.expires_at > datetime.now(timezone.utc),
            Token.is_used == False,
        ).first()

        if token is None:
            LogService.create_log(
                {
                    "module": f"{TokenService.__name__}.{TokenService.findValidToken.__name__}",
                    "message": "Se ingresó un token inválido",
                }
            )
            raise ValueError("El token buscado es inválido")

        return token

    @staticmethod
    def deleteExpiredTokens():
        """
        Elimina todos los tokens expirados de la base de datos.
        Se ejecuta automáticamente mediante APScheduler.
        """
        try:
            expired_tokens = Token.query.filter(
                Token.expires_at <= datetime.now(timezone.utc)
            ).all()

            count = len(expired_tokens)

            if count > 0:
                for token in expired_tokens:
                    db.session.delete(token)
                db.session.commit()

                LogService.create_log(
                    {
                        "module": f"{TokenService.__name__}.{TokenService.deleteExpiredTokens.__name__}",
                        "message": f"Se eliminaron {count} tokens expirados de la base de datos",
                    }
                )
                print(f"[APScheduler] Tokens expirados eliminados: {count}")
            else:
                print("[APScheduler] No hay tokens expirados para eliminar")

        except Exception as e:
            db.session.rollback()
            # Los errores de deadlock son esperados cuando múltiples workers intentan eliminar
            # al mismo tiempo. Solo registramos en log sin imprimir en consola para evitar ruido.
            LogService.create_log(
                {
                    "module": f"{TokenService.__name__}.{TokenService.deleteExpiredTokens.__name__}",
                    "message": f"Error al eliminar tokens expirados: {str(e)}",
                }
            )
            pass
