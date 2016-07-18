import functools, flask

# see http://flask.pocoo.org/snippets/8/

authdb = {
    ('admin', 'admin'),
    ('joel', 'coen'),
    ('ethan', 'coen'),
    ('hudsucker', 'proxy')
}


# FIXME: do some real authentication
def check_auth(username, password):
    return (username, password) in authdb


def requires_auth(methods=[]):
    def dec(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            auth = flask.request.authorization
            flag = flask.request.method in methods
            if flag and (not auth or not check_auth(auth.username, auth.password)):
                return flask.Response('Unauthorized.', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
            return f(*args, **kwargs)
        return wrapper
    return dec
