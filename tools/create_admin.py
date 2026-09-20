#!/usr/bin/env python3
"""
OmniLogix ULPF Administrator Account Provisioning Tool.

Usage:
  # Interactive mode:
  python tools/create_admin.py

  # Non-interactive / scriptable mode:
  python tools/create_admin.py --username admin --password MyStrongPassword123! --email admin@omnilogix.local
"""

import sys
import os
import argparse
import getpass

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.database import SessionLocal, init_db
from app.core.security import get_password_hash
from app.models.user import User


def main():
    parser = argparse.ArgumentParser(description="Create or update an OmniLogix Administrator account.")
    parser.add_argument("--username", "-u", help="Administrator username")
    parser.add_argument("--password", "-p", help="Administrator password (min 6 characters)")
    parser.add_argument("--email", "-e", help="Administrator email address")
    parser.add_argument("--role", "-r", default="ADMIN", choices=["ADMIN", "ANALYST", "OPERATOR", "VIEWER"], help="RBAC role")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()

    try:
        username = args.username
        if not username:
            username = input("Enter username: ").strip()
            if not username:
                print("Error: Username cannot be empty.", file=sys.stderr)
                sys.exit(1)

        password = args.password
        if not password:
            password = getpass.getpass("Enter password (min 6 chars): ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("Error: Passwords do not match.", file=sys.stderr)
                sys.exit(1)

        if len(password) < 6:
            print("Error: Password must be at least 6 characters long.", file=sys.stderr)
            sys.exit(1)

        email = args.email
        if not email and not args.username:
            email_in = input("Enter email [optional]: ").strip()
            email = email_in if email_in else None

        existing_user = db.query(User).filter(User.username == username).first()
        hashed_pw = get_password_hash(password)

        if existing_user:
            existing_user.hashed_password = hashed_pw
            existing_user.role = args.role
            existing_user.is_active = True
            if email:
                existing_user.email = email
            db.commit()
            print(f"[SUCCESS] Updated existing account '{username}' with role '{args.role}'.")
        else:
            new_user = User(
                username=username,
                email=email,
                hashed_password=hashed_pw,
                role=args.role,
                is_active=True
            )
            db.add(new_user)
            db.commit()
            print(f"[SUCCESS] Created new account '{username}' with role '{args.role}'.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
