from flask import Blueprint, render_template, session, redirect, url_for, \
     request, flash, g, jsonify, abort, make_response
from flask_openid import COMMON_PROVIDERS
from blog import oid
from blog.search import search as perform_search
from blog.utils import requires_login, request_wants_json,format_creole
from blog.database import db_session, User, Post, Category
from blog.listings.releases import releases
import os
import re
import json
from blog.uploader import Uploader
from blog import app
mod = Blueprint('general', __name__)


@mod.route('/')
def index():
    if request_wants_json():
        return jsonify(releases=[r.to_json() for r in releases])

    return render_template(
        'general/index.html',
        latest_release=releases[-1],
        # pdf link does not redirect, needs version
        # docs version only includes major.minor
        docs_pdf_version='.'.join(releases[-1].version.split('.', 2)[:2])
    )


@mod.route('/search/')
def search():
    q = request.args.get('q') or ''
    page = request.args.get('page', type=int) or 1
    results = None
    if q:
        results = perform_search(q, page=page)
        if results is None:
            abort(404)
    return render_template('general/search.html', results=results, q=q)


@mod.route('/logout/')
def logout():
    if 'openid' in session:
        flash(u'Logged out')
        del session['openid']
    return redirect(request.referrer or url_for('general.index'))


@mod.route('/login/', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None:
        return redirect(url_for('general.index'))
    if 'cancel' in request.form:
        flash(u'Cancelled. The OpenID was not changed.')
        return redirect(oid.get_next_url())
    openid = request.values.get('openid')
    if not openid:
        openid = COMMON_PROVIDERS.get(request.args.get('provider'))
    if openid:
        return oid.try_login(openid, ask_for=['fullname', 'nickname'])
    error = oid.fetch_error()
    if error:
        flash(u'Error: ' + error)
    return render_template('general/login.html', next=oid.get_next_url())


@mod.route('/first-login/', methods=['GET', 'POST'])
def first_login():
    if g.user is not None or 'openid' not in session:
        return redirect(url_for('.login'))
    if request.method == 'POST':
        if 'cancel' in request.form:
            del session['openid']
            flash(u'Login was aborted')
            return redirect(url_for('general.login'))
        db_session.add(User(request.form['name'], session['openid']))
        db_session.commit()
        flash(u'Successfully created profile and logged in')
        return redirect(oid.get_next_url())
    return render_template('general/first_login.html',
                           next=oid.get_next_url(),
                           openid=session['openid'])


@mod.route('/profile/', methods=['GET', 'POST'])
@requires_login
def profile():
    name = g.user.name
    if request.method == 'POST':
        name = request.form['name'].strip()
        if not name:
            flash(u'Error: a name is required')
        else:
            g.user.name = name
            db_session.commit()
            flash(u'User profile updated')
            return redirect(url_for('.index'))
    return render_template('general/profile.html', name=name)


@mod.route('/profile/change-openid/', methods=['GET', 'POST'])
@requires_login
@oid.loginhandler
def change_openid():
    if request.method == 'POST':
        if 'cancel' in request.form:
            flash(u'Cancelled. The OpenID was not changed.')
            return redirect(oid.get_next_url())
    openid = request.values.get('openid')
    if not openid:
        openid = COMMON_PROVIDERS.get(request.args.get('provider'))
    if openid:
        return oid.try_login(openid)
    error = oid.fetch_error()
    if error:
        flash(u'Error: ' + error)
    return render_template('general/change_openid.html',
                           next=oid.get_next_url())


@oid.after_login
def create_or_login(resp):
    session['openid'] = resp.identity_url
    user = g.user or User.query.filter_by(openid=resp.identity_url).first()
    if user is None:
        return redirect(url_for('.first_login', next=oid.get_next_url(),
                                name=resp.fullname or resp.nickname))
    if user.openid != resp.identity_url:
        user.openid = resp.identity_url
        db_session.commit()
        flash(u'OpenID identity changed')
    else:
        flash(u'Successfully signed in')
    return redirect(oid.get_next_url())


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
    
@mod.route('/uedit')
def uedit():
    return render_template(
        'blog/uedit.html'
    )
    
@mod.route('/create')
@requires_login
def create():
    category_id = None
    preview = None
    print "1111111111111111"
    if 'category' in request.args:
        rv = Category.query.filter_by(slug=request.args['category']).first()
        if rv is not None:
            category_id = rv.id
    if request.method == 'POST':
        print "5555555"
        category_id = request.form.get('category', type=int)
        if 'preview' in request.form:
            preview = format_creole(request.form['body'])
        else:
            title = request.form['title']
            body = request.form['body']
            print "22222222222"
            if not body:
                flash(u'Error: you have to enter a snippet')
            else:
                category = Category.query.get(category_id)
                if category is not None:
                    posts = Post(g.user, category, title, body, category)
                    db_session.add(posts)
                    db_session.commit()
                    flash(u'Your snippet was added')
                    print "tttttttttttt"
                    return redirect(posts.url)
    return render_template('blog/create.html',
        categories=Category.query.order_by(Category.name).all(),
        active_category=category_id, preview=preview)
    
    
    
@mod.route('/upload/', methods=['GET', 'POST', 'OPTIONS'])
def upload():

    mimetype = 'application/json'
    result = {}
    action = request.args.get('action')

    with open(os.path.join(app.static_folder, 'ueditor', 'php',
                           'config.json')) as fp:
        try:

            CONFIG = json.loads(re.sub(r'\/\*.*\*\/', '', fp.read()))
        except:
            CONFIG = {}

    if action == 'config':

        result = CONFIG

    elif action in ('uploadimage', 'uploadfile', 'uploadvideo'):

        if action == 'uploadimage':
            fieldName = CONFIG.get('imageFieldName')
            config = {
                "pathFormat": CONFIG['imagePathFormat'],
                "maxSize": CONFIG['imageMaxSize'],
                "allowFiles": CONFIG['imageAllowFiles']
            }
        elif action == 'uploadvideo':
            fieldName = CONFIG.get('videoFieldName')
            config = {
                "pathFormat": CONFIG['videoPathFormat'],
                "maxSize": CONFIG['videoMaxSize'],
                "allowFiles": CONFIG['videoAllowFiles']
            }
        else:
            fieldName = CONFIG.get('fileFieldName')
            config = {
                "pathFormat": CONFIG['filePathFormat'],
                "maxSize": CONFIG['fileMaxSize'],
                "allowFiles": CONFIG['fileAllowFiles']
            }

        if fieldName in request.files:
            field = request.files[fieldName]
            uploader = Uploader(field, config, mod.static_folder)
            result = uploader.getFileInfo()
        else:
            result['state'] = 'upload API error'

    elif action in ('uploadscrawl'):

        fieldName = CONFIG.get('scrawlFieldName')
        config = {
            "pathFormat": CONFIG.get('scrawlPathFormat'),
            "maxSize": CONFIG.get('scrawlMaxSize'),
            "allowFiles": CONFIG.get('scrawlAllowFiles'),
            "oriName": "scrawl.png"
        }
        if fieldName in request.form:
            field = request.form[fieldName]
            uploader = Uploader(field, config, app.static_folder, 'base64')
            result = uploader.getFileInfo()
        else:
            result['state'] = 'upload API error'

    elif action in ('catchimage'):
        config = {
            "pathFormat": CONFIG['catcherPathFormat'],
            "maxSize": CONFIG['catcherMaxSize'],
            "allowFiles": CONFIG['catcherAllowFiles'],
            "oriName": "remote.png"
        }
        fieldName = CONFIG['catcherFieldName']

        if fieldName in request.form:

            source = []
        elif '%s[]' % fieldName in request.form:

            source = request.form.getlist('%s[]' % fieldName)

        _list = []
        for imgurl in source:
            uploader = Uploader(imgurl, config, app.static_folder, 'remote')
            info = uploader.getFileInfo()
            _list.append({
                'state': info['state'],
                'url': info['url'],
                'original': info['original'],
                'source': imgurl,
            })

        result['state'] = 'SUCCESS' if len(_list) > 0 else 'ERROR'
        result['list'] = _list

    else:
        result['state'] = 'request address error'

    result = json.dumps(result)

    if 'callback' in request.args:
        callback = request.args.get('callback')
        if re.match(r'^[\w_]+$', callback):
            result = '%s(%s)' % (callback, result)
            mimetype = 'application/javascript'
        else:
            result = json.dumps({'state': 'callback args error'})

    res = make_response(result)
    res.mimetype = mimetype
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Headers'] = 'X-Requested-With,X_Requested_With'
    return redirect('blog/create2.html',post_content=res)


@mod.route('/addpost', methods=['POST'])
def addpost():
    if request.method == 'POST':
        db_session.add(Post(title=request.form['title'], body=request.form['content'], category_id=request.form['category'], post_name=request.form['postname']))
        db_session.commit()
        return render_template('blog/create2.html',content=request.form['content'])