"""Quick test of authentication system."""
from datetime import datetime

from pocketsage.config import BaseConfig
from pocketsage.infra.database import create_db_engine, create_session_factory, init_database
from pocketsage.services import auth

cfg = BaseConfig()
eng = create_db_engine(cfg)
init_database(eng)
sf = create_session_factory(eng)

print("Ensuring default accounts...")
auth.ensure_default_accounts(sf)

print("\nListing all users...")
users = auth.list_users(sf)
for u in users:
    print(f"  - {u.username} (role: {u.role}, id: {u.id})")

print("\nTesting admin login...")
admin_user = auth.authenticate(username='admin', password='admin123', session_factory=sf)
if admin_user:
    print(f"✓ Admin login successful: {admin_user.username} (role: {admin_user.role}, id: {admin_user.id})")
else:
    print("✗ Admin login FAILED")

print("\nTesting local login...")
local_user = auth.authenticate(username='local', password='local123', session_factory=sf)
if local_user:
    print(f"✓ Local login successful: {local_user.username} (role: {local_user.role}, id: {local_user.id})")
else:
    print("✗ Local login FAILED")
    # Debug local user password hash
    print("  Checking if local user exists...")
    local_check = auth.get_user_by_username('local', sf)
    if local_check:
        print(f"  User exists: {local_check.username}, trying to verify password hash...")
        from argon2 import PasswordHasher
        hasher = PasswordHasher()
        try:
            hasher.verify(local_check.password_hash, 'local123')
            print("  Password hash verification: PASSED")
        except Exception as e:
            print(f"  Password hash verification: FAILED - {e}")

if admin_user:
    print("\nTesting transaction creation with correct datetime...")
    from pocketsage.infra.repositories import SQLModelTransactionRepository
    from pocketsage.services import ledger_service

    txn_repo = SQLModelTransactionRepository(sf)
    saved_txn = ledger_service.save_transaction(
        repo=txn_repo,
        existing=None,
        amount=100.50,
        memo="Test transaction",
        occurred_at=datetime.now(),
        category_id=None,
        account_id=None,
        currency="USD",
        user_id=admin_user.id,
    )
    print(f"✓ Transaction created successfully: {saved_txn.memo} (id: {saved_txn.id})")

    # List transactions
    transactions = txn_repo.list_all(user_id=admin_user.id, limit=5)
    print(f"\nTotal transactions for admin: {len(transactions)}")
