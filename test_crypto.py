import crypto_utils

def test_encryption():
    user = "my_instagram_username"
    pw = "my_secure_password_123!"
    
    print("Original credentials:")
    print(f"User: {user}")
    print(f"Pass: {pw}")
    
    # Encrypt
    enc = crypto_utils.encrypt_credentials(user, pw)
    print("\nEncrypted String (Base64):")
    print(enc)
    
    # Decrypt
    dec = crypto_utils.decrypt_credentials(enc)
    if dec:
        dec_user, dec_pw = dec
        print("\nDecrypted credentials:")
        print(f"User: {dec_user}")
        print(f"Pass: {dec_pw}")
        
        if dec_user == user and dec_pw == pw:
            print("\nVerification: SUCCESS!")
        else:
            print("\nVerification: FAILED! Decrypted data doesn't match.")
    else:
        print("\nVerification: FAILED! Decryption returned None.")

if __name__ == "__main__":
    test_encryption()
