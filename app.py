from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, TrackedItem, PriceHistory
from scraper import scrape_price, scrape_product
from scheduler import start_scheduler
from email_utils import send_verification_email, send_reset_email, verify_token

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-to-anything-secret-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///prices.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

start_scheduler(app)

@app.route('/')
@login_required
def dashboard():
    items = TrackedItem.query.filter_by(user_id=current_user.id).all()
    alerts = []
    for item in items:
        if item.current_price and item.target_price and item.current_price <= item.target_price:
            alerts.append(item)
    return render_template('dashboard.html', items=items, alerts=alerts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('register'))
        hashed = generate_password_hash(request.form['password'])
        user = User(email=email, password=hashed, is_verified=False)
        db.session.add(user)
        db.session.commit()
        base_url = request.host_url.rstrip('/')
        send_verification_email(email, base_url)
        flash('Account created! Please check your email to verify your account.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            if not user.is_verified:
                flash('Please verify your email before logging in.')
                return redirect(url_for('login'))
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Wrong email or password.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/verify-email/<token>')
def verify_email(token):
    email = verify_token(token, salt='email-verify')
    if not email:
        flash('Verification link is invalid or expired.')
        return redirect(url_for('login'))
    user = User.query.filter_by(email=email).first()
    if user:
        user.is_verified = True
        db.session.commit()
        flash('Email verified! You can now log in.')
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            base_url = request.host_url.rstrip('/')
            send_reset_email(email, base_url)
        flash('If that email exists a reset link has been sent.')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_token(token, salt='password-reset')
    if not email:
        flash('Reset link is invalid or expired.')
        return redirect(url_for('login'))
    if request.method == 'POST':
        user = User.query.filter_by(email=email).first()
        if user:
            user.password = generate_password_hash(request.form['password'])
            db.session.commit()
            flash('Password reset successfully! Please log in.')
            return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)

@app.route('/add-item', methods=['POST'])
@login_required
def add_item():
    url = request.form['url'].strip()
    name = request.form.get('name', '').strip() or 'Unknown product'
    target = float(request.form['target_price'])
    image_url = request.form.get('image_url', '').strip()
    product = scrape_product(url)
    price = product["price"]
    if not image_url:
        image_url = product["image_url"]
    item = TrackedItem(
        user_id=current_user.id,
        url=url,
        product_name=name,
        target_price=target,
        current_price=price,
        image_url=image_url
    )
    db.session.add(item)
    db.session.commit()
    if price:
        db.session.add(PriceHistory(item_id=item.id, price=price))
        db.session.commit()
    flash(f'Now tracking "{name}". Current price: ₹{price or "unknown"}')
    return redirect(url_for('dashboard'))

@app.route('/delete-item/<int:item_id>')
@login_required
def delete_item(item_id):
    item = TrackedItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
        flash('Item removed.')
    return redirect(url_for('dashboard'))

@app.route('/refresh-price/<int:item_id>')
@login_required
def refresh_price(item_id):
    item = TrackedItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    product = scrape_product(item.url)
    new_price = product["price"]
    if new_price:
        item.current_price = new_price
        if product["image_url"]:
            item.image_url = product["image_url"]
        db.session.add(PriceHistory(item_id=item.id, price=new_price))
        db.session.commit()
        flash(f'Price updated to ₹{new_price:.2f}')
    else:
        flash('Could not fetch price. Website may be blocking the scraper.')
    return redirect(url_for('dashboard'))

@app.route('/history/<int:item_id>')
@login_required
def history(item_id):
    item = TrackedItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    records = PriceHistory.query.filter_by(item_id=item_id)\
                                .order_by(PriceHistory.recorded_at).all()
    labels = [r.recorded_at.strftime('%d %b, %H:%M') for r in records]
    prices = [r.price for r in records]
    return render_template('history.html', item=item, labels=labels, prices=prices)

@app.route('/edit-item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = TrackedItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        item.product_name = request.form['name'].strip()
        item.target_price = float(request.form['target_price'])
        item.url = request.form['url'].strip()
        image_url = request.form.get('image_url', '').strip()
        if image_url:
            item.image_url = image_url
        db.session.commit()
        flash(f'"{item.product_name}" updated successfully!')
        return redirect(url_for('dashboard'))
    return render_template('edit_item.html', item=item)

@app.route('/alerts')
@login_required
def alerts():
    from models import Alert
    all_alerts = Alert.query.filter_by(user_id=current_user.id)\
                            .order_by(Alert.created_at.desc()).all()
    return render_template('alerts.html', alerts=all_alerts)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        if name:
            current_user.name = name
            db.session.commit()
            flash('Name updated!')
        if current_password and new_password:
            if check_password_hash(current_user.password, current_password):
                current_user.password = generate_password_hash(new_password)
                db.session.commit()
                flash('Password changed successfully!')
            else:
                flash('Current password is wrong.')
    total_items = TrackedItem.query.filter_by(user_id=current_user.id).count()
    return render_template('profile.html', total_items=total_items)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)