from flask import Flask, redirect, url_for, request, render_template, flash
from flask import session as login_session
from flask_oauth import OAuth
from model import *
import json
import operator

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
    request_token_params={'scope': ['email', 'user_likes', 'user_hometown', 'user_location', 'user_friends']}
)

engine = create_engine('sqlite:///database.db')
Base.metadata.bind = engine
Base.metadata.create_all(engine)
DBSession = sessionmaker(bind=engine, autoflush=False)
session = DBSession()

@app.route('/')
def index():
    return render_template('start.html')

@app.route('/me')
def my_profile():
    if 'oauth_token' not in login_session or login_session['oauth_token'] == '':
        return redirect(url_for('login'))
    else:
        currUser = session.query(User).filter_by(facebook_id=login_session['facebook_id']).one()
        update_user_languages(login_session['facebook_id'])
        my_languages = [assoc.language for assoc in session.query(LanguageAssociation).filter_by(user=currUser).all()]
        all_languages = session.query(Language).all()
        all_languages.sort(key=lambda language: language.name)
        return render_template('index.html', user=currUser, \
            my_languages=my_languages, all_languages=all_languages)


def update_user_languages(facebook_id):
    user = session.query(User).filter_by(facebook_id=login_session['facebook_id']).one()
    session.query(LanguageAssociation).filter_by(user=user).delete()
    my_languages = []
    me = facebook.get('/me?fields=languages')
    if 'languages' in me.data:
        languages = me.data['languages']
        for language in languages:
            currLanguage = session.query(Language).filter_by(name=language['name']).first()
            # Create new Language if necessary
            if currLanguage is None:
                currLanguage = Language(name=language['name'], language_id=language['id'])
                session.add(currLanguage)
                session.commit()
            my_languages.append(currLanguage)
    for my_language in my_languages:
        languageAssociation = LanguageAssociation(user=user, language=my_language)
        session.add(languageAssociation)
        session.commit()


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
    me = facebook.get('/me?fields=id,name,languages,email,location,hometown,friends{languages,name}')
    login_session['facebook_id'] = me.data['id']

    friends = None
    # Create new User if necessary
    if session.query(User).filter_by(facebook_id=me.data['id']).first() is None:
        my_languages = []
        if 'languages' in me.data:
            languages = me.data['languages']
            for language in languages:
                currLanguage = session.query(Language).filter_by(name=language['name']).first()
                # Create new Language if necessary
                if currLanguage is None:
                    currLanguage = Language(name=language['name'], language_id=language['id'])
                    session.add(currLanguage)
                    session.commit()
                my_languages.append(currLanguage)
        user = User(name=me.data['name'], facebook_id=me.data['id'])
        if 'email' in me.data:
            user.email = me.data['email']
        if 'hometown' in me.data:
            user.hometown = me.data['hometown']['name']
        if 'location' in me.data:
            user.location = me.data['location']['name']
        session.add(user)
        session.commit()
        for my_language in my_languages:
            languageAssociation = LanguageAssociation(user=user, language=my_language)
            session.add(languageAssociation)
            session.commit()
    currUser = session.query(User).filter_by(facebook_id=me.data['id']).one()
    return redirect(url_for('my_profile'))
    # return 'Logged in as id=%s name=%s languages=%s redirect=%s' % \
    #     (me.data['id'], me.data['name'], me.data['languages'], request.args.get('next'))


@facebook.tokengetter
def get_facebook_oauth_token():
    return login_session.get('oauth_token')


@app.route('/logout')
def logout():
    login_session.pop('oauth_token')
    return redirect(url_for('index'))


def get_languages(user):
    return [assoc.language for assoc in session.query(LanguageAssociation).filter_by(user=user).all()]


def get_learning_languages(user):
    return [assoc.language for assoc in session.query(LearningLanguageAssociation).filter_by(user=user).all()]


@app.route('/matches')
def matches():
    # TODO: does not work. need to rewrite matching algorithm
    me = session.query(User).filter_by(facebook_id=login_session['facebook_id']).one()
    my_languages = get_languages(me)
    my_languages_to_learn = get_learning_languages(me)
    
    users = session.query(User).all()
    user_dict = {}
    for user in users:
        score = 0
        if user is not me:
            user_languages = get_languages(user)
            user_languages_to_learn = get_learning_languages(user)

            # Check common language
            score += len(set(my_languages) & set(user_languages)) * 10

            # If User knows a language you want to learn
            score += len(set(my_languages_to_learn) & set(user_languages)) * 20

            # If you know a language User wants to learn
            score += len(set(my_languages) & set(user_languages_to_learn)) * 5

            # TODO: mutual friends
            # TODO: location
            user_dict[user] = score
    sorted_users = []
    for u in sorted(user_dict, key=user_dict.get, reverse=True):
        sorted_users.append((u, user_dict[u]))
    return json.dumps([{
        'name': user.name, 
        'score': score, 
        'facebook_id': user.facebook_id,
        'languages': [assoc.language.name for assoc in user.languages],
        'learningLanguages': [assoc.language.name for assoc in user.learningLanguages],
        'hometown': user.hometown,
        'location': user.location
        } for (user, score) in sorted_users])


@app.route('/languagesToLearn')
def languages_to_learn():
    user = session.query(User).filter_by(facebook_id=login_session['facebook_id']).one()
    languages = [assoc.language for assoc in user.learningLanguages]
    return json.dumps([language.name for language in languages])


@app.route('/updateLearn', methods = ['POST'])
def update_learn():
    if request.method == 'POST':
        user = session.query(User).filter_by(facebook_id=login_session['facebook_id']).one()
        language_ids = request.form.getlist('learnLanguages')
        session.query(LearningLanguageAssociation).filter_by(user=user).delete()
        for language_id in language_ids:
            language = session.query(Language).filter_by(id=language_id).one()
            session.add(LearningLanguageAssociation(language=language, user=user))
            session.commit()
        return redirect(url_for('my_profile'))


if __name__ == '__main__':
    app.run()