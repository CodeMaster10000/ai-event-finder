from flask_restx import Namespace, Resource
from flask import request, abort
from dependency_injector.wiring import inject, Provide
from app.container import Container
from app.services.user_service import UserService
from app.schemas.user_schema import CreateUserSchema, UserSchema
from marshmallow import ValidationError
from app.models.user import User

# Namespace for user operations
user_ns = Namespace("users", description="User based operations")

# Marshmallow schemas for validation and serialization
create_user_schema = CreateUserSchema()
user_schema = UserSchema()
users_schema = UserSchema(many=True)

@user_ns.route("")
class UserBaseResource(Resource):
    @inject
    def get(self,
            user_service: UserService = Provide[Container.user_service]):
        """Get all users"""
        users = user_service.get_all()
        return users_schema.dump(users), 200

    @inject
    def post(self,
             user_service: UserService = Provide[Container.user_service]):
        """Create or update a user"""
        json_data = request.get_json()
        if not json_data:
            abort(400, description="JSON body required")
        try:
            data = create_user_schema.load(json_data)
        except ValidationError as err:
            abort(400, description=err.messages)

        # Instantiate User model from validated data
        user = User(**data)
        saved_user = user_service.save(user)
        return user_schema.dump(saved_user), 201

@user_ns.route('/id/<int:user_id>')
class UserByIdResource(Resource):
    @inject
    def get(self,
            user_id: int,
            user_service: UserService = Provide[Container.user_service]):
        """Get a user by ID"""
        user = user_service.get_by_id(user_id)
        if not user:
            abort(404, description=f"User {user_id} not found")
        return user_schema.dump(user), 200

    @inject
    def delete(self,
               user_id: int,
               user_service: UserService = Provide[Container.user_service]):
        """Delete a user by ID"""
        user = user_service.get_by_id(user_id)
        if not user:
            abort(404, description=f"User {user_id} not found")
        user_service.delete_by_id(user_id)
        return '', 204

@user_ns.route('/email/<string:email>')
class UserByEmailResource(Resource):
    @inject
    def get(self,
            email: str,
            user_service: UserService = Provide[Container.user_service]):
        """Get a user by email"""
        user = user_service.get_by_email(email)
        if not user:
            abort(404, description=f"User with email {email} not found")
        return user_schema.dump(user), 200

@user_ns.route('/name/<string:name>')
class UsersByNameResource(Resource):
    @inject
    def get(self,
            name: str,
            user_service: UserService = Provide[Container.user_service]):
        """Get a user by name"""
        user = user_service.get_by_name(name)
        if not user:
            abort(404, description=f"User with name {name} not found")
        return user_schema.dump(user), 200

@user_ns.route('/exists/id/<int:user_id>')
class ExistsByIdResource(Resource):
    @inject
    def get(self,
            user_id: int,
            user_service: UserService = Provide[Container.user_service]):
        """Check the existence of a user by ID"""
        exists = user_service.exists_by_id(user_id)
        return {'exists': exists}, 200

@user_ns.route('/exists/name/<string:name>')
class ExistsByNameResource(Resource):
    @inject
    def get(self,
            name: str,
            user_service: UserService = Provide[Container.user_service]):
        """Check the existence of users by name"""
        exists = user_service.exists_by_name(name)
        return {'exists': exists}, 200
