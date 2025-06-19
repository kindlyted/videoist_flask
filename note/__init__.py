from flask import Blueprint

note_bp = Blueprint('note', __name__, static_folder='static', template_folder='templates')

from . import routes