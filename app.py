from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db\\setni.db"
app.secret_key = "super secret key"
app.config["SESSION_TYPE"] = "filesystem"


db = SQLAlchemy(app=app)
login_manager = LoginManager(app=app)


# Entities

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, unique=True)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String)


class Place(db.Model):
    __tablename__ = "place"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, unique=True)
    description = db.Column(db.String)
    location = db.Column(db.String)
    category = db.Column(db.String)
    rating = db.Column(db.Float)  # hard-coded
    number_of_reviews = db.Column(db.Integer)  # hard-coded
    path_to_image = db.Column(db.String)
    price = db.Column(db.Integer)


class Reservation(db.Model):
    __tablename__ = "reservation"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer)  # Foreign key to User
    place_id = db.Column(db.Integer)  # Foreign key to Place
    number_of_people = db.Column(db.Integer)
    date = db.Column(db.String)
    time = db.Column(db.String)
    price_per_person = db.Column(db.Integer)

#

# Routes

@app.route('/')
def index():
    popular_places = db.session.query(Place).order_by(Place.rating.desc()).all()[:6]
    return render_template("index.html", popular_places=popular_places)


@app.route('/places')
def places():
    query = request.args.get("query")
    query = query if query is not None else ""
    category = request.args.get("category")
    category = int(category) if category is not None else 0
    location = request.args.get("location")
    location = int(location) if location is not None else 0

    categories = ["Сите", "Бар", "Ресторан", "Ноќен клуб"]
    locations = ["Сите", "Аеродром", "Бутел", "Гази Баба", "Ѓорче Петров", "Карпош", "Кисела Вода", "Сарај", "Центар",
                 "Чаир", "Шуто Оризари"]

    if category != 0 and location != 0:
        places = db.session.query(Place) \
            .filter(Place.name.contains(query), Place.category == categories[category],
                    Place.location == locations[location]).all()
    elif category != 0:
        places = db.session.query(Place).filter(Place.name.contains(query), Place.category == categories[category])\
            .all()
    elif location != 0:
        places = db.session.query(Place).filter(Place.name.contains(query), Place.location == locations[location]).all()
    else:
        places = db.session.query(Place).filter(Place.name.contains(query)).all()

    bars = [p for p in places if p.category == "Бар"]
    restaurants = [p for p in places if p.category == "Ресторан"]
    clubs = [p for p in places if p.category == "Ноќен клуб"]

    data = {"bars": bars, "restaurants": restaurants, "clubs": clubs, "query": query, "category": category,
            "location": location}
    return render_template("places.html", data=data)


@app.route('/place/<placeId>')
def place(placeId):
    placeId=int(placeId)
    place = db.session.query(Place).filter(Place.id == placeId).first()
    reservation = None
    if current_user.is_authenticated:
        reservation = db.session.query(Reservation)\
            .filter(Reservation.user_id == current_user.id, Reservation.place_id == place.id).first()
        if reservation:
            reservation.hour = reservation.time[:2]
            reservation.minute = reservation.time[3:]
    return render_template("place.html", place=place, reservation=reservation)


@app.route('/reserve', methods=['POST'])
@login_required
def reserve():
    number_of_people = int(request.form.get("numberOfPeople"))
    date = request.form.get("date")
    hour = request.form.get("hour")
    hour = "00" if hour == "0" else hour
    minute = request.form.get("minute")
    minute = "00" if minute == "0" else minute
    place_id = request.form.get("placeId")
    price_per_person = request.form.get("pricePerPerson")

    db.session.add(Reservation(user_id=current_user.id, place_id=place_id, number_of_people=number_of_people,
                               date=date, time=hour + ":" + minute, price_per_person=price_per_person))
    db.session.commit()

    return redirect(url_for("reservations"))


@app.route("/cancel", methods=['POST'])
@login_required
def cancel():
    reservation_id = request.form.get("reservationId")
    place_id = request.form.get("placeId")
    go_to = request.form.get("goTo")
    db.session.query(Reservation).filter(Reservation.id == reservation_id).delete()
    db.session.commit()
    if go_to == "myReservations":
        return redirect("/reservations")
    else:
        return redirect("/place/" + place_id)


@app.route("/reservations")
@login_required
def reservations():
    reservations = db.session.query(Reservation).filter(Reservation.user_id == current_user.id).all()
    for reservation in reservations:
        place = db.session.query(Place).filter(Place.id == reservation.place_id).first()
        reservation.place = place
    reservations = list(reversed(reservations))
    return render_template("reservations.html", reservations=reservations)


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/contact')
def contact():
    return render_template("contact.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form.get("inputUsername")
        email = request.form.get("inputEmail")
        password = request.form.get("inputPassword")

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get("inputEmail")
        password = request.form.get("inputPassword")

        user = User.query.filter(User.email == email).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for("index"))
        else:
            return render_template("login.html", failed=True)

    return render_template("login.html")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# Login helpers

@login_manager.user_loader
def load_user(user_id):
    """Check if user is logged-in on every page load."""
    if user_id is not None:
        return User.query.get(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to Login page."""
    return redirect(url_for("login"))

#

@app.before_first_request
def init():
    db.create_all()
    if len(Place.query.all()) == 0:
        db.session.add(User(username="Евгениј", email="legenco@yahoo.com", password="ki123"))

        description = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut " \
                      "labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco " \
                      "laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in " \
                      "voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat " \
                      "cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Mattis " \
                      "vulputate enim nulla aliquet porttitor lacus. Porta non pulvinar neque laoreet suspendisse " \
                      "interdum consectetur libero. Quisque id diam vel quam elementum pulvinar etiam non. Ultricies " \
                      "leo integer malesuada nunc vel. Dictum fusce ut placerat orci. Purus non enim praesent " \
                      "elementum facilisis leo vel fringilla."
        db.session.add(Place(name="Рустикана 2.0", description=description, location="Центар", category="Ресторан",
                             rating=4.7, number_of_reviews=482, path_to_image="../static/img/Rustikana2.0.jpg",
                             price=0))
        db.session.add(Place(name="Систем Паб", description=description, location="Аеродром", category="Бар",
                             rating=4.6, number_of_reviews=166, path_to_image="../static/img/SistemPub.jpg",
                             price=150))
        db.session.add(Place(name="Мартини", description=description, location="Карпош", category="Ресторан",
                             rating=4.4, number_of_reviews=921, path_to_image="../static/img/Martini.jpg", price=0))

        db.session.commit()


if __name__ == '__main__':
    app.run(port=5000)
