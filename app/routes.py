from flask import Blueprint, render_template, redirect, url_for
bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    return redirect(url_for("main.ledger"))

@bp.route("/ledger")
def ledger():
    return render_template("ledger.html", page="ledger")

@bp.route("/habits")
def habits():
    return render_template("habits.html", page="habits")

@bp.route("/liabilities")
def liabilities():
    return render_template("liabilities.html", page="liabilities")

@bp.route("/portfolio")
def portfolio():
    return render_template("portfolio.html", page="portfolio")

@bp.route("/admin")
def admin():
    return render_template("admin.html", page="admin")
