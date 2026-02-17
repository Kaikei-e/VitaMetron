package application

import (
	"context"
	"errors"
	"testing"
	"time"

	"vitametron/api/domain/entity"
	"vitametron/api/mocks"
)

func TestRecordCondition_Create_Success(t *testing.T) {
	var created bool
	repo := &mocks.MockConditionRepository{
		CreateFunc: func(_ context.Context, _ *entity.ConditionLog) error {
			created = true
			return nil
		},
	}
	uc := NewRecordConditionUseCase(repo)

	log := &entity.ConditionLog{Overall: 3, LoggedAt: time.Now()}
	if err := uc.Create(context.Background(), log); err != nil {
		t.Fatalf("Create() error = %v", err)
	}
	if !created {
		t.Error("repo.Create was not called")
	}
}

func TestRecordCondition_Create_ValidationError(t *testing.T) {
	var repoCalled bool
	repo := &mocks.MockConditionRepository{
		CreateFunc: func(_ context.Context, _ *entity.ConditionLog) error {
			repoCalled = true
			return nil
		},
	}
	uc := NewRecordConditionUseCase(repo)

	log := &entity.ConditionLog{Overall: 0} // invalid
	if err := uc.Create(context.Background(), log); err == nil {
		t.Error("Create() expected validation error, got nil")
	}
	if repoCalled {
		t.Error("repo.Create should not be called on validation error")
	}
}

func TestRecordCondition_Create_RepoError(t *testing.T) {
	repo := &mocks.MockConditionRepository{
		CreateFunc: func(_ context.Context, _ *entity.ConditionLog) error {
			return errors.New("db error")
		},
	}
	uc := NewRecordConditionUseCase(repo)

	log := &entity.ConditionLog{Overall: 3, LoggedAt: time.Now()}
	if err := uc.Create(context.Background(), log); err == nil {
		t.Error("Create() expected error from repo, got nil")
	}
}

func TestRecordCondition_GetByID_Success(t *testing.T) {
	expected := &entity.ConditionLog{ID: 1, Overall: 3, LoggedAt: time.Now()}
	repo := &mocks.MockConditionRepository{
		GetByIDFunc: func(_ context.Context, id int64) (*entity.ConditionLog, error) {
			if id != 1 {
				t.Errorf("GetByID() id = %d, want 1", id)
			}
			return expected, nil
		},
	}
	uc := NewRecordConditionUseCase(repo)

	result, err := uc.GetByID(context.Background(), 1)
	if err != nil {
		t.Fatalf("GetByID() error = %v", err)
	}
	if result.ID != expected.ID {
		t.Errorf("GetByID() ID = %d, want %d", result.ID, expected.ID)
	}
}

func TestRecordCondition_GetByID_NotFound(t *testing.T) {
	repo := &mocks.MockConditionRepository{
		GetByIDFunc: func(_ context.Context, _ int64) (*entity.ConditionLog, error) {
			return nil, nil
		},
	}
	uc := NewRecordConditionUseCase(repo)

	_, err := uc.GetByID(context.Background(), 999)
	if !errors.Is(err, entity.ErrNotFound) {
		t.Errorf("GetByID() error = %v, want ErrNotFound", err)
	}
}

func TestRecordCondition_List(t *testing.T) {
	now := time.Now()
	expected := &entity.ConditionListResult{
		Items: []entity.ConditionLog{
			{ID: 1, Overall: 3, LoggedAt: now},
			{ID: 2, Overall: 5, LoggedAt: now},
		},
		Total: 2,
	}
	repo := &mocks.MockConditionRepository{
		ListFunc: func(_ context.Context, filter entity.ConditionFilter) (*entity.ConditionListResult, error) {
			if filter.Limit != 20 {
				t.Errorf("List() default limit = %d, want 20", filter.Limit)
			}
			return expected, nil
		},
	}
	uc := NewRecordConditionUseCase(repo)

	result, err := uc.List(context.Background(), entity.ConditionFilter{
		From: now.Add(-24 * time.Hour),
		To:   now,
	})
	if err != nil {
		t.Fatalf("List() error = %v", err)
	}
	if len(result.Items) != 2 {
		t.Errorf("List() returned %d items, want 2", len(result.Items))
	}
}

