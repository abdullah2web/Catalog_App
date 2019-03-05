import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_setup import Catalog, Base, Item, User

engine = create_engine('sqlite:///catalogitem.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object.
session = DBSession()

# create new user by python.
User1 = User(
    name="Abdullah ALShayie",
    email="abdullah2web@gmail.com",
    picture="http://style.anu.edu.au/_anu/4/images/placeholders\
    /person_8x10.png")
session.add(User1)
session.commit()

# item for football.
category1 = Catalog(name="Football")
session.add(category1)
session.commit()

listItem1 = Item(user_id=1, name="Ball", description="A ball is a round object\
 with various uses. It is used in ball games, where the play of the game\
 follows the state of the ball as it is hit kicked or thrown by players.\
 ", date=datetime.datetime.utcnow(), catalog=category1)
session.add(listItem1)
session.commit()

# item for Basketball.
category2 = Catalog(name="Basketball")
session.add(category2)
session.commit()

listItem2 = Item(user_id=1, name="Shoes", description="In 1903, a special\
 basketball shoe with suction cups to prevent slippage was added to the\
 official basketball uniform demonstrated in the Spalding catalog.\
 ", date=datetime.datetime.utcnow(), catalog=category2)
session.add(listItem2)
session.commit()

# item for Baseball.
category3 = Catalog(name="Baseball")
session.add(category3)
session.commit()

listItem3 = Item(user_id=1, name="Bat", description="A baseball bat is a smooth\
 wooden or metal club used in the sport of baseball to hit the ball after it\
 is thrown by the pitcher.\
 ", date=datetime.datetime.utcnow(), catalog=category3)
session.add(listItem3)
session.commit()

# item for Snowboarding.
category4 = Catalog(name="Snowboarding")
session.add(category4)
session.commit()

listItem4 = Item(user_id=1, name="Snowboard", description="Snowboards are\
 boards where both feet are secured to the same board, which are wider than\
 skis, with the ability to glide on snow.\
 ", date=datetime.datetime.utcnow(), catalog=category4)
session.add(listItem4)
session.commit()

# When finish will print added items.
print("added items!")
