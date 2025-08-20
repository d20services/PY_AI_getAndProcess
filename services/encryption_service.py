from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

def decrypt_file(encrypted_data):
    return encrypted_data
    # return private_key.decrypt(
    #     encrypted_data,
    #     padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    # ).decode("utf-8")