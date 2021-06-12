import hmac
import binascii
import uuid
import sys


def gen_flag(base: str, flag: str, key: str, user: uuid.UUID) -> str:
    flag_part = "{" + flag + "}" + f"{user}"
    hash = hmac.digest(key.encode(), flag_part.encode(), "sha256")
    return base + "{" + flag + "_" + binascii.hexlify(hash).decode()[0:14] + "}"


if __name__ == "__main__":
    if len(sys.argv) != (1 + 4):
        print(f"Usage: {sys.argv[0]} <base> <flag> <key> <user uuid>")

    print(gen_flag(*sys.argv[1:4], uuid.UUID(sys.argv[4])))
