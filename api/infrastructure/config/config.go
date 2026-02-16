package config

import (
	"fmt"
	"os"
	"strconv"
)

type Config struct {
	DB     DBConfig
	Redis  RedisConfig
	Fitbit FitbitConfig
	Server ServerConfig
	ML     MLConfig
}

type DBConfig struct {
	Host     string
	Port     int
	Name     string
	User     string
	Password string
	SSLMode  string
}

// DSN returns a PostgreSQL connection string.
func (c DBConfig) DSN() string {
	userInfo := c.User
	if c.Password != "" {
		userInfo = c.User + ":" + c.Password
	}
	return fmt.Sprintf("postgres://%s@%s:%d/%s?sslmode=%s",
		userInfo, c.Host, c.Port, c.Name, c.SSLMode)
}

type RedisConfig struct {
	Host     string
	Port     int
	Password string
}

type FitbitConfig struct {
	ClientID     string
	ClientSecret string
	RedirectURI  string
}

type ServerConfig struct {
	Port int
}

type MLConfig struct {
	URL string
}

// Load reads configuration from environment variables and secrets.
func Load() *Config {
	return &Config{
		DB: DBConfig{
			Host:     envOrDefault("DB_HOST", "postgres"),
			Port:     envIntOrDefault("DB_PORT", 5432),
			Name:     envOrDefault("DB_NAME", "vitametron"),
			User:     envOrDefault("DB_USER", "vitametron"),
			Password: ReadSecret("db_password"),
			SSLMode:  envOrDefault("DB_SSLMODE", "disable"),
		},
		Redis: RedisConfig{
			Host:     envOrDefault("REDIS_HOST", "redis"),
			Port:     envIntOrDefault("REDIS_PORT", 6379),
			Password: ReadSecret("redis_password"),
		},
		Fitbit: FitbitConfig{
			ClientID:     ReadSecret("fitbit_client_id"),
			ClientSecret: ReadSecret("fitbit_client_secret"),
			RedirectURI:  envOrDefault("FITBIT_REDIRECT_URI", ""),
		},
		Server: ServerConfig{
			Port: envIntOrDefault("SERVER_PORT", 8080),
		},
		ML: MLConfig{
			URL: envOrDefault("ML_SERVICE_URL", "http://ml:8000"),
		},
	}
}

func envOrDefault(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envIntOrDefault(key string, fallback int) int {
	if v := os.Getenv(key); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return fallback
}
