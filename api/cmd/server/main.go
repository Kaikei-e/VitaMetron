package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"

	"vitametron/api/adapter/mlclient"
	"vitametron/api/adapter/postgres"
	"vitametron/api/application"
	"vitametron/api/handler"
	"vitametron/api/infrastructure/cache"
	"vitametron/api/infrastructure/config"
	"vitametron/api/infrastructure/database"
	"vitametron/api/infrastructure/server"
)

func main() {
	cfg := config.Load()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// Database
	pool, err := database.NewPool(ctx, cfg.DB)
	if err != nil {
		log.Fatalf("failed to connect to database: %v", err)
	}
	defer pool.Close()

	// Redis
	rdb := cache.NewRedis(cfg.Redis)
	defer rdb.Close()

	// Adapters
	conditionRepo := postgres.NewConditionRepo(pool)
	summaryRepo := postgres.NewDailySummaryRepo(pool)
	hrRepo := postgres.NewHeartRateRepo(pool)
	sleepRepo := postgres.NewSleepStageRepo(pool)
	exerciseRepo := postgres.NewExerciseRepo(pool)
	mlClient := mlclient.New(cfg.ML.URL)

	// Use cases
	conditionUC := application.NewRecordConditionUseCase(conditionRepo)
	insightsUC := application.NewGetInsightsUseCase(mlClient)
	// Note: SyncUseCase requires a BiometricsProvider (e.g., Fitbit adapter) not yet wired
	_ = hrRepo
	_ = sleepRepo
	_ = exerciseRepo

	// Handlers
	conditionHandler := handler.NewConditionHandler(conditionUC)
	insightsHandler := handler.NewInsightsHandler(insightsUC)
	biometricsHandler := handler.NewBiometricsHandler(summaryRepo)

	// Server
	srv := server.New()

	// Health checks
	srv.RegisterHealthRoutes(&pgxPinger{pool}, &redisPinger{rdb})

	// Routes
	api := srv.Echo.Group("/api")
	conditionHandler.Register(api)
	insightsHandler.Register(api)
	biometricsHandler.Register(api)

	// Graceful shutdown
	go func() {
		if err := srv.Echo.Start(fmt.Sprintf(":%d", cfg.Server.Port)); err != nil {
			log.Printf("server stopped: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	if err := srv.Echo.Shutdown(shutdownCtx); err != nil {
		log.Fatalf("server shutdown failed: %v", err)
	}
	log.Println("server exited gracefully")
}

type pgxPinger struct {
	pool *pgxpool.Pool
}

func (p *pgxPinger) Ping(ctx context.Context) error {
	return p.pool.Ping(ctx)
}

type redisPinger struct {
	client *redis.Client
}

func (p *redisPinger) Ping(ctx context.Context) error {
	return p.client.Ping(ctx).Err()
}
