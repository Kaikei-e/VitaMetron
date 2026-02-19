package healthconnect

import (
	"testing"
	"time"
)

func TestEpochMillisToJST(t *testing.T) {
	// 2026-02-19 05:30:00 UTC = 2026-02-19 14:30:00 JST
	// Unix millis for 2026-02-19 05:30:00 UTC
	ms := time.Date(2026, 2, 19, 5, 30, 0, 0, time.UTC).UnixMilli()

	got := EpochMillisToJST(ms)

	if got.Hour() != 14 || got.Minute() != 30 {
		t.Errorf("expected 14:30 JST, got %02d:%02d", got.Hour(), got.Minute())
	}
	if got.Location().String() != "JST" {
		t.Errorf("expected JST location, got %s", got.Location())
	}
	// Should round-trip back to the same UTC instant
	if got.UTC().Hour() != 5 || got.UTC().Minute() != 30 {
		t.Errorf("expected 05:30 UTC, got %v", got.UTC())
	}
}

func TestLocalDate(t *testing.T) {
	// 2026-02-19 05:30:00 UTC with JST offset (+9h = 32400s)
	ms := time.Date(2026, 2, 19, 5, 30, 0, 0, time.UTC).UnixMilli()

	got := LocalDate(ms, 9*3600)

	// In JST, this is 2026-02-19 14:30, so date should be 2026-02-19
	if got.Year() != 2026 || got.Month() != 2 || got.Day() != 19 {
		t.Errorf("expected 2026-02-19, got %v", got)
	}
	// Should be midnight in the local timezone
	if got.Hour() != 0 || got.Minute() != 0 {
		t.Errorf("expected midnight, got %02d:%02d", got.Hour(), got.Minute())
	}
}
