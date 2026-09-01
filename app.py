from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
import smtplib
import secrets

from urllib.parse import quote

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from werkzeug.security import generate_password_hash, check_password_hash

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

from scraper.price_scraper import scrape_product



app = Flask(__name__)

app.secret_key = "pricelens-secret-key-change-later"


# ==============================
# DATABASE CONNECTION
# ==============================

def get_db_connection():

    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


# ==============================
# EMAIL SERVICE
# ==============================

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

        print("Email Error:", e)

        return False


# ==============================
# VERIFICATION EMAIL
# ==============================

def send_verification_email(
    to_email,
    full_name,
    token
):

    verification_link = (
        "http://127.0.0.1:5000/verify/"
        + quote(token)
    )

    message = (
        "Hello " + full_name + ",\n\n"
        "Welcome to PriceLens!\n\n"
        "Thank you for creating your PriceLens account.\n\n"
        "Please verify your email address by clicking the link below:\n\n"
        + verification_link +
        "\n\n"
        "If you did not create a PriceLens account, "
        "you can ignore this email.\n\n"
        "Thank you,\n"
        "PriceLens Team"
    )

    return send_email(
        to_email,
        "Verify your PriceLens Account",
        message
    )


# ==============================
# PASSWORD VALIDATION
# ==============================

def validate_password(password):

    if len(password) < 6:

        return "Password must be at least 6 characters."

    if not any(
        char.isalpha()
        for char in password
    ):

        return "Password must contain at least one letter."

    if not any(
        char.isdigit()
        for char in password
    ):

        return "Password must contain at least one number."

    if not any(
        not char.isalnum()
        for char in password
    ):

        return "Password must contain at least one special symbol."

    return None


# ==============================
# HOME
# ==============================

@app.route("/")
def home():

    return render_template(
        "home.html"
    )


# ==============================
# DASHBOARD
# ==============================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    return render_template(
        "dashboard.html",
        user_name=session["user_name"]
    )


# ==============================
# PRODUCTS
# ==============================

@app.route("/products")
def products():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM products
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (
                session["user_id"],
            )
        )

        products_list = cursor.fetchall()

        cursor.close()

        conn.close()

        return render_template(
            "products.html",
            products=products_list
        )

    except Exception as e:

        return (
            "<h3>Database Error</h3>"
            "<p>" + str(e) + "</p>"
        )


# ==============================
# ADD / TRACK PRODUCT
# ==============================

