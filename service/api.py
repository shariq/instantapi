from flask import Flask, request, g, jsonify
from flask_restful import reqparse, abort, Api, Resource
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
api = Api(app)

from models import Action, Invocation

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

    def post(self):
        data = request.get_json(force=True)
        action_id = data['action_id']
        action = Action.query.get_or_404(resource_id)
        invocation = super().post()

        # TODO: template invocation parameters into action.content
        # Maybe needs to be it's own "templater" thing

        # TODO: initialize pool globally?
        pool.run_job(params={
            'id': invocation.id,
            'action_content': action.content,
        },
        # start_callback: POST to invocations/<id> with status: started
        # end_callback: POST to invocations/<id> with status: done and result: some result
        # error_callback: POST to invocations/<id> with status: errored and result: str(err)
        )
        return invocation.as_dict()


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
        return new.as_dict()


routes = [
    (ActionList, "/actions"),
    (ActionInstance, "/actions/<resource_id>"),
    (ActionInvocationList, "/actions/<action_id>/invocations"),
    (InvocationList, "/invocations"),
    (InvocationInstance, "/invocations/<resource_id>"),
]
for class_, route in routes:
    api.add_resource(class_, route)

@app.route('/')
def list_available_routes():
    return jsonify(
        routes={class_.__name__: request.base_url + route[1:] for class_, route in routes}
    )
