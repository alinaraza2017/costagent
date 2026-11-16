"""Load fictional demo records for local review.

Demo sign-in after seeding: demo@costwise.local / DemoPass123!
"""

from datetime import date
from decimal import Decimal

from app.database import Base, SessionLocal, engine
from app.models import Expense, Project, User
from app.security import hash_password
from app.services.calculations import money
from app.services.pert import suggest_points

DEMO_EMAIL = "demo@costwise.local"
DEMO_PASSWORD = "DemoPass123!"


SEEDED_EXPENSE_NAMES = {
    "Core switches",
    "Access points",
    "Patch cabling",
    "Rack cabinets",
    "UPS units",
    "Emergency firewall appliance",
    "Network engineer",
    "Junior technician",
    "Monitoring licenses",
    "Vendor site visit",
    "Launch posters",
    "Power circuits",
    "Helpdesk overtime",
    "Spare adapters",
    "Interface design",
    "Component library license",
    "Design laptop",
    "Orientation ads",
    "Portal hosting",
}


def _points(name: str, estimated: Decimal):
    if name == "Emergency firewall appliance":
        optimistic = money(estimated * Decimal("0.70"))
        most_likely = money(estimated)
        pessimistic = money(estimated * Decimal("1.80"))
        return optimistic, most_likely, pessimistic
    return suggest_points(estimated)


def _expense(project_id: int, name: str, category: str, estimated, actual, expense_date: str, vendor: str, description: str = "") -> Expense:
    estimated_amount = Decimal(str(estimated))
    optimistic, most_likely, pessimistic = _points(name, estimated_amount)
    return Expense(
        project_id=project_id,
        expense_name=name,
        category=category,
        description=description,
        estimated_cost=estimated_amount,
        actual_cost=Decimal(str(actual)),
        optimistic_cost=optimistic,
        most_likely_cost=most_likely,
        pessimistic_cost=pessimistic,
        expense_date=date.fromisoformat(expense_date),
        vendor=vendor,
    )


def fill_seeded_pert() -> None:
    """Give the original demo expenses a three-point estimate when they do not have one yet."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if user is None:
            return
        expenses = (
            db.query(Expense)
            .join(Project)
            .filter(
                Project.owner_id == user.id,
                Expense.expense_name.in_(SEEDED_EXPENSE_NAMES),
                Expense.optimistic_cost.is_(None),
            )
            .all()
        )
        for expense in expenses:
            if expense.most_likely_cost is not None or expense.pessimistic_cost is not None:
                continue
            optimistic, most_likely, pessimistic = _points(expense.expense_name, expense.estimated_cost)
            expense.optimistic_cost = optimistic
            expense.most_likely_cost = most_likely
            expense.pessimistic_cost = pessimistic
        if expenses:
            db.commit()
    finally:
        db.close()


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if existing is not None:
            print("Demo data already exists.")
            return
        user = User(email=DEMO_EMAIL, full_name="Demo Reviewer", password_hash=hash_password(DEMO_PASSWORD))
        db.add(user)
        db.flush()

        network = Project(
            owner_id=user.id,
            name="North Campus Network Upgrade",
            description="Fictional lab project for replacing switches, wireless, and a firewall.",
            start_date=date(2026, 1, 6),
            end_date=date(2026, 6, 30),
            budget=Decimal("2500000"),
            currency="PKR",
            status="active",
        )
        portal = Project(
            owner_id=user.id,
            name="Student Portal Redesign",
            description="Fictional project for a small student portal refresh.",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 9, 15),
            budget=Decimal("900000"),
            currency="PKR",
            status="planning",
        )
        db.add_all([network, portal])
        db.flush()

        db.add_all(
            [
                _expense(network.id, "Core switches", "Equipment", 100000, 100000, "2026-01-15", "NetSupply"),
                _expense(network.id, "Access points", "Equipment", 120000, 110000, "2026-02-02", "NetSupply"),
                _expense(network.id, "Patch cabling", "Equipment", 120000, 120000, "2026-02-20", "CableHouse"),
                _expense(network.id, "Rack cabinets", "Equipment", 125000, 130000, "2026-03-05", "Campus Stores"),
                _expense(network.id, "UPS units", "Equipment", 150000, 140000, "2026-03-18", "PowerGrid Co"),
                _expense(network.id, "Emergency firewall appliance", "Equipment", 160000, 900000, "2026-04-01", "NetSupply", "Unusually large fictional purchase for the anomaly example."),
                _expense(network.id, "Network engineer", "Personnel", 300000, 300000, "2026-01-31", "Campus HR"),
                _expense(network.id, "Junior technician", "Personnel", 120000, 110000, "2026-02-28", "Campus HR"),
                _expense(network.id, "Monitoring licenses", "Software", 60000, 60000, "2026-01-20", "CloudHost"),
                _expense(network.id, "Vendor site visit", "Travel", 40000, 55000, "2026-03-12", "City Coach"),
                _expense(network.id, "Launch posters", "Marketing", 25000, 20000, "2026-04-10", "PrintRoom"),
                _expense(network.id, "Power circuits", "Infrastructure", 70000, 90000, "2026-02-11", "Facilities"),
                _expense(network.id, "Helpdesk overtime", "Operations", 35000, 50000, "2026-05-02", "Campus HR"),
                _expense(network.id, "Spare adapters", "Other", 8000, 7500, "2026-05-16", "Campus Stores"),
                _expense(portal.id, "Interface design", "Personnel", 200000, 210000, "2026-06-01", "Studio North"),
                _expense(portal.id, "Component library license", "Software", 40000, 40000, "2026-06-15", "CloudHost"),
                _expense(portal.id, "Design laptop", "Equipment", 150000, 149000, "2026-07-01", "Campus Stores"),
                _expense(portal.id, "Orientation ads", "Marketing", 20000, 35000, "2026-07-20", "PrintRoom"),
                _expense(portal.id, "Portal hosting", "Infrastructure", 30000, 28000, "2026-08-01", "CloudHost"),
            ]
        )
        db.commit()
        print("Demo data created.")
        print("Email: demo@costwise.local")
        print("Password: DemoPass123!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
