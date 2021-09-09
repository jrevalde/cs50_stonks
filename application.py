import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")




@app.route("/add_cash", methods=["GET", "POST"])
@login_required
def add_cash():
    """Add cash to user table"""
    if request.method == "GET":
        return render_template("add_cash.html")
    else:
        #check for input errors
        if not request.form.get("cash"):
            return apology("please type cash to add.")

        db.execute("UPDATE users SET cash = cash + :amount WHERE id = :user_id", amount = request.form.get("cash"), user_id = session["user_id"])

        return redirect("/")






@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    #sum query returns total shares and symbol
    shares_sum = db.execute("""
        SELECT symbol, SUM(shares) as totalshares
        FROM history
        WHERE user_id = :user_id
        GROUP BY symbol
        HAVING totalshares > 0;
    """, user_id = session["user_id"] )
    sum_list = []
    cash_total = 0

    #use lookup for each symbol in shares_sum to use for the index table
    for row in shares_sum:
        symbol_name = lookup(row["symbol"])
        sum_list.append({"symbol": symbol_name["symbol"], "name": symbol_name["name"], "shares": row["totalshares"], "price": usd(symbol_name["price"]), "total": usd(symbol_name["price"] * row["totalshares"])})

        cash_total += symbol_name["price"] * row["totalshares"]

    total_cash_rows = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session["user_id"])

    cash = total_cash_rows[0]["cash"]

    #the current total worth of the owned shares + the users current cash
    cash_total += cash

    return render_template("index.html", sum_list = sum_list, cash = usd(cash), cash_total = usd(cash_total))











@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""


    if request.method == "GET":

        return render_template("buy.html")

    else:
        symbol = request.form.get("symbol").upper()
        symbol_dict = lookup(symbol)

        shares = request.form.get("shares")
        user_id = session["user_id"]
        shares_int = int(shares)

        #check the form inputs for errors e.g nothing entered in the fields, invalid symbols, invalide number of shares etc..
        if not request.form.get("symbol"):
            return apology("Please enter a symbol")
        elif symbol_dict is None:
            return apology("please return valid symbol")
        elif not request.form.get("shares"):
            return apology("Please input amount of shares you want to buy")
        elif not request.form.get("shares").isdigit():
            return apology("Please enter only number")
        elif shares_int < 0:
            return apology("please return only positive number")


        #checking if there's enuff money for purchase
        users_cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = user_id)
        cash = users_cash[0]["cash"]

        current_cash = cash - shares_int * symbol_dict["price"]

        if current_cash < 0:
            return apology("not enuff cash pls")

        #update users total cash to the new amount
        db.execute("UPDATE users SET cash = :new_cash WHERE id = :user_id", new_cash = current_cash, user_id = user_id)

        #update the transaction history
        db.execute("""INSERT INTO history(user_id, symbol, shares, price) VALUES(:user_id, :symbol, :shares, :price) ;"""
        , user_id = user_id, symbol = symbol, shares = shares, price = symbol_dict["price"])

        return redirect("/")








@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    user_id = session["user_id"]
    history = db.execute("""SELECT symbol, shares, price, transacted FROM history WHERE user_id = :user_id  """, user_id = user_id)
    for i in range(len(history)):
        history[i]["price"] = usd(history[i]["price"])
    return render_template("history.html", history = history)







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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists
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
    if request.method == "GET":
        return render_template("quote.html")

    else:

        #check first if symbol was typed in
        if not request.form.get("symbol"):
            return apology("must type add symbol into the symbol field ")
        #look up stop symbol by calling up the lookup function and displaying the results

        #declaring symbol variable for convenience
        symbol = request.form.get("symbol")

        #lookup the value of relative stock (python dictionary format)
        lookup_dict = lookup(symbol)

        #just checks if a valid symbol was added
        if lookup_dict == None:
            return apology("sorry symbol is invalid")

        #print out data to see what comes back
        return render_template("quoted.html", quote = lookup_dict)


#quoted app route to print out the results in look up dict
#@app.route("/quoted", methods = ["GET"])
##def quoted():
    #if request.method == "GET":
        #return render_template("quoted.html")






@app.route("/register", methods=["GET", "POST"])
def register():
    #forget any user id
    session.clear()

    """Register user"""
    if request.method == "POST":

        #error check the form submission
        if not request.form.get("username"):
            return apology("please type in a username")
        elif not request.form.get("password"):
            return apology("please type in a password")
        elif request.form.get("password") != request.form.get("password-confirm"):
            return apology("password-confirm does not match password")

        #if there are no errors

        #hash the user's password
        password_hash = generate_password_hash(request.form.get("password"))
        try:

            result = db.execute("INSERT INTO users(username, hash) VALUES(:username, :password_hash)"
            , username = request.form.get("username"), password_hash = password_hash)

        except:
            return apology("username already exists", 403)

        if result is None:
            return apology("username is taken", 403)

        session["user_id"] = result

        return redirect("/")

    else:
        return render_template("register.html")


        # Query database for username
        #rows = db.execute("SELECT * FROM users WHERE username = :username",
                          #username = request.form.get("username"))


        #if len(rows) != 1:
            #return apology("username already exists")

        #else:
            #inserting the username and hash number into the finance.db
            #db.execute("INSERT INTO users(username, hash) VALUES(:username, :password_hash)", username = username, password_hash = password_hash)

            #store user info into session
            #session["user_id"] = rows[0]["id"]

            #redirect user back to the / or index

            #return redirect("/")





@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""


    if request.method == "GET":

        #just a step for displaying the the symbols that the users has shares with.
        rows = db.execute("""SELECT symbol FROM history WHERE user_id = :user_id GROUP BY symbol HAVING SUM(shares) > 0;""", user_id = session["user_id"])
        return render_template("sell.html", symbols = [row["symbol"] for row in rows])
    else:
        user_id = session["user_id"]
        symbol = request.form.get("symbol").upper()
        symbol_dict = lookup(symbol)

        shares = request.form.get("shares")

        shares_int = int(shares)
        #check the form inputs for errors e.g nothing entered in the fields, invalid symbols, invalide number of shares etc..
        if not request.form.get("symbol"):
            return apology("Please enter a symbol")
        elif symbol_dict is None:
            return apology("please return valid symbol")
        elif not request.form.get("shares"):
            return apology("Please input amount of shares you want to buy")
        elif not request.form.get("shares").isdigit():
            return apology("Please enter only number")
        elif shares_int < 0:
            return apology("please return only positive number")

        #this step checks if user is trying to sell more shares than what they have available

        #this query is for getting the sum amount of shares the user has for each symbol.
        rows = db.execute("""SELECT symbol, SUM(shares) as totalshares FROM history WHERE user_id = :user_id GROUP BY symbol HAVING totalshares > 0; """,
        user_id = user_id)


        for row in rows:
            if row["symbol"] == symbol:
                if shares_int > row["totalshares"]:
                    return apology("trying to sell more shares than you have")

        #updating the users cash to reflect the amount added from the sale.
        users_cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = user_id)
        cash = users_cash[0]["cash"]

        current_cash = cash + shares_int * symbol_dict["price"]


        db.execute("UPDATE users SET cash = :new_cash WHERE id = :user_id", new_cash = current_cash, user_id = user_id)

        #update the transaction history
        db.execute("""INSERT INTO history(user_id, symbol, shares, price) VALUES(:user_id, :symbol, :shares, :price);"""
        , user_id = user_id, symbol = symbol, shares = -1 * shares_int, price = symbol_dict["price"])



        return redirect("/")






def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
