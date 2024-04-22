from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import os
import datetime
import random
 
app = Flask(__name__)
app.config['SECRET_KEY'] = 'team2'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:eadgbe21@localhost:3306/stocks'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # Hashed password for security
    cash_balance = db.Column(db.Float, default=0.0)
    is_admin = db.Column(db.Boolean, default=False)
 
    def deposit_cash(self, amount):
        self.cash_balance += amount
        db.session.commit()

    def withdraw_cash(self, amount):
        if self.cash_balance >= amount:
            self.cash_balance -= amount
            db.session.commit()
            return True
        else:
            return False

    def set_market_hours(self, open_time, close_time):
        if self.is_admin:
            # market_hours is a global variable
            market_hours['open'] = open_time
            market_hours['close'] = close_time
            return True
        else:
            return False

    def set_market_schedule(self, open_days):
        if self.is_admin:
            # market_schedule is a global variable
            market_schedule['open_days'] = open_days
            return True
        else:
            return False

    def cancel_order(self, transaction_id):
        transaction = Transaction.query.get(transaction_id)
        if transaction and transaction.user_id == self.id and not transaction.executed:
            db.session.delete(transaction)
            db.session.commit()
            return True
        else:
            return False

    def view_portfolio(self):
        return self.stocks

# market hours and schedule
market_hours = {
    'open': datetime.time(9, 00),  # 9:00 AM
    'close': datetime.time(16, 0)  # 4:00 PM
}

market_schedule = {
    'open_days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
}

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    ticker_symbol = db.Column(db.String(10), unique=True, nullable=False)
    volume = db.Column(db.Integer, nullable=False) # Volume of the stock available for trading.
    price = db.Column(db.Float, nullable=False) 

    def update_price(self):
        self.price = self.price * random.uniform(0.95, 1.05)
        db.session.commit()

    # Relationship with Stock model by using a secondary table
    stocks = db.relationship('Stock', secondary='user_stock', backref=db.backref('users', lazy='dynamic'))

    def buy_stock(self, stock, quantity):
        # Check if the market is open
        current_time = datetime.datetime.now().time()
        current_day = datetime.datetime.now().strftime('%A')
        if current_day in market_schedule['open_days'] and market_hours['open'] <= current_time <= market_hours['close']:
            if self.cash_balance >= stock.price * quantity:
                self.cash_balance -= stock.price * quantity
                self.stocks.append(stock)
                new_transaction = Transaction(user_id=self.id, stock_id=stock.id, action='Buy', quantity=quantity, price=stock.price)
                db.session.add(new_transaction)
                db.session.commit()
                return True
            else:
                return False
        else:
             return False  # Market is not open

    def sell_stock(self, stock, quantity):
        # Check if the market is open
        current_time = datetime.datetime.now().time()
        current_day = datetime.datetime.now().strftime('%A')
        if current_day in market_schedule['open_days'] and market_hours['open'] <= current_time <= market_hours['close']:
            if stock in self.stocks:
                self.cash_balance += stock.price * quantity
                self.stocks.remove(stock)
                new_transaction = Transaction(user_id=self.id, stock_id=stock.id, action='Sell', quantity=quantity, price=stock.price)
                db.session.add(new_transaction)
                db.session.commit()
                return True
            else:
                return False  # Stock not owned by user
        else:
            return False  # Market is not open

# Create a secondary table for the many-to-many relationship between User and Stock
user_stock = db.Table('user_stock',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('stock_id', db.Integer, db.ForeignKey('stock.id'), primary_key=True)
)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    action = db.Column(db.String(10), nullable=False)  # Buy or Sell
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    executed = db.Column(db.Boolean, default=False)

    def execute(self):                  #buy and sell action checks if the user money to purchase the specified quantity of stock,
                                        #if they do, it deducts the cost from the user's cash balance and updates the stock's volume
        if not self.executed:
            stock = Stock.query.get(self.stock_id)
            user = User.query.get(self.user_id)
            if self.action == 'buy':
                if user.cash_balance >= stock.price * self.quantity:
                    user.cash_balance -= stock.price * self.quantity
                    stock.volume -= self.quantity
                    self.executed = True
                    db.session.commit()
                    return True
            elif self.action == 'sell':
                if stock in user.stocks:
                    user.cash_balance += stock.price * self.quantity
                    stock.volume += self.quantity
                    self.executed = True
                    db.session.commit()
                    return True
        return False

