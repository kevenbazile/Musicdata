from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Artist(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    followers = db.Column(db.Integer, nullable=False)
    genres = db.Column(db.String, nullable=True)
    popularity = db.Column(db.Integer, nullable=False)

class Track(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    popularity = db.Column(db.Integer, nullable=False)
    artist_id = db.Column(db.String, db.ForeignKey('artist.id'), nullable=False)
    streams = db.Column(db.Integer, nullable=True)
    downloads = db.Column(db.Integer, nullable=True)

    artist = db.relationship('Artist', back_populates='tracks')

Artist.tracks = db.relationship('Track', order_by=Track.id, back_populates='artist')
