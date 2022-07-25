"""Module for encryption and decryption compatible with MetaMask."""
from base64 import a85decode, a85encode

# PyNaCl==1.5.0
from nacl.public import Box, PrivateKey, PublicKey

import secrets

def _hex_to_bytes(hex: str) -> bytes:
  return bytes.fromhex(hex[2:] if hex[:2] == "0x" else hex)

def get_public_key(private_key_hex: str) -> bytes:
  """Export public key for contract join request.

  Args:
    private_key: hex string representing private key

  Returns:
    32 bytes representing public key
  """
  return bytes(PrivateKey(_hex_to_bytes(private_key_hex)).public_key)

def encrypt_nacl(public_key: bytes, data: bytes) -> bytes:
  """Encryption function using NaCl box compatible with MetaMask
  For implementation used in MetaMask look into: https://github.com/MetaMask/eth-sig-util

  Args:
    public_key: public key of recipient (32 bytes)
    data: message data

  Returns:
    encrypted data
  """
  emph_key = PrivateKey.generate()
  enc_box = Box(emph_key, PublicKey(public_key))
  # Encryption must work with MetaMask decryption (requires valid utf-8)
  data = a85encode(data)
  ciphertext = enc_box.encrypt(data)
  return bytes(emph_key.public_key) + ciphertext

def decrypt_nacl(private_key: bytes, data: bytes) -> bytes:
  """Decryption function using NaCl box compatible with MetaMask
  For implementation used in MetaMask look into: https://github.com/MetaMask/eth-sig-util

  Args:
    private_key: private key to decrypt with
    data: encrypted message data

  Returns:
    decrypted data
  """
  emph_key, ciphertext = data[:32], data[32:]
  box = Box(PrivateKey(private_key), PublicKey(emph_key))
  return a85decode(box.decrypt(ciphertext))

'''
private_key = "0xc718adce055a99f9f81ec53b8d058ae372ba838b471eb5b5db49d79dc27a017f"
public_key = get_public_key(private_key)
print("Public key: ")
print(public_key.hex())

secret = secrets.token_bytes(nbytes=32)
print("\nsecret: ")
print(secret)

cipher_text = encrypt_nacl(public_key, secret)
print("\ncipher text: ")
print(cipher_text)

original_secret = decrypt_nacl(_hex_to_bytes(private_key), cipher_text)
print("\noriginal text: ")
print(original_secret)
'''