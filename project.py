# Use the important libraries such as Flask, sqlalchemy and python lib.
import random
import string
import json
import os
import datetime
import httplib2
import requests
from flask import Flask, render_template, request, redirect, jsonify, \
    url_for, flash, make_response
from flask import session as login_session
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from db_setup import Base, Catalog, Item, User
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError


app = Flask(__name__)

#engine = create_engine('sqlite:///catalogitem.db')
engine = create_engine('postgresql://catalog:password@localhost/catalog')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Helper Functions.
def create_user(login_session):
    """Grab username, email and picture from login session"""
    new_user = User(name=login_session['username'],
                    email=login_session['email'],
                    picture=login_session['picture'])
    session.add(new_user)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def get_user_id(user_id):
    """Grab users id from db and return it"""
    user = session.query(User).filter_by(id=user_id).one()
    return user


def get_user_email(email):
    """Grab users email from db and return it"""
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# JSON Loads.
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog App"


# User Register form.
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        picture = request.form.get("picture")
        session.execute("INSERT INTO user(name, email, picture) VALUES(\
            :name,:email,:picture)", {
                "name": name, "email": email, "picture": picture
                })
        session.commit()
        return redirect(url_for("showLogin"))
    else:
        return render_template('register.html')


# Create anti-forgery state token and login form.
@app.route('/login', methods=["GET", "POST"])
def showLogin():
    state = ''.join(
        random.choice(
            string.ascii_uppercase + string.digits) for x in range(32))
    login_session['state'] = state
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")

        namedata = session.execute("SELECT name FROM user WHERE name=: name", {
            "name": name}).fetchone()
        emaildata = session.execute(
            "SELECT email FROM user WHERE email=: email", {
                "email": email}).fetchone()

        if namedata and emaildata is None:
            return render_template('login.html')
        else:
            return redirect(url_for('showCatalog'))
    else:
        return render_template('login.html', STATE=state)


# Google connect.
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code, now compatible with Python3
    request.get_data()
    code = request.data.decode('utf-8')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    # Submit request, parse response - Python3 compatible
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    str_response = response.decode('utf-8')
    result = json.loads(str_response)

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    # See if user exists, if not, make new one
    user_id = get_user_email(data['email'])
    if not user_id:
        user_id = create_user(login_session)
    login_session['user_id'] = user_id

    output = ('')
    output += ('<h1>Welcome, ')
    output += login_session['username']
    output += ('!</h1>')
    output += ('<img src="')
    output += login_session['picture']
    output += (' " style = "width: 300px; height: 300px;border-radius: 150px;\
        -webkit-border-radius: 150px;-moz-border-radius: 150px;"> ')
    flash("you are now logged in as %s" % login_session['username'])
    return output


# Google DISCONNECT Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Disconnect Route from database.
@app.route('/disconnect')
def disconnect():
    """Disconnect based on provider"""
    # Check provider and then call function to log user out
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalog'))
    else:
        flash("You were not logged in to begin with!")
        return redirect(url_for('showCatalog'))


# Show all catalog and items APIs by JSON.
@app.route('/catalog.json')
def catalogJSON():
    catalog = session.query(Catalog).order_by(Catalog.name.asc()).all()
    catalogJSON = []
    for catalog in catalog:
        cat = catalog.serialize
        item = session.query(Item).filter(
            Item.catalog_name == catalog.name).all()
        itemJSON = []
        for item in item:
            itemJSON.append(item.serialize)
        cat['item'] = itemJSON
        catalogJSON.append(cat)
    return jsonify(catalog=[catalogJSON])


# Show all catalog and latest items page.
@app.route('/')
@app.route('/catalog/')
def showCatalog():
    catalog = session.query(Catalog).order_by(asc(Catalog.name))
    item = session.query(Item).order_by(desc(Item.date)).limit(4)
    if 'username' not in login_session:
        return render_template(
            'publicCatalog.html', catalog=catalog, item=item)
    else:
        return render_template('catalog.html', catalog=catalog, item=item)


# Show a catalog items page.
@app.route('/catalog/<string:catalog_name>/items/')
def showItem(catalog_name):
    cataloges = session.query(Catalog).order_by(asc(Catalog.name))
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    item = session.query(Item).filter_by(catalog_name=catalog_name).all()
    return render_template(
        'item.html', cataloges=cataloges, item=item, catalog=catalog)


# Description an item.
@app.route('/catalog/<string:catalog_name>/<string:item_name>/')
def descItem(catalog_name, item_name):
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    item = session.query(Item).filter_by(name=item_name).one()
    creator = get_user_id(item.user_id)
    if 'username' not in login_session or creator.id != login_session[
        'user_id'
    ]:
        return render_template(
            'publicitemDesc.html', item=item, catalog=catalog)
    else:
        return render_template('itemDesc.html', item=item, catalog=catalog)


# Create a new item.
@app.route('/catalog/new/', methods=['GET', 'POST'])
def newItem():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        if (request.form['name'] and
                request.form['description'] and
                request.form['catalog']):
            newItem = Item(
             name=request.form['name'],
             description=request.form['description'],
             date=datetime.datetime.utcnow(),
             catalog=session.query(Catalog)
             .filter_by(name=request.form['catalog']).one(),
             user_id=login_session['user_id'])
            session.add(newItem)
            session.commit()
            flash("new item created!")
            return redirect(url_for('showCatalog'))
        else:
            flash("Please check form again for empty fields")
            catalog = session.query(Catalog).all()
            return render_template('newitem.html',
                                   catalog=catalog)
    else:
        catalog = session.query(Catalog).all()
        return render_template('newitem.html',
                               catalog=catalog)


# Edit an item.
@app.route('/catalog/<string:catalog_name>/<string:item_name>/edit/',
           methods=['GET', 'POST'])
def editItem(catalog_name, item_name):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Item).filter_by(name=item_name).one()
    if login_session['user_id'] != editedItem.user_id:
        return "<script>function myFunction() {alert('You are not authorized\
         toedit items, Please login');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        session.add(editedItem)
        session.commit()
        flash("The Item has been edited")
        return redirect(url_for('showCatalog', catalog_name=catalog_name))
    else:
        return render_template(
            'edititem.html', catalog_name=catalog_name,
            item_name=item_name,
            item=editedItem
            )


# Delete an item.
@app.route('/catalog/<string:catalog_name>/<string:item_name>/delete/',
           methods=['GET', 'POST'])
def deleteItem(catalog_name, item_name):
    if 'username' not in login_session:
        return redirect('/login')
    catalog = session.query(Catalog).filter_by(catalog_name=catalog_name).one()
    itemToDelete = session.query(Item).filter_by(name=item_name).one()
    if login_session['user_id'] != catalog.user_id:
        return "<script>function myFunction() {alert('You are not authorized to\
         delete items, please login');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("The Item has been deleted")
        return redirect(url_for('showCatalog', catalog_name=catalog_name))
    else:
        return render_template('deleteItem.html', item=itemToDelete)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
