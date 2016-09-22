from flask import Blueprint, render_template, session, redirect, url_for, \
     request, flash, g, jsonify, abort
from flask_openid import COMMON_PROVIDERS
from blog import oid
from blog.search import search as perform_search
from blog.utils import requires_login, request_wants_json
from blog.database import db_session, User
from blog.listings.releases import releases

mod = Blueprint('blog', __name__)

@mod.route('/blogindex')
def blogindex():
    return render_template(
        'blog/index.html'
    )
    
@mod.route('/blogindex1')
def blogindex1():
    return render_template(
        'blog/index1.html'
    )
    
@mod.route('/blogindex2')
def blogindex2():
    return render_template(
        'blog/index2.html'
    )