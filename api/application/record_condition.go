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
	if err := log.Validate(); err != nil {
		return err
	}
	return uc.repo.Create(ctx, log)
}

func (uc *RecordConditionUseCase) List(ctx context.Context, from, to time.Time) ([]entity.ConditionLog, error) {
	return uc.repo.List(ctx, from, to)
}

func (uc *RecordConditionUseCase) Delete(ctx context.Context, id int64) error {
	return uc.repo.Delete(ctx, id)
}

func (uc *RecordConditionUseCase) GetTags(ctx context.Context) ([]string, error) {
	return uc.repo.GetTags(ctx)
}
