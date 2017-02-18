from flask import Flask, redirect, url_for, session, request, render_template
from flask_oauth import OAuth


SECRET_KEY = 'development key'
DEBUG = True
FACEBOOK_APP_ID = '388932641474955'
FACEBOOK_APP_SECRET = '43613ff3768341eee29a88987967cf31'


app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY
oauth = OAuth()

facebook = oauth.remote_app('facebook',
    base_url='https://graph.facebook.com/',
    request_token_url=None,
    access_token_url='/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    consumer_key=FACEBOOK_APP_ID,
    consumer_secret=FACEBOOK_APP_SECRET,
    request_token_params={'scope': ['email', 'user_likes']}
)

engine = create_engine('sqlite:///database.db')
Base.metadata.bind = engine
Base.metadata.create_all(engine)
DBSession = sessionmaker(bind=engine, autoflush=False)
session = DBSession()

@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login')
def login():
    return facebook.authorize(callback=url_for('facebook_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True))


@app.route('/login/authorized')
@facebook.authorized_handler
def facebook_authorized(resp):
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['oauth_token'] = (resp['access_token'], '')
    me = facebook.get('/me?fields=id,name,languages,email')
    
    return render_template('index.html', name=me.data['name'])
    # return 'Logged in as id=%s name=%s languages=%s redirect=%s' % \
    #     (me.data['id'], me.data['name'], me.data['languages'], request.args.get('next'))


@facebook.tokengetter
def get_facebook_oauth_token():
    return session.get('oauth_token')


if __name__ == '__main__':
    app.run()