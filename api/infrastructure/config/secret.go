package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// secretsDir is the base directory for Docker secrets.
// Overridden in tests.
var secretsDir = "/run/secrets"

// ReadSecret reads a secret by name.
// It first checks /run/secrets/{name}, then falls back to os.Getenv(NAME).
// Returns empty string if neither source has a value.
func ReadSecret(name string) string {
	data, err := os.ReadFile(filepath.Join(secretsDir, name))
	if err == nil {
		return strings.TrimSpace(string(data))
	}
	return os.Getenv(strings.ToUpper(name))
}

// MustReadSecret calls ReadSecret and panics if the result is empty.
// Use this at startup for required secrets.
func MustReadSecret(name string) string {
	v := ReadSecret(name)
	if v == "" {
		panic(fmt.Sprintf("required secret %q is not set", name))
	}
	return v
}
