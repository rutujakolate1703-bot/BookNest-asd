import os
from flask import Flask, session, render_template
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from config import Config
from models import db, User, CartItem


def ensure_database_exists(uri):
    """Create the database if missing when using a local/dev MySQL server that allows it."""
    url = make_url(uri)
    if not url.drivername.startswith("mysql") or not url.database:
        return
    server_only = URL.create(
        url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        query=url.query,
    )
    engine = create_engine(server_only, pool_pre_ping=True)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{url.database}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
    finally:
        engine.dispose()


def create_app(test_config=None):
    flask_app = Flask(__name__)
    flask_app.config.from_object(Config)
    if test_config:
        flask_app.config.update(test_config)

    if os.environ.get("ENSURE_DB_EXISTS") == "1":
        ensure_database_exists(flask_app.config["SQLALCHEMY_DATABASE_URI"])

    db.init_app(flask_app)

    from routes.auth_routes import auth_bp
    from routes.book_routes import book_bp
    from routes.cart_routes import cart_bp
    from routes.order_routes import order_bp
    from routes.payment_routes import payment_bp
    from routes.admin_routes import admin_bp

    for bp in (auth_bp, book_bp, cart_bp, order_bp, payment_bp, admin_bp):
        flask_app.register_blueprint(bp)

    @flask_app.template_filter("inr")
    def inr(value):
        return f"₹{value:,.2f}"

    @flask_app.context_processor
    def inject_globals():
        """Makes current_user and cart_count available in every template."""
        user = db.session.get(User, session["user_id"]) if "user_id" in session else None
        count = 0
        if user:
            count = sum(i.quantity for i in CartItem.query.filter_by(user_id=user.id))
        return {"current_user": user, "cart_count": count}

    @flask_app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="Page not found"), 404

    return flask_app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)