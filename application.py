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


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = db.execute("SELECT symbol, shares FROM stocks WHERE user_id=:userid", userid=session.get("user_id")) 
    print(f"STOCKS {stocks}")
    
    balance= db.execute("SELECT cash FROM users WHERE id=:userid", userid=session.get("user_id"))
    
    money=float(balance[0]["cash"])
    
    #https://cs50.stackexchange.com/questions/30264/pset7-finance-index
    for stock in stocks:
        symbol=str(stock["symbol"])
        shares=int(stock["shares"])
        quote_stock= lookup(stock["symbol"])
        stock["price"]= quote_stock["price"]
        price=stock["price"]
        stock["holdings"]= float(shares*price)
        holdings=stock["holdings"]
        
    
    return render_template("index.html", stocks=stocks, money=money)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if not request.method=="POST":
        return render_template("buy.html")
    if request.method=="POST":    
        shares = int(request.form.get("shares"))
        if not request.form.get("symbol"):
            return apology("Please enter a stock symbol", 403)
        
        if not request.form.get("shares"):
            return apology("Please enter a stock symbol", 403)
        
        if shares < 0:
            return apology("Please enter a valid number of shares", 403)
        
        else:
            stock= lookup(request.form.get("symbol")) 
            price= float(stock["price"]) #gets stock price  
            
            userbalance= db.execute("SELECT cash FROM users WHERE id=:userid", userid= session.get("user_id")) 
            
            print(userbalance)
            cash= float(userbalance[0]["cash"])
            
            cost= float(price*shares)
            
            if cash-cost <0:
                return apology("You cannot afford this stock")
            
            elif cash-cost >0:    
                balance= db.execute("UPDATE users SET cash = :cash WHERE id = :userid", userid=session.get("user_id"), cash=cash-cost)                    
                stock= db.execute("INSERT INTO stocks(user_id, symbol, shares) VALUES(:userid, :symbol, :shares)", userid= session.get("user_id"), symbol=request.form.get("symbol"), shares=request.form.get("shares"))
                
                print(balance)
                print(stock)
                return redirect("/")
            
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
        rows = db.execute("SELECT * FROM users WHERE username = :username",  username=request.form.get("username"))

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
    if not request.method =="POST":
        return render_template("quote.html")
    
    if request.method =="POST":
        stockinfo = lookup(request.form.get("symbol"))
        name=stockinfo["name"]
        price=stockinfo["price"]
        symb=stockinfo["symbol"]
        return render_template("quoted.html", name=name, price=price, symb=symb)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    
    if request.method == "POST":
        if not request.form.get("username"): 
            return apology("Please enter a username", 403)

        if not request.form.get("password"):
            return apology("Please enter a password", 403)
    
        if not request.form.get("confirmation"):
            return apology("Please confirm your password", 403)
    
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Make sure that your password is entered correctly", 403)
        
        else:
            username = request.form.get("username")
            password = request.form.get("password")
            
            if len(password)>=6:
                hashedpassword = generate_password_hash(password)  
                db.execute("INSERT INTO users(username, hash) VALUES(:username, :hashedpassword)", username=username, hashedpassword=hashedpassword)      
                return render_template("success.html")
            
            elif len(password)<6:
                return apology("Please choose a longer password")
                        
    if not request.method== "POST":
        return render_template("register.html")
    
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""            
    if not request.method=="POST":
        userstocks= db.execute("SELECT symbol FROM stocks WHERE user_id=:userid", userid=session.get("user_id"))
        print(userstocks)
                            
        return render_template("sell.html", userstocks=userstocks)
    
    if request.method=="POST":
        if not request.form.get("symbol"):
            return apology("Please select a stock symbol to sell")
    
        if not request.form.get("shares"):
            return apology("Please enter a valid number of shares to sell")
        if request.form.get("shares")=="0":
            return apology("Please enter a valid number of shares to sell")
        else:
            stocksymbol= db.execute("SELECT symbol FROM stocks WHERE user_id=:userid AND symbol=:symbol", userid=session.get("user_id"), symbol=request.form.get("symbol"))
    
            #gets the stock price and shares they want to sell
            stock=lookup(request.form.get("symbol"))
            price=float(stock["price"])
            shares=int(request.form.get("shares"))
            balance= db.execute("SELECT cash FROM users WHERE id=:userid", userid=session.get("user_id"))
            print(balance)
            cash=float(balance[0]["cash"])
            holdings=float(shares*price) #amount of $ they will regain
    
            #updates their cash balance
            db.execute("UPDATE users SET cash=:cash WHERE id=:userid", userid=session.get("user_id"), cash= cash+holdings)
            
            #selects the shares that they own of the company
            stockshares= db.execute("SELECT SUM(shares) FROM stocks WHERE user_id=:userid AND symbol=:stocksymbol", userid=session.get("user_id"), stocksymbol=request.form.get("symbol"))
            print(stockshares)
            #updates the shares
            x= int(stockshares[0]["SUM(shares)"])
            shares=int(x-shares)
            
            db.execute("UPDATE stocks SET shares=:shares WHERE id=:userid AND symbol=:stocksymbol", shares=shares, userid=session.get("user_id"), stocksymbol=request.form.get("symbol"))    
            return redirect("/") 

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
