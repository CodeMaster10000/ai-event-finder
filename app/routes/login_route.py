from dependency_injector.wiring import inject, Provide
from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import create_access_token
from app.services.user_service import UserService
from app.container import Container

auth_ns = Namespace("auth", description="Authentication")

login_model = auth_ns.model("Login", {
    "email": fields.String(required=True),
    "password": fields.String(required=True)
})

@auth_ns.route("/login")
class Login(Resource):
    @inject # Injects User Service from DI container
    @auth_ns.expect(login_model)
    def post(self,
                user_service: UserService = Provide[Container.user_service]):
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return {"message": "Email and password are required."}, 400

        user = user_service.get_by_email(email)

        if not user or not user.password == password:
            return {"message": "Invalid credentials"}, 401

        access_token = create_access_token(identity=str(user.id))
        return {"access_token": access_token}
