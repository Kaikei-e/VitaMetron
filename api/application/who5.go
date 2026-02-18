package application

import (
	"context"
	"time"

	"vitametron/api/domain/entity"
	"vitametron/api/domain/port"
)

type WHO5UseCase struct {
	repo port.WHO5Repository
}

func NewWHO5UseCase(repo port.WHO5Repository) *WHO5UseCase {
	return &WHO5UseCase{repo: repo}
}

func (uc *WHO5UseCase) Create(ctx context.Context, a *entity.WHO5Assessment) error {
	if a.AssessedAt.IsZero() {
		a.AssessedAt = time.Now()
	}
	if err := a.Validate(); err != nil {
		return err
	}
	a.ComputeScores()
	return uc.repo.Create(ctx, a)
}

func (uc *WHO5UseCase) GetLatest(ctx context.Context) (*entity.WHO5Assessment, error) {
	return uc.repo.GetLatest(ctx)
}

func (uc *WHO5UseCase) GetByID(ctx context.Context, id int64) (*entity.WHO5Assessment, error) {
	a, err := uc.repo.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if a == nil {
		return nil, entity.ErrNotFound
	}
	return a, nil
}

func (uc *WHO5UseCase) List(ctx context.Context, limit, offset int) ([]entity.WHO5Assessment, int, error) {
	if limit <= 0 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}
	return uc.repo.List(ctx, limit, offset)
}
