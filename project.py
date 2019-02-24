# Use the important librarys such as Flask, sqlalchey and python lib.
import datetime
from flask import Flask, render_template, request, redirect, jsonify, url_for
from flask import flash
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from db_setup import Base, Catalog, Item, User
from flask import session as login_session
import random
import string
import json
from flask import make_response
import requests

app = Flask(__name__)

engine = create_engine('sqlite:///catalogitem.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Login by username and email.
@app.route('/login')
def showLogin():
    name = request.form.get("name")
    email = request.form.get("email")
    return render_template('login.html', name=name, email=email)


# Try to Connect.
@app.route('/connect', methods=['POST'])
def connect():
    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['name']
    output += '!</h1>'
    flash("you are now logged in as %s" % login_session['name'])
    return output
    return render_template('catalog.html')


# User Helper 3 Functions.
def createUser(login_session):
    newUser = User(name=login_session['name'], email=login_session[
                   'email'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# This function for disconnect and logout.
@app.route('/disconnect')
def disconnect():
        return 'Disconnect'


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
            'publiccatalog.html', catalog=catalog, item=item)
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
    if 'username' not in login_session:
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
