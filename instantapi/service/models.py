import json
from flask import request
from sqlalchemy.ext.hybrid import hybrid_property
from typing import List, Any, Optional, Dict

from service.api import db


def as_dict(self):
    return dict((c.name, getattr(self, c.name)) for c in self.__table__.columns)


db.Model.as_dict = as_dict


class Action(db.Model):
    __updatable__ = [
        "content",
    ]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    content = db.Column(db.String)
    _parameters = db.Column(
        "parameters", db.String
    )  # comma-separated list of parameters

    @property
    def parameters(self):
        if self._parameters:
            return self._parameters.split(",")

    @parameters.setter
    def parameters(self, parameters: Optional[List[str]]):
        if parameters:
            self._parameters = ",".join(parameters)
        else:
            self._parameters = None

    def __repr__(self):
        return f"<Action {self.name}>"


class Invocation(db.Model):
    """
    State machine:

    Init -> Received -> Working -> Done
    """

    __updatable__ = ["status", "result"]

    id = db.Column(db.Integer, primary_key=True)
    action_id = db.Column(db.Integer, db.ForeignKey("action.id"), nullable=False)
    status = db.Column(db.String, default="init", nullable=False)  # todo: enum
    result = db.Column(db.String, nullable=True)

    action = db.relationship("Action", backref=db.backref("actions", lazy=True))

    _parameters = db.Column("parameters", db.String)  # JSON object of parameters

    @property
    def parameters(self):
        if self._parameters:
            return json.loads(self._parameters)

    @parameters.setter
    def parameters(self, parameters: Optional[Dict[str, Any]]):
        if parameters:
            self._parameters = json.dumps(parameters)
        else:
            self._parameters = None

    def __repr__(self):
        return f"<Invocation #{self.id} of {self.action.name} ({self.action.id})>"

    def as_dict(self):
        d = super().as_dict()
        if "password" in (d.get("parameters") or {}):
            d["parameters"]["password"] = "REDACTED"
        if self.result:
            try:
                result_dict = json.loads(self.result)
                d["result"] = result_dict
                d["links"] = {
                    "screenshot": f"{request.url_root}screenshots/{d['result']['screenshot_path']}"
                }
            except Exception:
                pass
        return d
