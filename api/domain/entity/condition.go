package entity

import (
	"errors"
	"fmt"
	"time"
)

type ConditionLog struct {
	ID       int64
	LoggedAt time.Time
	// Legacy (kept for backward compatibility; new records auto-compute from VAS)
	Overall  int
	Mental   *int
	Physical *int
	Energy   *int
	// VAS 0-100 (primary evaluation dimensions)
	OverallVAS      int  // required (Well-being)
	MoodVAS         *int // optional
	EnergyVAS       *int // optional
	SleepQualityVAS *int // optional
	StressVAS       *int // optional
	Note            string
	Tags            []string
	CreatedAt       time.Time
}

type TagCount struct {
	Tag   string `json:"tag"`
	Count int    `json:"count"`
}

type ConditionFilter struct {
	From      time.Time
	To        time.Time
	Tag       string
	Limit     int
	Offset    int
	SortField string
	SortDir   string
}

type ConditionListResult struct {
	Items []ConditionLog `json:"items"`
	Total int            `json:"total"`
}

type ConditionSummary struct {
	TotalCount      int     `json:"total_count"`
	OverallAvg      float64 `json:"overall_avg"`
	OverallMin      int     `json:"overall_min"`
	OverallMax      int     `json:"overall_max"`
	MentalAvg       float64 `json:"mental_avg"`
	MentalMin       int     `json:"mental_min"`
	MentalMax       int     `json:"mental_max"`
	PhysicalAvg     float64 `json:"physical_avg"`
	PhysicalMin     int     `json:"physical_min"`
	PhysicalMax     int     `json:"physical_max"`
	EnergyAvg       float64 `json:"energy_avg"`
	EnergyMin       int     `json:"energy_min"`
	EnergyMax       int     `json:"energy_max"`
	OverallVASAvg      float64 `json:"overall_vas_avg"`
	OverallVASMin      int     `json:"overall_vas_min"`
	OverallVASMax      int     `json:"overall_vas_max"`
	MoodVASAvg         float64 `json:"mood_vas_avg"`
	MoodVASMin         int     `json:"mood_vas_min"`
	MoodVASMax         int     `json:"mood_vas_max"`
	EnergyVASAvg       float64 `json:"energy_vas_avg"`
	EnergyVASMin       int     `json:"energy_vas_min"`
	EnergyVASMax       int     `json:"energy_vas_max"`
	SleepQualityVASAvg float64 `json:"sleep_quality_vas_avg"`
	SleepQualityVASMin int     `json:"sleep_quality_vas_min"`
	SleepQualityVASMax int     `json:"sleep_quality_vas_max"`
	StressVASAvg       float64 `json:"stress_vas_avg"`
	StressVASMin       int     `json:"stress_vas_min"`
	StressVASMax       int     `json:"stress_vas_max"`
}

func (c *ConditionLog) Validate() error {
	// OverallVAS is required (0-100)
	if c.OverallVAS < 0 || c.OverallVAS > 100 {
		return fmt.Errorf("overall_vas must be between 0 and 100, got %d", c.OverallVAS)
	}
	if err := validateOptionalVAS("mood_vas", c.MoodVAS); err != nil {
		return err
	}
	if err := validateOptionalVAS("energy_vas", c.EnergyVAS); err != nil {
		return err
	}
	if err := validateOptionalVAS("sleep_quality_vas", c.SleepQualityVAS); err != nil {
		return err
	}
	if err := validateOptionalVAS("stress_vas", c.StressVAS); err != nil {
		return err
	}
	// Legacy fields: validate if present but not required
	if c.Overall != 0 {
		if c.Overall < 1 || c.Overall > 5 {
			return fmt.Errorf("overall must be between 1 and 5, got %d", c.Overall)
		}
	}
	if err := validateOptionalRange("mental", c.Mental); err != nil {
		return err
	}
	if err := validateOptionalRange("physical", c.Physical); err != nil {
		return err
	}
	if err := validateOptionalRange("energy", c.Energy); err != nil {
		return err
	}
	if len(c.Note) > 1000 {
		return errors.New("note must be 1000 characters or less")
	}
	if len(c.Tags) > 10 {
		return errors.New("tags must be 10 or fewer")
	}
	for _, tag := range c.Tags {
		if len(tag) > 50 {
			return fmt.Errorf("tag must be 50 characters or less, got %q", tag)
		}
	}
	return nil
}

// VASToLegacyOverall converts a VAS 0-100 score to legacy 1-5 scale.
func VASToLegacyOverall(vas int) int {
	v := vas/20 + 1
	if v < 1 {
		v = 1
	}
	if v > 5 {
		v = 5
	}
	return v
}

func validateOptionalVAS(name string, v *int) error {
	if v == nil {
		return nil
	}
	if *v < 0 || *v > 100 {
		return errors.New(name + " must be between 0 and 100")
	}
	return nil
}

func validateOptionalRange(name string, v *int) error {
	if v == nil {
		return nil
	}
	if *v < 1 || *v > 5 {
		return errors.New(name + " must be between 1 and 5")
	}
	return nil
}
