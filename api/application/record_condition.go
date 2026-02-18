package application

import (
	"context"
	"time"

	"vitametron/api/domain/entity"
	"vitametron/api/domain/port"
)

type RecordConditionUseCase struct {
	repo port.ConditionRepository
}

func NewRecordConditionUseCase(repo port.ConditionRepository) *RecordConditionUseCase {
	return &RecordConditionUseCase{repo: repo}
}

func (uc *RecordConditionUseCase) Create(ctx context.Context, log *entity.ConditionLog) error {
	// Auto-compute legacy Overall from OverallVAS if not set
	if log.Overall == 0 {
		log.Overall = entity.VASToLegacyOverall(log.OverallVAS)
	}
	if err := log.Validate(); err != nil {
		return err
	}
	return uc.repo.Create(ctx, log)
}

func (uc *RecordConditionUseCase) GetByID(ctx context.Context, id int64) (*entity.ConditionLog, error) {
	log, err := uc.repo.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if log == nil {
		return nil, entity.ErrNotFound
	}
	return log, nil
}

func (uc *RecordConditionUseCase) List(ctx context.Context, filter entity.ConditionFilter) (*entity.ConditionListResult, error) {
	if filter.Limit <= 0 {
		filter.Limit = 20
	}
	if filter.Limit > 100 {
		filter.Limit = 100
	}
	return uc.repo.List(ctx, filter)
}

func (uc *RecordConditionUseCase) Update(ctx context.Context, id int64, log *entity.ConditionLog) error {
	// Auto-compute legacy Overall from OverallVAS if not set
	if log.Overall == 0 {
		log.Overall = entity.VASToLegacyOverall(log.OverallVAS)
	}
	if err := log.Validate(); err != nil {
		return err
	}
	existing, err := uc.repo.GetByID(ctx, id)
	if err != nil {
		return err
	}
	if existing == nil {
		return entity.ErrNotFound
	}
	log.ID = id
	return uc.repo.Update(ctx, log)
}

func (uc *RecordConditionUseCase) Delete(ctx context.Context, id int64) error {
	return uc.repo.Delete(ctx, id)
}

func (uc *RecordConditionUseCase) GetTags(ctx context.Context) ([]entity.TagCount, error) {
	return uc.repo.GetTags(ctx)
}

func (uc *RecordConditionUseCase) GetSummary(ctx context.Context, from, to time.Time) (*entity.ConditionSummary, error) {
	return uc.repo.GetSummary(ctx, from, to)
}
