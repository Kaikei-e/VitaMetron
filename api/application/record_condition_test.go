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

func TestRecordCondition_List(t *testing.T) {
	now := time.Now()
	expected := []entity.ConditionLog{
		{ID: 1, Overall: 3, LoggedAt: now},
		{ID: 2, Overall: 5, LoggedAt: now},
	}
	repo := &mocks.MockConditionRepository{
		ListFunc: func(_ context.Context, _, _ time.Time) ([]entity.ConditionLog, error) {
			return expected, nil
		},
	}
	uc := NewRecordConditionUseCase(repo)

	results, err := uc.List(context.Background(), now.Add(-24*time.Hour), now)
	if err != nil {
		t.Fatalf("List() error = %v", err)
	}
	if len(results) != 2 {
		t.Errorf("List() returned %d items, want 2", len(results))
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
		GetTagsFunc: func(_ context.Context) ([]string, error) {
			return []string{"headache", "tired"}, nil
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
