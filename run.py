from blog import app
from blog.database import init_db
init_db()
app.run(debug=True)