@app.route(
    "/add-product",
    methods=["POST"]
)
def add_product():

    # Login check

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # Get form values

    product_url = request.form.get(
        "product_url",
        ""
    ).strip()

    target_price = request.form.get(
        "target_price",
        ""
    ).strip()


    # ==============================
    # VALIDATION
    # ==============================

    if not product_url or not target_price:

        return (
            "<h3>Please enter Product URL "
            "and Target Price.</h3>"
            "<a href='/products'>Go Back</a>"
        )


    try:

        target_price = float(
            target_price
        )

        if target_price <= 0:

            return (
                "<h3>Target price must be "
                "greater than 0.</h3>"
                "<a href='/products'>Go Back</a>"
            )

    except ValueError:

        return (
            "<h3>Invalid target price.</h3>"
            "<a href='/products'>Go Back</a>"
        )


    # ==============================
    # SCRAPE PRODUCT
    # ==============================

    print()
    print("================================")
    print("PriceLens Product Tracking")
    print("================================")
    print("URL:", product_url)
    print("Target Price:", target_price)
    print("Starting scraper...")


    try:

        product = scrape_product(
            product_url
        )

    except Exception as e:

        print(
            "Scraping Error:",
            e
        )

        return (
            "<h3>Scraping failed.</h3>"
            "<p>" + str(e) + "</p>"
            "<a href='/products'>Go Back</a>"
        )


    # ==============================
    # CHECK SCRAPER RESULT
    # ==============================

    if not product:

        return (
            "<h3>Unable to fetch "
            "product details.</h3>"
            "<p>Please check the product URL.</p>"
            "<a href='/products'>Go Back</a>"
        )


    product_name = product.get(
        "name"
    )

    current_price = product.get(
        "price"
    )

    product_image = product.get(
        "image"
    )


    print(
        "Product Name:",
        product_name
    )

    print(
        "Current Price:",
        current_price
    )

    print(
        "Product Image:",
        product_image
    )


    if not product_name:

        return (
            "<h3>Product name could not "
            "be extracted.</h3>"
            "<a href='/products'>Go Back</a>"
        )


    if current_price is None:

        return (
            "<h3>Product price could not "
            "be extracted.</h3>"
            "<a href='/products'>Go Back</a>"
        )


    # ==============================
    # CONVERT PRICE
    # ==============================

    try:

        current_price = float(
            current_price
        )

    except (
        ValueError,
        TypeError
    ):

        return (
            "<h3>Invalid product price "
            "returned by scraper.</h3>"
            "<a href='/products'>Go Back</a>"
        )


    # ==============================
    # SAVE PRODUCT TO MYSQL
    # ==============================

    try:

        conn = get_db_connection()

        cursor = conn.cursor()


        cursor.execute(
            """
            INSERT INTO products
            (
                user_id,
                product_url,
                product_name,
                current_price,
                target_price,
                product_image,
                highest_price,
                lowest_price,
                average_price
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                session["user_id"],
                product_url,
                product_name,
                current_price,
                target_price,
                product_image,
                current_price,
                current_price,
                current_price
            )
        )


        conn.commit()

        cursor.close()

        conn.close()


        print()
        print("================================")
        print("Product saved successfully!")
        print("================================")
        print("Name:", product_name)
        print("Price:", current_price)
        print("Target:", target_price)


    except Exception as e:

        print(
            "Database Error:",
            e
        )

        return (
            "<h3>Database Error</h3>"
            "<p>" + str(e) + "</p>"
            "<a href='/products'>Go Back</a>"
        )


    # ==============================
    # TARGET PRICE ALERT
    # ==============================

    if current_price <= target_price:

        print()

        print(
            "🎯 TARGET PRICE REACHED!"
        )


        alert_subject = (
            "🎯 PriceLens - "
            "Target Price Reached!"
        )


        alert_message = f"""
Hello {session["user_name"]},

Good news! 🎉

Your tracked product has reached your target price.

Product: {product_name}

Current Price: ₹{current_price:,.2f}

Target Price: ₹{target_price:,.2f}

🔥 The current price is now at or below your target price.

You can check the product here:

{product_url}

Happy Shopping!

PriceLens Team
"""


        email_success = send_email(
            session["user_email"],
            alert_subject,
            alert_message
        )


        if email_success:

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


    # ==============================
    # RETURN TO PRODUCTS
    # ==============================

    return redirect(
        url_for("products")
    )


# ==============================
# LOGIN
# ==============================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        try:

            conn = get_db_connection()

            cursor = conn.cursor(
                dictionary=True
            )


            cursor.execute(
                "SELECT * FROM users WHERE email = %s",
                (email,)
            )


            user = cursor.fetchone()


            cursor.close()

            conn.close()


            if not user:

                return (
                    "<h3>Invalid email "
                    "or password.</h3>"
                    "<a href='/login'>Go Back</a>"
                )


            if not check_password_hash(
                user["password"],
                password
            ):

                return (
                    "<h3>Invalid email "
                    "or password.</h3>"
                    "<a href='/login'>Go Back</a>"
                )


            if not user["email_verified"]:

                return (
                    "<h3>Email not verified.</h3>"
                    "<p>Please check your Gmail "
                    "and verify your email address "
                    "first.</p>"
                    "<a href='/login'>Go Back</a>"
                )


            session["user_id"] = user["id"]

            session["user_name"] = (
                user["full_name"]
            )

            session["user_email"] = (
                user["email"]
            )


            return redirect(
                url_for("dashboard")
            )


        except Exception as e:

            return (
                "<h3>Database Error</h3>"
                "<p>" + str(e) + "</p>"
                "<a href='/login'>Go Back</a>"
            )


    return render_template(
        "login.html"
    )


# ==============================
# LOGOUT
# ==============================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ==============================
# REGISTER
# ==============================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        full_name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )


        if (
            not full_name
            or not email
            or not password
        ):

            return (
                "<h3>Please fill in "
                "all required fields.</h3>"
                "<a href='/register'>Go Back</a>"
            )


        error = validate_password(
            password
        )


        if error:

            return (
                "<h3>" + error + "</h3>"
                "<a href='/register'>Go Back</a>"
            )


        if password != confirm_password:

            return (
                "<h3>Passwords do not match.</h3>"
                "<a href='/register'>Go Back</a>"
            )


        hashed_password = (
            generate_password_hash(
                password
            )
        )


        verification_token = (
            secrets.token_urlsafe(32)
        )


        try:

            conn = get_db_connection()

            cursor = conn.cursor()


            cursor.execute(
                """
                INSERT INTO users
                (
                    full_name,
                    email,
                    password,
                    email_verified,
                    verification_token
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    full_name,
                    email,
                    hashed_password,
                    False,
                    verification_token
                )
            )


            conn.commit()


            cursor.close()

            conn.close()


            email_sent = (
                send_verification_email(
                    email,
                    full_name,
                    verification_token
                )
            )


            if email_sent:

                return (
                    "<h2>Account created "
                    "successfully!</h2>"
                    "<p>A verification link "
                    "has been sent to your email.</p>"
                    "<p>Please check your Gmail "
                    "inbox and click the "
                    "verification link.</p>"
                    "<a href='/login'>"
                    "Go to Login"
                    "</a>"
                )


            return (
                "<h3>Account created, "
                "but email could not be sent.</h3>"
                "<p>Check the Flask terminal "
                "for the email error.</p>"
                "<a href='/login'>Go to Login</a>"
            )


        except mysql.connector.IntegrityError:

            return (
                "<h3>Email already registered.</h3>"
                "<a href='/register'>Go Back</a>"
            )


        except Exception as e:

            return (
                "<h3>Database Error</h3>"
                "<p>" + str(e) + "</p>"
                "<a href='/register'>Go Back</a>"
            )


    return render_template(
        "register.html"
    )


