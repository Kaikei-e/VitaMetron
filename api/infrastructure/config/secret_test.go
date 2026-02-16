package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestReadSecret_FromFile(t *testing.T) {
	dir := t.TempDir()
	originalDir := secretsDir
	secretsDir = dir
	t.Cleanup(func() { secretsDir = originalDir })

	if err := os.WriteFile(filepath.Join(dir, "test_secret"), []byte("  file-value  \n"), 0600); err != nil {
		t.Fatal(err)
	}

	got := ReadSecret("test_secret")
	if got != "file-value" {
		t.Errorf("ReadSecret() = %q, want %q", got, "file-value")
	}
}

func TestReadSecret_FallbackToEnv(t *testing.T) {
	dir := t.TempDir()
	originalDir := secretsDir
	secretsDir = dir
	t.Cleanup(func() { secretsDir = originalDir })

	t.Setenv("TEST_SECRET", "env-value")

	got := ReadSecret("test_secret")
	if got != "env-value" {
		t.Errorf("ReadSecret() = %q, want %q", got, "env-value")
	}
}

func TestReadSecret_BothMissing_ReturnsEmpty(t *testing.T) {
	dir := t.TempDir()
	originalDir := secretsDir
	secretsDir = dir
	t.Cleanup(func() { secretsDir = originalDir })

	got := ReadSecret("nonexistent")
	if got != "" {
		t.Errorf("ReadSecret() = %q, want empty string", got)
	}
}

func TestMustReadSecret_Panics_WhenEmpty(t *testing.T) {
	dir := t.TempDir()
	originalDir := secretsDir
	secretsDir = dir
	t.Cleanup(func() { secretsDir = originalDir })

	defer func() {
		if r := recover(); r == nil {
			t.Error("MustReadSecret() did not panic for missing secret")
		}
	}()

	MustReadSecret("missing_secret")
}

func TestMustReadSecret_Returns_WhenPresent(t *testing.T) {
	dir := t.TempDir()
	originalDir := secretsDir
	secretsDir = dir
	t.Cleanup(func() { secretsDir = originalDir })

	if err := os.WriteFile(filepath.Join(dir, "present"), []byte("value"), 0600); err != nil {
		t.Fatal(err)
	}

	got := MustReadSecret("present")
	if got != "value" {
		t.Errorf("MustReadSecret() = %q, want %q", got, "value")
	}
}
