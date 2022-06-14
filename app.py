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
    # User stocks
    stocks = db.execute("SELECT symbol, shares FROM portfolios WHERE user_id = ?", session["user_id"])
    
    # User cash
    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

    # Add 'total sum' to cash dictionary
    cash[0]["total"] = cash[0]["cash"]
    
    # Add "price" & "sum of stocks" to stocks dictionary
    # and update "total" in cash dictionary
    for stock in stocks:
        stock["price"] = lookup(stock["symbol"])["price"]
        stock["sum"] = stock["price"] * stock["shares"]
        cash[0]["total"] += stock["price"] * stock["shares"]

    """Show portfolio of stocks"""
    return render_template("index.html", stocks=stocks, cash=cash[0])


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # Request symbol
        symbol = request.form.get("symbol").upper()

        # Verify symbol
        if not symbol or lookup(symbol) == None:
            return apology("Symbol is empty or is invalid")

        # Get shares and try casting
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return apology("Invalid number of shares")

        # Verify shares
        if shares < 1:
            return apology("Invalid number of shares")

        # Get price of stock
        price = lookup(symbol)["price"]

        # Get cash of the user
        rows = db.execute("SELECT cash from users WHERE id = ?", session["user_id"])

        # Verify user has enough cash to buy
        if (price * shares) < rows[0]["cash"]:
            # add stock if not in table
            if not db.execute("SELECT * FROM portfolios WHERE symbol = ? AND user_id = ?", symbol, session["user_id"]):
                db.execute("INSERT INTO portfolios (user_id, symbol, shares) VALUES (?, ?, ?)", session["user_id"], symbol, shares)
            # update stock if already exists
            else:
                db.execute("UPDATE portfolios SET shares = shares + ? WHERE symbol = ? AND user_id = ?", shares, symbol, session["user_id"])
            # add transaction and update user cash
            db.execute("INSERT INTO transactions (user_id, movement, symbol, shares, price, date) VALUES (?, 'buy', ?, ?, ?, datetime())", session["user_id"], symbol, shares, price)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", rows[0]["cash"] - (price * shares), session["user_id"])
        else:
            return apology("Number of shares cannot be afford at the current price")
    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = ?", session["user_id"])
    return render_template("history.html", transactions=transactions)


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
    rows = db.execute("SELECT symbol, shares FROM portfolios WHERE user_id = ?", session["user_id"])
    if request.method == "POST":

        # Get symbol and number of stocks
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")

        # Ensure a symbol and a number were provided
        if not symbol or not shares:
            return apology("A stock and a number of shares are required")

        # Cast shares string to number
        try:
            shares = int(shares)
        except ValueError:
            return apology("Invalid number of shares")
            
        # Verify shares is a positive number
        if shares < 1:
            return apology("Invalid number of shares")

        # Ensure user has that stock
        for row in rows:
            if symbol == row["symbol"]:
                # Ensure user has amount of stocks
                if shares <= row["shares"]:
                    db.execute("UPDATE portfolios SET shares = shares - ? WHERE symbol = ? AND user_id = ?", shares, symbol, session["user_id"])
                    db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", lookup(symbol)["price"] * shares, session["user_id"])
                    db.execute("INSERT INTO transactions (user_id, movement, symbol, shares, price, date) VALUES (?, 'sell', ?, ?, ?, datetime())", session["user_id"], symbol, shares, lookup(symbol)["price"])
                    # Delete empty entries
                    db.execute("DELETE FROM portfolios WHERE shares = 0 AND user_id = ?", session["user_id"])
                    return redirect("/sell")
                else:
                    return apology("You don't own that many shares of that stock")
        return apology("You don't have shares of that stock")
                


    return render_template("sell.html", rows=rows)
