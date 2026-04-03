import hashlib
import hmac
import os
from datetime import datetime, timedelta
from typing import List

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, constr
from sqlalchemy import func
from sqlalchemy.orm import Session

import crud
import models
from database import DATABASE_URL, get_db

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
ROLE_ADMIN = "admin"
ROLE_USER = "user"
ROLE_SELLER = "seller"


def _stable_default_signing_key() -> str:
    seed = DATABASE_URL or "shop-db-default-seed"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


JWT_SIGNING_KEY = os.getenv("JWT_SIGNING_KEY", _stable_default_signing_key())
PASSWORD_SIGNING_KEY = os.getenv("PASSWORD_SIGNING_KEY", JWT_SIGNING_KEY)
ADMIN_REGISTRATION_KEY = os.getenv("ADMIN_REGISTRATION_KEY", "1461")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
auth_router = APIRouter()
router = APIRouter()


def _hs256_sign(value: str, key: str) -> str:
    return hmac.new(key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SIGNING_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password, hashed_password):
    expected_hash = _hs256_sign(plain_password, PASSWORD_SIGNING_KEY)
    return hmac.compare_digest(expected_hash, hashed_password)


def get_password_hash(password):
    return _hs256_sign(password, PASSWORD_SIGNING_KEY)


def _normalize_role(role: str | None) -> str:
    normalized = (role or ROLE_USER).strip().lower()
    if normalized not in {ROLE_ADMIN, ROLE_USER, ROLE_SELLER}:
        raise HTTPException(status_code=400, detail="Invalid role. Allowed values: admin, user, seller")
    return normalized


def is_admin(current_user: models.Customer) -> bool:
    return (getattr(current_user, "Role", ROLE_USER) or ROLE_USER).lower() == ROLE_ADMIN


def is_seller(db: Session, current_user: models.Customer) -> bool:
    if is_admin(current_user):
        return False
    seller_profile = (
        db.query(models.Supplier)
        .filter(
            models.Supplier.OwnerCustomerID == current_user.CustomerID,
            func.lower(models.Supplier.Role) == ROLE_SELLER,
        )
        .first()
    )
    return seller_profile is not None


def ensure_seller_or_admin(db: Session, current_user: models.Customer) -> None:
    if is_admin(current_user):
        return
    if not is_seller(db, current_user):
        raise HTTPException(status_code=403, detail="Only seller or admin can modify supplier/product data")


def ensure_customer_scope(customer_id: int, current_user: models.Customer) -> None:
    if is_admin(current_user):
        return
    if customer_id != current_user.CustomerID:
        raise HTTPException(status_code=403, detail="Access denied")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, JWT_SIGNING_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        customer_id = payload.get("customer_id")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        customer = None
        if customer_id is not None:
            customer = db.query(models.Customer).filter(models.Customer.CustomerID == customer_id).first()

        if customer is None:
            customer = db.query(models.Customer).filter(models.Customer.Name == username).first()

        if customer is None:
            raise HTTPException(status_code=401, detail="User not found")
        return customer
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@auth_router.post("/register")
def register(
    username: str,
    email: str,
    password: str,
    role: str = ROLE_USER,
    admin_key: str | None = None,
    phone: str | None = None,
    country: str | None = None,
    db: Session = Depends(get_db),
):
    normalized_role = _normalize_role(role)
    if normalized_role == ROLE_ADMIN and admin_key != ADMIN_REGISTRATION_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    customer = db.query(models.Customer).filter(
        (models.Customer.Name == username) | (models.Customer.Email == email)
    ).first()
    if customer:
        raise HTTPException(status_code=400, detail="User already exists")

    persisted_customer_role = ROLE_USER if normalized_role == ROLE_SELLER else normalized_role

    new_customer = models.Customer(
        Name=username,
        Email=email,
        Phone=phone,
        Country=country,
        Role=persisted_customer_role,
        password_hash=get_password_hash(password),
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    supplier_id = None
    if normalized_role == ROLE_SELLER:
        seller_profile = models.Supplier(
            SupplierName=username,
            Phone=phone,
            Role=ROLE_SELLER,
            OwnerCustomerID=new_customer.CustomerID,
        )
        db.add(seller_profile)
        db.commit()
        db.refresh(seller_profile)
        supplier_id = seller_profile.SupplierID

    return {
        "message": "User created successfully",
        "customer_id": new_customer.CustomerID,
        "supplier_id": supplier_id,
    }


@auth_router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    customer = db.query(models.Customer).filter(models.Customer.Name == form_data.username).first()
    if not customer or not customer.password_hash or not verify_password(form_data.password, customer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(
        {
            "sub": customer.Name,
            "customer_id": customer.CustomerID,
            "role": (customer.Role or ROLE_USER).lower(),
        }
    )
    return {"access_token": token, "token_type": "bearer"}

# ---------- SCHEMAS ----------
class Customer(BaseModel):
    CustomerID: int | None = None
    Name: constr(min_length=2, max_length=100) | None = None
    Email: EmailStr | None = None
    Phone: constr(min_length=6, max_length=20) | None = None
    Country: constr(min_length=2, max_length=50) | None = None
    Role: str | None = None

    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

class CustomerRead(BaseModel):
    CustomerID: int
    Name: str
    Email: EmailStr
    Phone: str | None
    Country: str | None
    Role: str | None

    model_config = {"from_attributes": True}


# ---------- ROUTES ----------
@router.get("/customer", response_model=List[CustomerRead])
def read_customers(
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    if is_admin(current_user):
        return crud.get_customers(db)

    customer = crud.get_customer(db, current_user.CustomerID)
    return [customer] if customer else []

@router.get("/customer/{customer_id}", response_model=Customer)
def read_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)
    target_customer_id = customer_id if is_admin(current_user) else current_user.CustomerID
    customer = crud.get_customer(db, target_customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.put("/customer/{customer_id}", response_model=Customer)
def update_customer(
    customer_id: int,
    customer: Customer,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)
    target_customer_id = customer_id if is_admin(current_user) else current_user.CustomerID
    db_customer = crud.get_customer(db, target_customer_id)
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    update_data = customer.dict(exclude_unset=True)
    if not is_admin(current_user):
        update_data.pop("Role", None)
    return crud.update_customer(db, target_customer_id, **update_data)

@router.delete("/customer/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)
    target_customer_id = customer_id if is_admin(current_user) else current_user.CustomerID
    db_customer = crud.delete_customer(db, target_customer_id)
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted successfully"}
