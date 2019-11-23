from api import db


def db_save(d):
    def save(model):
        d.session.add(model)
        d.session.commit()


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
    result = db.Column(db.String)

    action = db.relationship("Action", backref=db.backref("actions", lazy=True))

    def __repr__(self):
        return f"<Invocation #{self.id} of {self.action.name} ({self.action.id})>"
