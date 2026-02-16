package cache

import (
	"fmt"

	"vitametron/api/infrastructure/config"
	"github.com/redis/go-redis/v9"
)

func NewRedis(cfg config.RedisConfig) *redis.Client {
	return redis.NewClient(&redis.Options{
		Addr:     fmt.Sprintf("%s:%d", cfg.Host, cfg.Port),
		Password: cfg.Password,
	})
}

// Addr returns the Redis address string for testing.
func Addr(cfg config.RedisConfig) string {
	return fmt.Sprintf("%s:%d", cfg.Host, cfg.Port)
}
