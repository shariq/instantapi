from flask import Flask, request, g, jsonify
from flask_restful import reqparse, abort, Api, Resource
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
api = Api(app)

from models import db_save, Action, Invocation

db.save = db_save

parser = reqparse.RequestParser()
parser.add_argument("task")


def error(message, status_code):
    return {
        "message": message,
        "status_code": status_code,
    }


class SqlResource(Resource):
    model = None

    def __init__(self, model=None):
        if model:
            self.model = model
        if self.model is None:
            raise NotImplemented
        super().__init__()


class InstanceResource(SqlResource):
    def get(self, resource_id):
        return self.model.query.get_or_404(resource_id).as_dict()

    def post(self, resource_id):
        data = request.get_json(force=True)
        m = self.model.query.get_or_404(resource_id)
        for (key, value) in data.items():
            if key not in m.__updatable__:
                return error(f"Can't update key {key}", 400)
            setattr(m, key, value)
        db.session.commit()
        return m.as_dict()


class ListResource(SqlResource):
    def get(self):
        return jsonify(items=[m.as_dict() for m in self.model.query.all()])

    def post(self):
        data = request.get_json(force=True)
        new = self.model(**data)
        db.session.add(new)
        db.session.commit()
        return new.as_dict()


class ActionInstance(InstanceResource):
    model = Action


class ActionList(ListResource):
    model = Action


class InvocationInstance(InstanceResource):
    model = Invocation


class InvocationList(ListResource):
    model = Invocation


class ActionInvocationList(Resource):
    def get(self, action_id):
        Action.get_or_404(action_id)
        invocations = Invocation.query.filter_by(action_id=action_id).all()
        return jsonify(items=[m.as_dict() for m in invocations])

    def post(self, action_id):
        Action.get_or_404(action_id)
        new = Invocation(action_id=action_id)
        db.session.add(new)
        db.session.commit()
        return new.as_dict


api.add_resource(ActionList, "/actions")
api.add_resource(ActionInstance, "/actions/<resource_id>")
api.add_resource(ActionInvocationList, "/actions/<action_id>/invocations")
api.add_resource(InvocationList, "/invocations")
api.add_resource(InvocationInstance, "/invocations/<resource_id>")
