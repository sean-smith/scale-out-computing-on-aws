from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class ApiKeys(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean)
    created_on = db.Column(db.DateTime)
    deactivated_on = db.Column(db.DateTime)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}