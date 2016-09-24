# -*- coding: utf-8 -*-
from urlparse import urljoin
from flask import Blueprint, render_template, request, flash, abort, redirect, \
     g, url_for, jsonify
from werkzeug.contrib.atom import AtomFeed
from blog.utils import requires_login, requires_admin, \
     format_creole, request_wants_json
from blog.database import Category, Post, Comment, db_session

from datetime import datetime

mod = Blueprint('posts', __name__, url_prefix='/posts')


@mod.route('/')
def index():
    return render_template('posts/index.html',
        categories=Category.query.order_by(Category.name).all(),
        recent=Post.query.order_by(Post.update_time.desc()).limit(5).all())


@mod.route('/new/', methods=['GET', 'POST'])
@requires_login
def new():
    category_id = None
    preview = None
    if 'category' in request.args:
        rv = Category.query.filter_by(slug=request.args['category']).first()
        if rv is not None:
            category_id = rv.id
    if request.method == 'POST':
        category_id = request.form.get('category', type=int)
        if 'preview' in request.form:
            preview = format_creole(request.form['body'])
        else:
            title = request.form['title']
            body = request.form['body']
            if not body:
                flash(u'Error: you have to enter a post')
            else:
                category = Category.query.get(category_id)
                if category is not None:
                    post = Post(g.user, title, body, category)
                    db_session.add(post)
                    db_session.commit()
                    flash(u'Your post was added')
                    return redirect(post.url)
    return render_template('posts/new.html',
        categories=Category.query.order_by(Category.name).all(),
        active_category=category_id, preview=preview)


@mod.route('/<int:id>/', methods=['GET', 'POST'])
def show(id):
    post = Post.query.get(id)
    if post is None:
        abort(404)
    if request_wants_json():
        return jsonify(post=post.to_json())
    if request.method == 'POST':
        title = request.form['title']
        text = request.form['text']
        if text:
            db_session.add(Comment(post, g.user, title, text))
            db_session.commit()
            flash(u'Your comment was added')
            return redirect(post.url)
    return render_template('posts/show.html', post=post)


@mod.route('/comments/<int:id>/', methods=['GET', 'POST'])
@requires_admin
def edit_comment(id):
    comment = Comment.query.get(id)
    if comment is None:
        abort(404)
    form = dict(title=comment.title, text=comment.text)
    if request.method == 'POST':
        if 'delete' in request.form:
            db_session.delete(comment)
            db_session.commit()
            flash(u'Comment was deleted.')
            return redirect(comment.post.url)
        elif 'cancel' in request.form:
            return redirect(comment.post.url)
        form['title'] = request.form['title']
        form['text'] = request.form['text']
        if not form['text']:
            flash(u'Error: comment text is required.')
        else:
            comment.title = form['title']
            comment.text = form['text']
            print id
            comment.post_id = id
            db_session.commit()
            flash(u'Comment was updated.')
            return redirect(comment.post.url)
    return render_template('posts/edit_comment.html', form=form,
                           comment=comment)


@mod.route('/edit/<int:id>/', methods=['GET', 'POST'])
@requires_login
def edit(id):
    post = Post.query.get(id)
    if post is None:
        abort(404)
    if g.user is None or (not g.user.is_admin and post.author != g.user):
        abort(401)
    preview = None
    form = dict(title=post.title, body=post.body,
                category=post.category.id)
    if request.method == 'POST':
        form['title'] = request.form['title']
        form['body'] = request.form['body']
        form['category'] = request.form.get('category', type=int)
        if 'preview' in request.form:
            preview = format_creole(request.form['body'])
        elif 'delete' in request.form:
            for comment in post.comments:
                db_session.delete(comment)
            db_session.delete(post)
            db_session.commit()
            flash(u'Your post was deleted')
            return redirect(url_for('posts.index'))
        else:
            category_id = request.form.get('category', type=int)
            if not form['body']:
                flash(u'Error: you have to enter a post')
            else:
                category = Category.query.get(category_id)
                if category is not None:
                    post.title = form['title']
                    post.body = form['body']
                    post.category = category
                    post.update_time=datetime.utcnow()
                    db_session.commit()
                    flash(u'Your post was modified')
                    return redirect(post.url)
    return render_template('posts/edit.html',
        post=post, preview=preview, form=form,
        categories=Category.query.order_by(Category.name).all())


@mod.route('/category/<slug>/')
def category(slug):
    category = Category.query.filter_by(slug=slug).first()
    if category is None:
        abort(404)
    posts = category.posts.order_by(Post.title).all()
    if request_wants_json():
        return jsonify(category=category.to_json(),
                       posts=[s.id for s in posts])
    return render_template('posts/category.html', category=category,
                           posts=posts)


@mod.route('/manage-categories/', methods=['GET', 'POST'])
@requires_admin
def manage_categories():
    categories = Category.query.order_by(Category.name).all()
    if request.method == 'POST':
        for category in categories:
            category.name = request.form['name.%d' % category.id]
            category.slug = request.form['slug.%d' % category.id]
        db_session.commit()
        flash(u'Categories updated')
        return redirect(url_for('.manage_categories'))
    return render_template('posts/manage_categories.html',
                           categories=categories)


@mod.route('/new-category/', methods=['POST'])
@requires_admin
def new_category():
    category = Category(name=request.form['name'])
    db_session.add(category)
    db_session.commit()
    flash(u'Category %s created.' % category.name)
    return redirect(url_for('.manage_categories'))


@mod.route('/delete-category/<int:id>/', methods=['GET', 'POST'])
@requires_admin
def delete_category(id):
    category = Category.query.get(id)
    if category is None:
        abort(404)
    if request.method == 'POST':
        if 'cancel' in request.form:
            flash(u'Deletion was aborted')
            return redirect(url_for('.manage_categories'))
        move_to_id = request.form.get('move_to', type=int)
        if move_to_id:
            move_to = Category.query.get(move_to_id)
            if move_to is None:
                flash(u'Category was removed in the meantime')
            else:
                for post in category.posts.all():
                    post.category = move_to
                db_session.delete(category)
                flash(u'Category %s deleted and entries moved to %s.' %
                      (category.name, move_to.name))
        else:
            category.posts.delete()
            db_session.delete(category)
            flash(u'Category %s deleted' % category.name)
        db_session.commit()
        return redirect(url_for('.manage_categories'))
    return render_template('posts/delete_category.html',
                           category=category,
                           other_categories=Category.query
                              .filter(Category.id != category.id).all())


@mod.route('/recent.atom')
def recent_feed():
    feed = AtomFeed(u'Recent Flask posts',
                    subtitle=u'Recent additions to the Flask post archive',
                    feed_url=request.url, url=request.url_root)
    posts = Post.query.order_by(Post.pub_date.desc()).limit(15)
    for post in posts:
        feed.add(post.title, unicode(post.rendered_body),
                 content_type='html', author=post.author.name,
                 url=urljoin(request.url_root, post.url),
                 updated=post.pub_date)
    return feed.get_response()


@mod.route('/posts/<int:id>/comments.atom')
def comments_feed(id):
    post = Post.query.get(id)
    if post is None:
        abort(404)
    feed = AtomFeed(u'Comments for post “%s”' % post.title,
                    feed_url=request.url, url=request.url_root)
    for comment in post.comments:
        feed.add(comment.title or u'Untitled Comment',
                 unicode(comment.rendered_text),
                 content_type='html', author=comment.author.name,
                 url=request.url, updated=comment.pub_date)
    return feed.get_response()
