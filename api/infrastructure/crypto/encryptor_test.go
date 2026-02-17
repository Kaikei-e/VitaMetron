package crypto

import (
	"bytes"
	"encoding/base64"
	"testing"
)

func validKey() string {
	key := make([]byte, 32)
	for i := range key {
		key[i] = byte(i)
	}
	return base64.StdEncoding.EncodeToString(key)
}

func TestRoundTrip(t *testing.T) {
	enc, err := NewEncryptor(validKey())
	if err != nil {
		t.Fatal(err)
	}

	plaintext := []byte("secret token value")
	ciphertext, err := enc.Encrypt(plaintext)
	if err != nil {
		t.Fatal(err)
	}

	decrypted, err := enc.Decrypt(ciphertext)
	if err != nil {
		t.Fatal(err)
	}

	if !bytes.Equal(plaintext, decrypted) {
		t.Errorf("decrypted = %q, want %q", decrypted, plaintext)
	}
}

func TestEncryptProducesDifferentCiphertexts(t *testing.T) {
	enc, err := NewEncryptor(validKey())
	if err != nil {
		t.Fatal(err)
	}

	plaintext := []byte("same input")
	ct1, _ := enc.Encrypt(plaintext)
	ct2, _ := enc.Encrypt(plaintext)

	if bytes.Equal(ct1, ct2) {
		t.Error("two encryptions of the same plaintext should differ (unique nonces)")
	}
}

func TestInvalidKeyLength(t *testing.T) {
	shortKey := base64.StdEncoding.EncodeToString([]byte("too short"))
	_, err := NewEncryptor(shortKey)
	if err == nil {
		t.Fatal("expected error for short key")
	}
}

func TestInvalidBase64Key(t *testing.T) {
	_, err := NewEncryptor("not-valid-base64!!!")
	if err == nil {
		t.Fatal("expected error for invalid base64")
	}
}

func TestDecryptTamperedCiphertext(t *testing.T) {
	enc, err := NewEncryptor(validKey())
	if err != nil {
		t.Fatal(err)
	}

	ciphertext, err := enc.Encrypt([]byte("sensitive data"))
	if err != nil {
		t.Fatal(err)
	}

	// Tamper with the ciphertext
	ciphertext[len(ciphertext)-1] ^= 0xFF

	_, err = enc.Decrypt(ciphertext)
	if err == nil {
		t.Fatal("expected error for tampered ciphertext")
	}
}

func TestDecryptTooShort(t *testing.T) {
	enc, err := NewEncryptor(validKey())
	if err != nil {
		t.Fatal(err)
	}

	_, err = enc.Decrypt([]byte("short"))
	if err == nil {
		t.Fatal("expected error for short ciphertext")
	}
}

func TestEmptyPlaintext(t *testing.T) {
	enc, err := NewEncryptor(validKey())
	if err != nil {
		t.Fatal(err)
	}

	ciphertext, err := enc.Encrypt([]byte{})
	if err != nil {
		t.Fatal(err)
	}

	decrypted, err := enc.Decrypt(ciphertext)
	if err != nil {
		t.Fatal(err)
	}

	if len(decrypted) != 0 {
		t.Errorf("expected empty plaintext, got %d bytes", len(decrypted))
	}
}
