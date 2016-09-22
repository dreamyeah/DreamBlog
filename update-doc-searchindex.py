#!/usr/bin/env python
from blog import app
from blog.search import update_documentation_index
with app.test_request_context():
    update_documentation_index()
