import jinja2
import json
import requests

from flask import Flask, request, g, jsonify, send_from_directory
from flask_restful import reqparse, abort, Api, Resource
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from worker.replayer import Pool, DummyWorker

# from mock import Mock

worker_pool = Pool()
# worker_pool = Mock()  # use when just testing the API

app = Flask(__name__, static_url_path="")
db_path = Path(__file__).parent.parent.joinpath("database.db").absolute()
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
api = Api(app)

from service.models import Action, Invocation


def error(message, status_code):
    return {
        "message": message,
        "status_code": status_code,
    }


class SqlResource(Resource):
    model = None

    def __init__(self, model=None):
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


def update_invocation(invocation_id, payload):
    requests.post(f"http://localhost:5000/invocations/{invocation_id}", json=payload)


def invocation_start_callback(invocation_id):
    def callback():
        update_invocation(invocation_id, {"status": "working"})

    return callback


def invocation_end_callback(invocation_id):
    def callback(result):
        try:
            result = json.dumps(result)
        except Exception:
            result = str(result)
        update_invocation(invocation_id, {"status": "done", "result": result})

    return callback


def invocation_error_callback(invocation_id):
    def callback(err):
        update_invocation(invocation_id, {"status": "failed", "result": str(err)})

    return callback


def run_action(invocation, incoming_parameters: dict):
    selectors = incoming_parameters.pop('selectors', [])
    if invocation.action.parameters is None:
        content = invocation.action.content
    else:
        content = jinja2.Template(invocation.action.content).render(incoming_parameters)
    worker_pool.async_run_job(
        params={"id": invocation.id, "content": content, "selectors": selectors},
        start_callback=invocation_start_callback(invocation.id),
        end_callback=invocation_end_callback(invocation.id),
        error_callback=invocation_error_callback(invocation.id),
    )
    db.session.refresh(invocation)
    return invocation.as_dict()


def check_required_parameters(required: set, incoming: set):
    if not required.issubset(incoming):
        abort(400, message=f"Missing parameters: {list(required - incoming)}")


class InvocationList(ListResource):
    model = Invocation

    def post(self):
        data = request.get_json(force=True)
        action_id = data["action_id"]
        action = Action.query.get_or_404(action_id)
        if action.parameters is not None:
            check_required_parameters(
                set(action.parameters), set(data["parameters"].keys())
            )
        invocation_dict = super().post()
        invocation = Invocation.query.get_or_404(invocation_dict["id"])
        return run_action(invocation, data["parameters"])


class ActionInvocationList(Resource):
    def get(self, action_id):
        Action.query.get_or_404(action_id)
        invocations = Invocation.query.filter_by(action_id=action_id).all()
        return jsonify(items=[m.as_dict() for m in invocations])

    def post(self, action_id):
        data = request.get_json(force=True)
        action = Action.query.get_or_404(action_id)
        if action.parameters is not None:
            check_required_parameters(
                set(action.parameters), set(data["parameters"].keys())
            )
        invocation = Invocation(action_id=action_id, parameters=data["parameters"])
        db.session.add(invocation)
        db.session.commit()
        return run_action(invocation, data["parameters"])


@app.route("/screenshots/<path:path>")
def send_screenshot(path):
    return send_from_directory("screenshots", path)


routes = [
    (ActionList, "/actions"),
    (ActionInstance, "/actions/<resource_id>"),
    (ActionInvocationList, "/actions/<action_id>/invocations"),
    (InvocationList, "/invocations"),
    (InvocationInstance, "/invocations/<resource_id>"),
]
for class_, route in routes:
    api.add_resource(class_, route)


@app.route("/")
def list_available_routes():
    return jsonify(
        routes={
            class_.__name__: request.base_url + route[1:] for class_, route in routes
        }
    )
