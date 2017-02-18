from flask import Flask, redirect, url_for, request, render_template
from flask import session as login_session
from flask_oauth import OAuth
from model import *

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
    login_session['oauth_token'] = (resp['access_token'], '')
    me = facebook.get('/me?fields=id,name,languages,email')

    # Create new User if necessary
    if session.query(User).filter_by(facebook_id=me.data['id']).first() is None:
        my_languages = []
        if 'languages' in me.data:
            languages = me.data['languages']
            for language in languages:
                currLanguage = session.query(Language).filter_by(language_id=language['id']).first()
                # Create new Language if necessary
                if currLanguage is None:
                    currLanguage = Language(name=language['name'], id=language['id'])
                    session.add(currLanguage)
                    session.commit()
                my_languages.append(currLanguage)
        user = User(name=me.data['name'], email=me.data['email'], facebook_id=me.data['id'])
        for my_language in my_languages:
            languageAssociation = LanguageAssociation(user=user, language=my_language)
            session.add(languageAssociation)
            session.commit()
    currUser = session.query(User).filter_by(facebook_id=me.data['id']).one()
    return render_template('index.html', user=currUser)
    # return 'Logged in as id=%s name=%s languages=%s redirect=%s' % \
    #     (me.data['id'], me.data['name'], me.data['languages'], request.args.get('next'))


@facebook.tokengetter
def get_facebook_oauth_token():
    return login_session.get('oauth_token')


if __name__ == '__main__':
    app.run()