from flask import (
    Flask, render_template,
    request, redirect, url_for,
    session, flash
)
import sqlite3
from functools import wraps

app = Flask(__name__)

#Secret key required for sessions and is changeable
app.secret_key = "super_secret_key"

DATABASE = "Lamphouse.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# USER AUTHENTICATION:
# To verify username/password from the Users table in the database I use login()
# Then after the session is created, we need to have a clear session using logout()
# The login_required decorator is used to protect routes that require authentication.

# --------- AUTH HELPERS ---------
def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            # not logged in, send to login page
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view

# --------- ROUTES ---------------------------------------------------

@app.route("/")
def home():
    # if logged in, go to dashboard, otherwise go to login
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM Users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user and user["password"] == password:
            # correct login
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Logged in successfully!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password", "error")

    # if GET or failed login, show the login form
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    # Example protected page
    return render_template("dashboard.html", username=session.get("username"))

#This is the Database Connection + the Clients list view from my table
# I use a helper function to connect to the sqlite database: get_db_connection()
# Then to query the Clients table and fetch all records ordered by last name and first name,
#  the function list_clients() is defined. This also renders the clients.html template,
# passing the retrieved clients data for display.
# --------- CLIENTS CRUD -----------------------

@app.route("/clients")
@login_required
def list_clients():
    conn = get_db_connection()
    clients = conn.execute(
        "SELECT * FROM Clients ORDER BY last_name, first_name"
    ).fetchall()
    conn.close()
    return render_template("clients.html", clients=clients)

#new_client() handles both GET and POST requests for adding a new client.
# On GET, it displays an empty form, On POST, it processes the form data - 
#-inserts a new record into the Clients table, then redirects back to the clients list with a success message.

@app.route("/clients/new", methods=["GET", "POST"])
@login_required
def new_client():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone = request.form.get("phone")

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO Clients (first_name, last_name, email, phone) VALUES (?, ?, ?, ?)",
            (first_name, last_name, email, phone)
        )
        conn.commit()
        conn.close()

        flash("New client added!", "success")
        return redirect(url_for("list_clients"))

    # if GET, show empty form
    return render_template("new_client.html")

@app.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def edit_client(client_id):
    conn = get_db_connection()
    client = conn.execute(
        "SELECT * FROM Clients WHERE client_id = ?",
        (client_id,)
    ).fetchone()

    if client is None:
        conn.close()
        flash("Client not found.", "error")
        return redirect(url_for("list_clients"))

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone = request.form.get("phone")

        conn.execute(
            "UPDATE Clients SET first_name = ?, last_name = ?, email = ?, phone = ? WHERE client_id = ?",
            (first_name, last_name, email, phone, client_id)
        )
        conn.commit()
        conn.close()

        flash("Client updated!", "success")
        return redirect(url_for("list_clients"))

    # if GET, show form with existing data
    conn.close()
    return render_template("edit_client.html", client=client)

@app.route("/clients/<int:client_id>/delete", methods=["POST"])
@login_required
def delete_client(client_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM Clients WHERE client_id = ?", (client_id,))
    conn.commit()
    conn.close()

    flash("Client deleted.", "info")
    return redirect(url_for("list_clients"))

#ROUTE protection:
# The @login_required decorator that is shown on all routes, ensures that only logged in users
# can have access to these pages. 
@app.route("/analytics")
@login_required
def analytics():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT P.package_name,
               SUM(I.subtotal + I.tax) AS total_revenue
        FROM Invoices I
        JOIN Packages P ON I.package_id = P.package_id
        GROUP BY P.package_id, P.package_name
        ORDER BY total_revenue DESC;
        """
    ).fetchall()
    conn.close()

    # Convert query result to plain Python lists for the chart
    labels = [row["package_name"] for row in rows]
    totals = [row["total_revenue"] for row in rows]

    return render_template("analytics.html", labels=labels, totals=totals)


if __name__ == "__main__":
    app.run(debug=True)
