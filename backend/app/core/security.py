from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        hasher.verify(hashed, password)
        return True

    except VerifyMismatchError:
        return False



if __name__ == "__main__":
    pass


