import custom_static
from bottle import *

@get('/')
def index():
    return(custom_static.data)

run(reloader=True, host='0.0.0.0', port=80, server='paste')
