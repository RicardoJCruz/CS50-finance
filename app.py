import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # Request symbol
        symbol = request.form.get("symbol")

        # Verify symbol
        if not symbol or lookup(symbol) == None:
            return apology("Symbol is empty or is invalid")

        # Get shares and try casting
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return apology("Invalid number of shares")

        # Verify shares
        if shares <= 0:
            return apology("Invalid number of shares")

        # 
        price = lookup(symbol)["price"]
        rows = db.execute("SELECT cash from users WHERE id = ?", session["user_id"])
        if (price * shares) < rows[0]["cash"]:
            db.execute("INSERT INTO transactions (user_id, movement, symbol, shares, price, date) VALUES (?, 'buy', ?, ?, ?, datetime())", session["user_id"], symbol, shares, price)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", rows[0]["cash"] - (price * shares), session["user_id"])
        else:
            return apology("Number of shares cannot be afford at the current price")
    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        if symbol != None:
            return render_template("quoted.html", name=symbol["name"], price=symbol["price"], symbol=symbol["symbol"])
        else:
            return apology("Invalid symbol")
    
    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        confirmation = request.form.get("confirmation")
        if not username or db.execute("SELECT username FROM users WHERE username = ?", username):
            return apology("Username is empty or already taken")
        
        elif not password or not confirmation or password != confirmation:
            return apology("Password is empty or do not match")
        
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password))
    
    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    return apology("TODO")
