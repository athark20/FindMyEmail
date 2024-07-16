from flask import Flask, render_template, request, redirect, url_for, session
import requests
import json
import stripe

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your own secret key

# Stripe API keys
stripe.api_key = 'your_stripe_secret_key'

# Replace with your People Data Labs API key
API_KEY = 'b010fab23f11855e95b86af706e1adc0cf12fc24de835ca4d6276b9055baad41'

# Mock user data
users = {
    "admin": {"password": "adminpass", "is_admin": True, "subscribed": True},
    "user": {"password": "userpass", "is_admin": False, "subscribed": False}
}

@app.route('/')
def index():
    user = None
    if 'username' in session:
        user = users.get(session['username'])
    return render_template('index.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)
        if user and user['password'] == password:
            session['username'] = username
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid username or password")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            return render_template('signup.html', error="Username already exists")
        users[username] = {"password": password, "is_admin": False, "subscribed": False}
        session['username'] = username
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/enrich', methods=['POST'])
def enrich():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = users[session['username']]
    data = request.form.to_dict()
    if not data.get('name') and not data.get('phone'):
        return render_template('index.html', error="Either Name or Phone number is required", user=user)

    enriched_data = call_enrichment_api(data)
    required_data = extract_required_data(enriched_data)
    return render_template('index.html', data=[required_data], user=user)

def call_enrichment_api(data):
    url = 'https://api.peopledatalabs.com/v5/person/enrich'
    headers = {'Content-Type': 'application/json', 'X-API-Key': API_KEY}
    response = requests.post(url, json=data, headers=headers)
    return response.json().get('data', {})

def extract_required_data(data):
    emails = [email['address'] for email in data.get('emails', [])]
    addresses = [address['street_address'] for address in data.get('street_addresses', [])]
    return {
        'emails': emails,
        'addresses': addresses
    }

@app.route('/checkout')
def checkout():
    session['payment_intent_id'] = None
    intent = stripe.PaymentIntent.create(
        amount=1000,  # amount in cents
        currency='usd',
        metadata={'integration_check': 'accept_a_payment'}
    )
    session['payment_intent_id'] = intent['id']
    return render_template('checkout.html', client_secret=intent['client_secret'])

@app.route('/confirm_payment', methods=['POST'])
def confirm_payment():
    if 'username' not in session:
        return redirect(url_for('login'))

    payment_intent_id = session.get('payment_intent_id')
    if payment_intent_id:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        if intent['status'] == 'succeeded':
            users[session['username']]['subscribed'] = True
            return redirect(url_for('index'))

    return redirect(url_for('checkout'))

if __name__ == '__main__':
    app.run(debug=True)
