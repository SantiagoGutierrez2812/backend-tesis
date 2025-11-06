from flask import Flask, request
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from .database import init_db, db
from .smtp_config import init_smtp
import os
from datetime import timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

# Importar todos los modelos para que SQLAlchemy los reconozca
from .models import *

# Importar los Blueprints
from .routes.product.product_routes import product_bp
from .routes.transaction_type.transaction_type_routes import transaction_type_bp
from .routes.supplier.supplier_routes import supplier_bp
from .routes.company.company_routes import company_bp
from .routes.branch.branch_routes import branch_bp
from .routes.inventory.inventory_routes import inventory_bp
from .routes.staff.staff_routes import personal_bp
from .routes.login.login_routes import auth_bp
from .routes.log.log_routes import log_bp
from .routes.login_logs.user_logins_routes import user_logins_bp
from .routes.product_transaction.product_transaction_routes import (
    product_transaction_bp,
)


def create_app():
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret-key")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

    init_db(app)
    JWTManager(app)
    init_smtp(app)

    CORS(
        app,
        resources={
            r"/*": {
                "origins": [
                    "http://localhost:5173",
                    "https://frontend-tesis-dusky.vercel.app"
                ],         
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True
            }
        }
    )

    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            response = app.make_response('')
            response.status_code = 200
            return response

    # Registrar blueprints
    app.register_blueprint(product_bp)
    app.register_blueprint(transaction_type_bp)
    app.register_blueprint(supplier_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(branch_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(personal_bp)
    app.register_blueprint(product_transaction_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(log_bp)
    app.register_blueprint(user_logins_bp)

    with app.app_context():
        db.create_all()

    # Configurar APScheduler para tareas programadas
    scheduler = BackgroundScheduler()

    # Importar TokenService dentro de app_context
    from .services.token.token_service import TokenService

    # Tarea para eliminar tokens expirados cada 24 horas a las 3:00 AM
    scheduler.add_job(
        func=lambda: app.app_context().push() or TokenService.deleteExpiredTokens(),
        trigger=CronTrigger(hour=3, minute=0),
        id="delete_expired_tokens",
        name="Eliminar tokens expirados diariamente",
        replace_existing=True
    )

    # Iniciar el scheduler
    scheduler.start()
    print("[APScheduler] Scheduler iniciado - Limpieza de tokens programada para las 3:00 AM diariamente")

    # Asegurar que el scheduler se detenga cuando la aplicación se cierre
    atexit.register(lambda: scheduler.shutdown())

    return app
