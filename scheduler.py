from apscheduler.schedulers.background import BackgroundScheduler
from models import db, TrackedItem, PriceHistory, User
from scraper import scrape_price
import smtplib
from email.mime.text import MIMEText

SENDER_EMAIL = "pricetrack2815@gmail.com"
SENDER_PASSWORD = "ladmxwnzoyachxub"

def send_alert_email(to_email, item, new_price):
    msg = MIMEText(
        f"Good news!\n\n"
        f"'{item.product_name}' has dropped to ₹{new_price:.2f}.\n"
        f"Your target was ₹{item.target_price:.2f}.\n\n"
        f"Buy it here: {item.url}"
    )
    msg['Subject'] = f"Price drop alert: {item.product_name}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"[Alert sent] to {to_email} for {item.product_name}")
    except Exception as e:
        print(f"[Email error] {e}")

def check_all_prices(app):
    with app.app_context():
        from models import Alert
        items = TrackedItem.query.all()
        for item in items:
            new_price = scrape_price(item.url)
            if new_price is None:
                continue

            old_price = item.current_price
            item.current_price = new_price
            db.session.add(PriceHistory(item_id=item.id, price=new_price))

            if item.target_price and new_price <= item.target_price:
                item.has_alert = True

                alert = Alert(
                    user_id=item.user_id,
                    item_id=item.id,
                    product_name=item.product_name,
                    old_price=old_price,
                    new_price=new_price,
                    target_price=item.target_price
                )
                db.session.add(alert)

                user = User.query.get(item.user_id)
                if user:
                    send_alert_email(user.email, item, new_price)
                    print(f"[Alert] Price drop for {item.product_name}")

            db.session.commit()
            print(f"[Updated] {item.product_name} → ₹{new_price}")

def start_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=check_all_prices,
        args=[app],
        trigger='interval',
        hours = 6
    )
    scheduler.start()
    print("[Scheduler] Price checks will run every 6 hours.")