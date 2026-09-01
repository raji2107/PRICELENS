import time
import mysql.connector
import smtplib

from apscheduler.schedulers.background import BackgroundScheduler

from scraper.price_scraper import scrape_product

from config import (
    DB_HOST,
    DB_USER,
    DB_PASSWORD,
    DB_NAME,
    MAIL_SERVER,
    MAIL_PORT,
    MAIL_USE_TLS,
    MAIL_USERNAME,
    MAIL_PASSWORD
)

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# =================================
# DATABASE CONNECTION
# =================================

def get_db_connection():

    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


# =================================
# SEND EMAIL
# =================================

def send_email(to_email, subject, message):

    msg = MIMEMultipart()

    msg["From"] = MAIL_USERNAME
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(
        MIMEText(message, "plain")
    )

    try:

        server = smtplib.SMTP(
            MAIL_SERVER,
            MAIL_PORT
        )

        if MAIL_USE_TLS:
            server.starttls()

        server.login(
            MAIL_USERNAME,
            MAIL_PASSWORD
        )

        server.sendmail(
            MAIL_USERNAME,
            to_email,
            msg.as_string()
        )

        server.quit()

        return True

    except Exception as e:

        print(
            "❌ Email Error:",
            e
        )

        return False


# =================================
# CHECK ALL PRODUCTS
# =================================

def check_prices():

    print()
    print("================================")
    print("PriceLens Automatic Price Check")
    print("================================")

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                p.id,
                p.user_id,
                p.product_url,
                p.product_name,
                p.current_price,
                p.target_price,
                u.full_name,
                u.email
            FROM products p
            JOIN users u
                ON p.user_id = u.id
            """
        )

        products = cursor.fetchall()

        print(
            "Products found:",
            len(products)
        )

        for product in products:

            print()
            print("--------------------------------")
            print(
                "Checking:",
                product["product_name"]
            )

            print(
                "URL:",
                product["product_url"]
            )

            # -----------------------------
            # SCRAPE
            # -----------------------------

            try:

                scraped_product = scrape_product(
                    product["product_url"]
                )

            except Exception as e:

                print(
                    "❌ Scraping Error:",
                    e
                )

                continue

            if not scraped_product:

                print(
                    "❌ Could not update product"
                )

                continue

            new_price = scraped_product.get(
                "price"
            )

            if new_price is None:

                print(
                    "❌ Price not found"
                )

                continue

            old_price = product[
                "current_price"
            ]

            target_price = product[
                "target_price"
            ]

            print(
                "Old Price:",
                old_price
            )

            print(
                "New Price:",
                new_price
            )

            print(
                "Target Price:",
                target_price
            )

            # -----------------------------
            # UPDATE PRICE
            # -----------------------------

            cursor.execute(
                """
                UPDATE products
                SET
                    current_price = %s
                WHERE id = %s
                """,
                (
                    new_price,
                    product["id"]
                )
            )

            conn.commit()

            print(
                "✅ Price updated"
            )

            # -----------------------------
            # TARGET CHECK
            # -----------------------------

            if new_price <= target_price:

                print()
                print(
                    "🎯 TARGET PRICE REACHED!"
                )

                # -----------------------------
                # DUPLICATE ALERT CHECK
                # -----------------------------

                cursor.execute(
                    """
                    SELECT id
                    FROM price_alerts
                    WHERE product_id = %s
                      AND user_id = %s
                      AND target_price = %s
                    """,
                    (
                        product["id"],
                        product["user_id"],
                        target_price
                    )
                )

                existing_alert = cursor.fetchone()

                if existing_alert:

                    print(
                        "📧 Alert already sent. "
                        "Skipping duplicate email."
                    )

                else:

                    # -------------------------
                    # EMAIL ALERT
                    # -------------------------

                    alert_subject = (
                        "🎯 PriceLens - "
                        "Target Price Reached!"
                    )

                    alert_message = f"""
Hello {product["full_name"]},

Good news! 🎉

Your tracked product has reached your target price.

Product:
{product["product_name"]}

Current Price:
₹{new_price:,.2f}

Target Price:
₹{target_price:,.2f}

🔥 The current price is now at or below your target price.

You can check the product here:

{product["product_url"]}

Happy Shopping!

PriceLens Team
"""

                    email_success = send_email(
                        product["email"],
                        alert_subject,
                        alert_message
                    )

                    if email_success:

                        cursor.execute(
                            """
                            INSERT INTO price_alerts
                            (
                                product_id,
                                user_id,
                                target_price
                            )
                            VALUES (%s, %s, %s)
                            """,
                            (
                                product["id"],
                                product["user_id"],
                                target_price
                            )
                        )

                        conn.commit()

                        print(
                            "📧 Target alert email sent!"
                        )

                    else:

                        print(
                            "⚠️ Target reached, "
                            "but email failed."
                        )

            else:

                print(
                    "Price is still above "
                    "target price."
                )

        print()
        print("================================")
        print(
            "✅ Automatic price check complete"
        )
        print("================================")

    except Exception as e:

        print(
            "❌ Scheduler Error:",
            e
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =================================
# START AUTOMATIC SCHEDULER
# =================================

if __name__ == "__main__":

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        check_prices,
        "interval",
        hours=1,
        next_run_time=None
    )

    scheduler.start()

    print()
    print("================================")
    print("🚀 PriceLens Scheduler Started")
    print("================================")
    print("⏰ Price check interval: 1 hour")
    print("Press Ctrl+C to stop.")
    print("================================")

    try:

        while True:

            time.sleep(1)

    except KeyboardInterrupt:

        print()
        print("🛑 Scheduler stopped.")

        scheduler.shutdown()