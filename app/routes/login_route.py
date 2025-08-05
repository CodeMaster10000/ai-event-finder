from flask import request
from flask_restx import Namespace, Resource, fields
from app.extensions import db
from app.models.user import User
from flask_jwt_extended import create_access_token

auth_ns = Namespace("auth", description="Authentication")

login_model = auth_ns.model("Login", {
    "email": fields.String(required=True),
    "password": fields.String(required=True)
})

@auth_ns.route("/login")
class Login(Resource):
    @staticmethod
    @auth_ns.expect(login_model)
    def post():
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return {"message": "Email and password are required."}, 400

        user = db.session.query(User).filter_by(email=email).first()
        if not user or user.password != password:
            return {"message": "Invalid credentials"}, 401

        access_token = create_access_token(identity=str(user.id))
        return {"access_token": access_token}
