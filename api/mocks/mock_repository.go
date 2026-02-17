package mocks

import (
	"context"
	"time"

	"vitametron/api/domain/entity"
)

type MockConditionRepository struct {
	CreateFunc     func(ctx context.Context, log *entity.ConditionLog) error
	GetByIDFunc    func(ctx context.Context, id int64) (*entity.ConditionLog, error)
	ListFunc       func(ctx context.Context, filter entity.ConditionFilter) (*entity.ConditionListResult, error)
	UpdateFunc     func(ctx context.Context, log *entity.ConditionLog) error
	DeleteFunc     func(ctx context.Context, id int64) error
	GetTagsFunc    func(ctx context.Context) ([]entity.TagCount, error)
	GetSummaryFunc func(ctx context.Context, from, to time.Time) (*entity.ConditionSummary, error)
}

func (m *MockConditionRepository) Create(ctx context.Context, log *entity.ConditionLog) error {
	return m.CreateFunc(ctx, log)
}

func (m *MockConditionRepository) GetByID(ctx context.Context, id int64) (*entity.ConditionLog, error) {
	return m.GetByIDFunc(ctx, id)
}

func (m *MockConditionRepository) List(ctx context.Context, filter entity.ConditionFilter) (*entity.ConditionListResult, error) {
	return m.ListFunc(ctx, filter)
}

func (m *MockConditionRepository) Update(ctx context.Context, log *entity.ConditionLog) error {
	return m.UpdateFunc(ctx, log)
}

func (m *MockConditionRepository) Delete(ctx context.Context, id int64) error {
	return m.DeleteFunc(ctx, id)
}

func (m *MockConditionRepository) GetTags(ctx context.Context) ([]entity.TagCount, error) {
	return m.GetTagsFunc(ctx)
}

func (m *MockConditionRepository) GetSummary(ctx context.Context, from, to time.Time) (*entity.ConditionSummary, error) {
	return m.GetSummaryFunc(ctx, from, to)
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
	BulkUpsertFunc      func(ctx context.Context, stages []entity.SleepStage) error
	ListByDateFunc      func(ctx context.Context, date time.Time) ([]entity.SleepStage, error)
	ListByTimeRangeFunc func(ctx context.Context, from, to time.Time) ([]entity.SleepStage, error)
}

func (m *MockSleepStageRepository) BulkUpsert(ctx context.Context, stages []entity.SleepStage) error {
	return m.BulkUpsertFunc(ctx, stages)
}

func (m *MockSleepStageRepository) ListByDate(ctx context.Context, date time.Time) ([]entity.SleepStage, error) {
	return m.ListByDateFunc(ctx, date)
}

func (m *MockSleepStageRepository) ListByTimeRange(ctx context.Context, from, to time.Time) ([]entity.SleepStage, error) {
	return m.ListByTimeRangeFunc(ctx, from, to)
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
	GetFunc    func(ctx context.Context, provider string) ([]byte, []byte, time.Time, error)
	SaveFunc   func(ctx context.Context, provider string, accessToken, refreshToken []byte, expiresAt time.Time) error
	DeleteFunc func(ctx context.Context, provider string) error
}

func (m *MockTokenRepository) Get(ctx context.Context, provider string) ([]byte, []byte, time.Time, error) {
	return m.GetFunc(ctx, provider)
}

func (m *MockTokenRepository) Save(ctx context.Context, provider string, accessToken, refreshToken []byte, expiresAt time.Time) error {
	return m.SaveFunc(ctx, provider, accessToken, refreshToken, expiresAt)
}

func (m *MockTokenRepository) Delete(ctx context.Context, provider string) error {
	return m.DeleteFunc(ctx, provider)
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

type MockDataQualityRepository struct {
	UpsertFunc         func(ctx context.Context, q *entity.DataQuality) error
	GetByDateFunc      func(ctx context.Context, date time.Time) (*entity.DataQuality, error)
	ListRangeFunc      func(ctx context.Context, from, to time.Time) ([]entity.DataQuality, error)
	CountValidDaysFunc func(ctx context.Context, before time.Time, windowDays int) (int, error)
}

func (m *MockDataQualityRepository) Upsert(ctx context.Context, q *entity.DataQuality) error {
	return m.UpsertFunc(ctx, q)
}

func (m *MockDataQualityRepository) GetByDate(ctx context.Context, date time.Time) (*entity.DataQuality, error) {
	return m.GetByDateFunc(ctx, date)
}

func (m *MockDataQualityRepository) ListRange(ctx context.Context, from, to time.Time) ([]entity.DataQuality, error) {
	return m.ListRangeFunc(ctx, from, to)
}

func (m *MockDataQualityRepository) CountValidDays(ctx context.Context, before time.Time, windowDays int) (int, error) {
	return m.CountValidDaysFunc(ctx, before, windowDays)
}

type MockAnomalyRepository struct {
	GetByDateFunc func(ctx context.Context, date time.Time) (*entity.AnomalyDetection, error)
	ListRangeFunc func(ctx context.Context, from, to time.Time) ([]entity.AnomalyDetection, error)
}

func (m *MockAnomalyRepository) GetByDate(ctx context.Context, date time.Time) (*entity.AnomalyDetection, error) {
	return m.GetByDateFunc(ctx, date)
}

func (m *MockAnomalyRepository) ListRange(ctx context.Context, from, to time.Time) ([]entity.AnomalyDetection, error) {
	return m.ListRangeFunc(ctx, from, to)
}

type MockDivergenceRepository struct {
	GetByDateFunc func(ctx context.Context, date time.Time) (*entity.DivergenceDetection, error)
	ListRangeFunc func(ctx context.Context, from, to time.Time) ([]entity.DivergenceDetection, error)
}

func (m *MockDivergenceRepository) GetByDate(ctx context.Context, date time.Time) (*entity.DivergenceDetection, error) {
	return m.GetByDateFunc(ctx, date)
}

func (m *MockDivergenceRepository) ListRange(ctx context.Context, from, to time.Time) ([]entity.DivergenceDetection, error) {
	return m.ListRangeFunc(ctx, from, to)
}

type MockVRIRepository struct {
	GetByDateFunc func(ctx context.Context, date time.Time) (*entity.VRIScore, error)
	ListRangeFunc func(ctx context.Context, from, to time.Time) ([]entity.VRIScore, error)
}

func (m *MockVRIRepository) GetByDate(ctx context.Context, date time.Time) (*entity.VRIScore, error) {
	return m.GetByDateFunc(ctx, date)
}

func (m *MockVRIRepository) ListRange(ctx context.Context, from, to time.Time) ([]entity.VRIScore, error) {
	return m.ListRangeFunc(ctx, from, to)
}