# ==============================
# EMAIL VERIFICATION
# ==============================

@app.route(
    "/verify/<token>"
)
def verify_email(token):

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            dictionary=True
        )


        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE verification_token = %s
            """,
            (token,)
        )


        user = cursor.fetchone()


        if not user:

            cursor.close()

            conn.close()

            return (
                "<h3>Invalid or expired "
                "verification link.</h3>"
                "<a href='/login'>"
                "Go to Login"
                "</a>"
            )


        cursor.execute(
            """
            UPDATE users
            SET
                email_verified = TRUE,
                verification_token = NULL
            WHERE id = %s
            """,
            (user["id"],)
        )


        conn.commit()


        cursor.close()

        conn.close()


        return (
            "<h2>Email verified "
            "successfully!</h2>"
            "<p>Your PriceLens account "
            "is now verified.</p>"
            "<p>You can now login "
            "to your account.</p>"
            "<a href='/login'>"
            "Go to Login"
            "</a>"
        )


    except Exception as e:

        return (
            "<h3>Verification Error</h3>"
            "<p>" + str(e) + "</p>"
            "<a href='/login'>"
            "Go to Login"
            "</a>"
        )


# ==============================
# EMAIL TEST
# ==============================

@app.route("/email-test")
def email_test():

    success = send_email(
        MAIL_USERNAME,
        "PriceLens Email Test",
        "Hello! This is a test email from PriceLens."
    )


    if success:

        return (
            "<h2>Email sent successfully!</h2>"
            "<p>Check your Gmail inbox.</p>"
        )


    return (
        "<h3>Email sending failed.</h3>"
        "<p>Check the Flask terminal "
        "for the error.</p>"
    )


# ==============================
# DATABASE TEST
# ==============================

@app.route("/db-test")
def db_test():

    try:

        conn = get_db_connection()

        conn.close()

        return (
            "PriceLens MySQL "
            "Connection Successful!"
        )


    except Exception as e:

        return (
            "MySQL Connection Failed: "
            + str(e)
        )


# ==============================
# RUN APPLICATION
# ==============================

if __name__ == "__main__":

    app.run(
        debug=True,
        use_reloader=False
    )