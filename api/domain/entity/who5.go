package entity

import (
	"errors"
	"fmt"
	"time"
)

type WHO5Assessment struct {
	ID          int64
	AssessedAt  time.Time
	PeriodStart time.Time
	PeriodEnd   time.Time
	Items       [5]int // each 0-5
	RawScore    int    // 0-25
	Percentage  int    // 0-100
	Note        string
	CreatedAt   time.Time
}

func (w *WHO5Assessment) Validate() error {
	for i, item := range w.Items {
		if item < 0 || item > 5 {
			return fmt.Errorf("item%d must be between 0 and 5, got %d", i+1, item)
		}
	}
	if w.PeriodStart.IsZero() {
		return errors.New("period_start is required")
	}
	if w.PeriodEnd.IsZero() {
		return errors.New("period_end is required")
	}
	if w.PeriodEnd.Before(w.PeriodStart) {
		return errors.New("period_end must be after period_start")
	}
	if len(w.Note) > 1000 {
		return errors.New("note must be 1000 characters or less")
	}
	return nil
}

// ComputeScores calculates RawScore and Percentage from Items.
func (w *WHO5Assessment) ComputeScores() {
	sum := 0
	for _, v := range w.Items {
		sum += v
	}
	w.RawScore = sum
	w.Percentage = sum * 4
}
