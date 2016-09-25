import os

_basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = False

SECRET_KEY = 'testkey'
DATABASE_URI = "mysql://%s:%s@%s/%s" % ('root', '123456', '127.0.0.1', 'blog')
DATABASE_CONNECT_OPTIONS = {}
ADMINS = frozenset(['https://login.xxx.com/openid/xxx/'])

WHOOSH_INDEX = os.path.join(_basedir, 'blog.whoosh')
DOCUMENTATION_PATH = os.path.join(_basedir, '../flask/docs/_build/dirhtml')

del os
