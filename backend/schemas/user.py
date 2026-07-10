from pydantic import BaseModel, EmailStr
from datetime import datetime



# What the user sends when REGISTERING

class UserCreate(BaseModel):
    username: str
    email: EmailStr        # pydantic validates it is a proper email format
    password: str          # plain text 


# What the user sends when LOGGING IN

     class UserLogin(BaseModel):
       email: EmailStr
       password: str


# What we send back to the user

 class UserOut(BaseModel):
     id: int
     username: str
     email: EmailStr
     is_active: bool
    created_at: datetime


    model_config = {"from_attributes": True}


# The JWT token we send back after a successful login

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"



# The data packed inside the JWT token

class TokenData(BaseModel):
    user_id: int | None = None
