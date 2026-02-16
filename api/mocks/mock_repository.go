package mocks

import (
	"context"
	"time"

	"vitametron/api/domain/entity"
)

type MockConditionRepository struct {
	CreateFunc  func(ctx context.Context, log *entity.ConditionLog) error
	ListFunc    func(ctx context.Context, from, to time.Time) ([]entity.ConditionLog, error)
	DeleteFunc  func(ctx context.Context, id int64) error
	GetTagsFunc func(ctx context.Context) ([]string, error)
}

func (m *MockConditionRepository) Create(ctx context.Context, log *entity.ConditionLog) error {
	return m.CreateFunc(ctx, log)
}

func (m *MockConditionRepository) List(ctx context.Context, from, to time.Time) ([]entity.ConditionLog, error) {
	return m.ListFunc(ctx, from, to)
}

func (m *MockConditionRepository) Delete(ctx context.Context, id int64) error {
	return m.DeleteFunc(ctx, id)
}

func (m *MockConditionRepository) GetTags(ctx context.Context) ([]string, error) {
	return m.GetTagsFunc(ctx)
}

type MockDailySummaryRepository struct {
	UpsertFunc    func(ctx context.Context, summary *entity.DailySummary) error
	GetByDateFunc func(ctx context.Context, date time.Time) (*entity.DailySummary, error)
	ListRangeFunc func(ctx context.Context, from, to time.Time) ([]entity.DailySummary, error)
}

func (m *MockDailySummaryRepository) Upsert(ctx context.Context, summary *entity.DailySummary) error {
	return m.UpsertFunc(ctx, summary)
}

func (m *MockDailySummaryRepository) GetByDate(ctx context.Context, date time.Time) (*entity.DailySummary, error) {
	return m.GetByDateFunc(ctx, date)
}

func (m *MockDailySummaryRepository) ListRange(ctx context.Context, from, to time.Time) ([]entity.DailySummary, error) {
	return m.ListRangeFunc(ctx, from, to)
}

type MockHeartRateRepository struct {
	BulkUpsertFunc func(ctx context.Context, samples []entity.HeartRateSample) error
	ListRangeFunc  func(ctx context.Context, from, to time.Time) ([]entity.HeartRateSample, error)
}

func (m *MockHeartRateRepository) BulkUpsert(ctx context.Context, samples []entity.HeartRateSample) error {
	return m.BulkUpsertFunc(ctx, samples)
}

func (m *MockHeartRateRepository) ListRange(ctx context.Context, from, to time.Time) ([]entity.HeartRateSample, error) {
	return m.ListRangeFunc(ctx, from, to)
}

type MockSleepStageRepository struct {
	BulkUpsertFunc func(ctx context.Context, stages []entity.SleepStage) error
	ListByDateFunc func(ctx context.Context, date time.Time) ([]entity.SleepStage, error)
}

func (m *MockSleepStageRepository) BulkUpsert(ctx context.Context, stages []entity.SleepStage) error {
	return m.BulkUpsertFunc(ctx, stages)
}

func (m *MockSleepStageRepository) ListByDate(ctx context.Context, date time.Time) ([]entity.SleepStage, error) {
	return m.ListByDateFunc(ctx, date)
}

type MockExerciseRepository struct {
	UpsertFunc    func(ctx context.Context, log *entity.ExerciseLog) error
	ListRangeFunc func(ctx context.Context, from, to time.Time) ([]entity.ExerciseLog, error)
}

func (m *MockExerciseRepository) Upsert(ctx context.Context, log *entity.ExerciseLog) error {
	return m.UpsertFunc(ctx, log)
}

func (m *MockExerciseRepository) ListRange(ctx context.Context, from, to time.Time) ([]entity.ExerciseLog, error) {
	return m.ListRangeFunc(ctx, from, to)
}

type MockTokenRepository struct {
	GetFunc  func(ctx context.Context, provider string) ([]byte, []byte, time.Time, error)
	SaveFunc func(ctx context.Context, provider string, accessToken, refreshToken []byte, expiresAt time.Time) error
}

func (m *MockTokenRepository) Get(ctx context.Context, provider string) ([]byte, []byte, time.Time, error) {
	return m.GetFunc(ctx, provider)
}

func (m *MockTokenRepository) Save(ctx context.Context, provider string, accessToken, refreshToken []byte, expiresAt time.Time) error {
	return m.SaveFunc(ctx, provider, accessToken, refreshToken, expiresAt)
}

type MockPredictionRepository struct {
	SaveFunc      func(ctx context.Context, pred *entity.ConditionPrediction) error
	GetByDateFunc func(ctx context.Context, date time.Time) (*entity.ConditionPrediction, error)
}

func (m *MockPredictionRepository) Save(ctx context.Context, pred *entity.ConditionPrediction) error {
	return m.SaveFunc(ctx, pred)
}

func (m *MockPredictionRepository) GetByDate(ctx context.Context, date time.Time) (*entity.ConditionPrediction, error) {
	return m.GetByDateFunc(ctx, date)
}