from flask import request, session, redirect, url_for, flash
from werkzeug.security import check_password_hash

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Query the database for the user
        user = User.query.filter_by(username=username).first()

        # Check if the user exists and the password is correct
        if user and check_password_hash(user.password, password):
            # Log the user in by storing their user id in the session
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password. Please try again.', 'failure')
            return redirect(url_for('login'))

    # Render the login form template
    return render_template("login.html")


# Initialize the database
def create_app():
    db.create_all()

    # Generate initial stock data
    def generate_initial_stocks():
        stocks_data = [
            {"company_name": "Apple Inc.", "ticker": "AAPL", "volume": 1000, "initial_price": 150.0},
            {"company_name": "Microsoft Corporation", "ticker": "MSFT", "volume": 800, "initial_price": 300.0},
            {"company_name": "Alphabet Inc.", "ticker": "GOOGL", "volume": 600, "initial_price": 2500.0},
            {"company_name": "Facebook, Inc.", "ticker": "FB", "volume": 700, "initial_price": 350.0}
        ]
        for stock_data in stocks_data:
            stock = Stock(**stock_data)
            stock.current_price = stock.initial_price  # Set current price initially
            db.session.add(stock)
        db.session.commit()

    # Check if initial stocks are already generated
    if not Stock.query.first():
        generate_initial_stocks()

# Random stock price generator
def update_stock_prices():
    stocks = Stock.query.all()
    for stock in stocks:
        fluctuation = random.uniform(-10, 10)  # Random fluctuation in percentage
        new_price = stock.current_price * (1 + fluctuation / 100)
        stock.current_price = round(new_price, 2)
    db.session.commit() 

# Define routes
@app.route("/")
def home():
    stocks = Stock.query.all()
    return render_template('index.html', stocks=stocks)
 
@app.route("/newacc")
def newacc():
    return render_template('newacc.html')


@app.route("/contact")
def contact():
    return render_template('contact.html')

@app.route("/trade", methods=['GET', 'POST'])
def trade():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        stock_ticker = request.form['stock_ticker']
        number_of_shares = int(request.form['number_of_shares'])
        action = request.form['action']  # Buy or sell
        user = User.query.get(session['user_id'])

        stock = Stock.query.filter_by(ticker=stock_ticker).first()
        if stock:
            total_cost = number_of_shares * stock.current_price
            if action == 'buy':
                if total_cost <= user.cash_balance:
                    # Deduct cash balance
                    user.cash_balance -= total_cost
                    # Update stock volume
                    stock.volume += number_of_shares
                    # Record transaction
                    transaction = Transaction(user_id=user.id, stock_id=stock.id, action='Buy', quantity=number_of_shares, price=stock.current_price)
                    db.session.add(transaction)
                    flash('Stock purchased successfully', 'success')
                else:
                    flash('Insufficient funds', 'failure')
            elif action == 'sell':
                if number_of_shares <= stock.volume:
                    # Add cash balance
                    user.cash_balance += total_cost
                    # Update stock volume
                    stock.volume -= number_of_shares
                    # Record transaction
                    transaction = Transaction(user_id=user.id, stock_id=stock.id, action='Sell', quantity=number_of_shares, price=stock.current_price)
                    db.session.add(transaction)
                    flash('Stock sold successfully', 'success')
                else:
                    flash('Insufficient shares to sell', 'failure')

    return render_template('trade.html')

@app.route("/portfolio")
def portfolio():
    return render_template('portfolio.html')

@app.route("/transaction")
def transaction():
    return render_template('transaction.html')

if __name__ == "__main__":
    with app.app_context():
        create_app()
        app.run(debug=True)
