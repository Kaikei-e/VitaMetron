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

	"vitametron/api/adapter/fitbit"
	"vitametron/api/adapter/mlclient"
	"vitametron/api/adapter/postgres"
	"vitametron/api/application"
	"vitametron/api/handler"
	"vitametron/api/infrastructure/cache"
	"vitametron/api/infrastructure/config"
	"vitametron/api/infrastructure/crypto"
	"vitametron/api/infrastructure/database"
	"vitametron/api/infrastructure/scheduler"
	"vitametron/api/infrastructure/server"
)

func main() {
	cfg := config.Load()

	// Run migrations before opening the connection pool
	if err := database.RunMigrations(cfg.DB.DSN()); err != nil {
		log.Fatalf("failed to run migrations: %v", err)
	}
	log.Println("database migrations applied")

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

	// Crypto
	enc, err := crypto.NewEncryptor(cfg.Fitbit.EncryptionKey)
	if err != nil {
		log.Fatalf("failed to init encryptor: %v", err)
	}

	// Adapters
	conditionRepo := postgres.NewConditionRepo(pool)
	summaryRepo := postgres.NewDailySummaryRepo(pool)
	hrRepo := postgres.NewHeartRateRepo(pool)
	sleepRepo := postgres.NewSleepStageRepo(pool)
	exerciseRepo := postgres.NewExerciseRepo(pool)
	tokenRepo := postgres.NewTokenRepo(pool)
	qualityRepo := postgres.NewDataQualityRepo(pool)
	vriRepo := postgres.NewVRIRepo(pool)
	mlClient := mlclient.New(cfg.ML.URL)

	// Fitbit OAuth + Client
	fitbitOAuth := fitbit.NewFitbitOAuth(cfg.Fitbit, rdb, tokenRepo, enc)
	fitbitClient := fitbit.NewFitbitClient(fitbitOAuth)

	who5Repo := postgres.NewWHO5Repo(pool)

	// Use cases
	conditionUC := application.NewRecordConditionUseCase(conditionRepo)
	who5UC := application.NewWHO5UseCase(who5Repo)
	insightsUC := application.NewGetInsightsUseCase(mlClient)
	syncUC := application.NewSyncBiometricsUseCase(fitbitClient, summaryRepo, hrRepo, sleepRepo, exerciseRepo, qualityRepo)

	// Handlers
	conditionHandler := handler.NewConditionHandler(conditionUC)
	who5Handler := handler.NewWHO5Handler(who5UC)
	insightsHandler := handler.NewInsightsHandler(insightsUC)
	biometricsHandler := handler.NewBiometricsHandler(summaryRepo, hrRepo, sleepRepo, qualityRepo)
	oauthHandler := handler.NewOAuthHandler(fitbitOAuth, syncUC)
	syncHandler := handler.NewSyncHandler(syncUC)
	importUC := application.NewImportHealthConnectUseCase(summaryRepo, hrRepo, sleepRepo, exerciseRepo)
	importHandler := handler.NewImportHandler(importUC, rdb, cfg.Preprocessor.UploadDir)
	anomalyRepo := postgres.NewAnomalyRepo(pool)
	divergenceRepo := postgres.NewDivergenceRepo(pool)
	vriHandler := handler.NewVRIHandler(mlClient, vriRepo)
	anomalyHandler := handler.NewAnomalyHandler(mlClient, anomalyRepo)
	divergenceHandler := handler.NewDivergenceHandler(mlClient, divergenceRepo)
	hrvHandler := handler.NewHRVHandler(mlClient)
	weeklyInsightsHandler := handler.NewWeeklyInsightsHandler(mlClient)
	healthkitHandler := handler.NewHealthKitHandler(rdb, cfg.Preprocessor.URL, cfg.Preprocessor.UploadDir)

	// Scheduler
	interval := cfg.Sync.IntervalMin
	if interval < 5 {
		interval = 5
	}
	sched := scheduler.New(syncUC, fitbitOAuth, time.Duration(interval)*time.Minute)
	sched.Start()
	log.Printf("sync scheduler started: every %d minutes", interval)

	// Server
	srv := server.New()

	// Health checks
	srv.RegisterHealthRoutes(&pgxPinger{pool}, &redisPinger{rdb})

	// Routes
	api := srv.Echo.Group("/api")
	conditionHandler.Register(api)
	who5Handler.Register(api)
	insightsHandler.Register(api)
	biometricsHandler.Register(api)
	oauthHandler.Register(api)
	syncHandler.Register(api)
	importHandler.Register(api)
	vriHandler.Register(api)
	anomalyHandler.Register(api)
	divergenceHandler.Register(api)
	hrvHandler.Register(api)
	weeklyInsightsHandler.Register(api)
	healthkitHandler.Register(api)

	// Graceful shutdown
	go func() {
		if err := srv.Echo.Start(fmt.Sprintf(":%d", cfg.Server.Port)); err != nil {
			log.Printf("server stopped: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	sched.Stop()
	log.Println("sync scheduler stopped")

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