func TestRecordCondition_List_LimitCapped(t *testing.T) {
	repo := &mocks.MockConditionRepository{
		ListFunc: func(_ context.Context, filter entity.ConditionFilter) (*entity.ConditionListResult, error) {
			if filter.Limit != 100 {
				t.Errorf("List() capped limit = %d, want 100", filter.Limit)
			}
			return &entity.ConditionListResult{}, nil
		},
	}
	uc := NewRecordConditionUseCase(repo)

	_, err := uc.List(context.Background(), entity.ConditionFilter{Limit: 500})
	if err != nil {
		t.Fatalf("List() error = %v", err)
	}
}

func TestRecordCondition_Update_Success(t *testing.T) {
	existing := &entity.ConditionLog{ID: 1, Overall: 3, LoggedAt: time.Now()}
	var updated bool
	repo := &mocks.MockConditionRepository{
		GetByIDFunc: func(_ context.Context, _ int64) (*entity.ConditionLog, error) {
			return existing, nil
		},
		UpdateFunc: func(_ context.Context, log *entity.ConditionLog) error {
			updated = true
			if log.ID != 1 {
				t.Errorf("Update() ID = %d, want 1", log.ID)
			}
			return nil
		},
	}
	uc := NewRecordConditionUseCase(repo)

	log := &entity.ConditionLog{Overall: 4, LoggedAt: time.Now()}
	if err := uc.Update(context.Background(), 1, log); err != nil {
		t.Fatalf("Update() error = %v", err)
	}
	if !updated {
		t.Error("repo.Update was not called")
	}
}

func TestRecordCondition_Update_ValidationError(t *testing.T) {
	repo := &mocks.MockConditionRepository{}
	uc := NewRecordConditionUseCase(repo)

	log := &entity.ConditionLog{Overall: 0} // invalid
	if err := uc.Update(context.Background(), 1, log); err == nil {
		t.Error("Update() expected validation error, got nil")
	}
}

func TestRecordCondition_Update_NotFound(t *testing.T) {
	repo := &mocks.MockConditionRepository{
		GetByIDFunc: func(_ context.Context, _ int64) (*entity.ConditionLog, error) {
			return nil, nil
		},
	}
	uc := NewRecordConditionUseCase(repo)

	log := &entity.ConditionLog{Overall: 3, LoggedAt: time.Now()}
	err := uc.Update(context.Background(), 999, log)
	if !errors.Is(err, entity.ErrNotFound) {
		t.Errorf("Update() error = %v, want ErrNotFound", err)
	}
}

func TestRecordCondition_Delete(t *testing.T) {
	repo := &mocks.MockConditionRepository{
		DeleteFunc: func(_ context.Context, id int64) error {
			if id != 42 {
				t.Errorf("Delete() id = %d, want 42", id)
			}
			return nil
		},
	}
	uc := NewRecordConditionUseCase(repo)

	if err := uc.Delete(context.Background(), 42); err != nil {
		t.Fatalf("Delete() error = %v", err)
	}
}

func TestRecordCondition_GetTags(t *testing.T) {
	repo := &mocks.MockConditionRepository{
		GetTagsFunc: func(_ context.Context) ([]entity.TagCount, error) {
			return []entity.TagCount{
				{Tag: "headache", Count: 5},
				{Tag: "tired", Count: 3},
			}, nil
		},
	}
	uc := NewRecordConditionUseCase(repo)

	tags, err := uc.GetTags(context.Background())
	if err != nil {
		t.Fatalf("GetTags() error = %v", err)
	}
	if len(tags) != 2 {
		t.Errorf("GetTags() returned %d tags, want 2", len(tags))
	}
	if tags[0].Count != 5 {
		t.Errorf("GetTags()[0].Count = %d, want 5", tags[0].Count)
	}
}

func TestRecordCondition_GetSummary(t *testing.T) {
	now := time.Now()
	expected := &entity.ConditionSummary{
		TotalCount: 10,
		OverallAvg: 3.5,
		OverallMin: 1,
		OverallMax: 5,
	}
	repo := &mocks.MockConditionRepository{
		GetSummaryFunc: func(_ context.Context, _, _ time.Time) (*entity.ConditionSummary, error) {
			return expected, nil
		},
	}
	uc := NewRecordConditionUseCase(repo)

	result, err := uc.GetSummary(context.Background(), now.Add(-7*24*time.Hour), now)
	if err != nil {
		t.Fatalf("GetSummary() error = %v", err)
	}
	if result.TotalCount != 10 {
		t.Errorf("GetSummary() TotalCount = %d, want 10", result.TotalCount)
	}
}
