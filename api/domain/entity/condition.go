package entity

import (
	"errors"
	"fmt"
	"time"
)

type ConditionLog struct {
	ID         int64
	LoggedAt   time.Time
	Overall    int
	Mental     *int
	Physical   *int
	Energy     *int
	OverallVAS *int
	Note       string
	Tags       []string
	CreatedAt  time.Time
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
	TotalCount int     `json:"total_count"`
	OverallAvg float64 `json:"overall_avg"`
	OverallMin int     `json:"overall_min"`
	OverallMax int     `json:"overall_max"`
	MentalAvg  float64 `json:"mental_avg"`
	MentalMin  int     `json:"mental_min"`
	MentalMax  int     `json:"mental_max"`
	PhysicalAvg float64 `json:"physical_avg"`
	PhysicalMin int     `json:"physical_min"`
	PhysicalMax int     `json:"physical_max"`
	EnergyAvg  float64 `json:"energy_avg"`
	EnergyMin  int     `json:"energy_min"`
	EnergyMax  int     `json:"energy_max"`
}

func (c *ConditionLog) Validate() error {
	if c.Overall < 1 || c.Overall > 5 {
		return fmt.Errorf("overall must be between 1 and 5, got %d", c.Overall)
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
	if c.OverallVAS != nil && (*c.OverallVAS < 0 || *c.OverallVAS > 100) {
		return errors.New("overall_vas must be between 0 and 100")
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

func validateOptionalRange(name string, v *int) error {
	if v == nil {
		return nil
	}
	if *v < 1 || *v > 5 {
		return errors.New(name + " must be between 1 and 5")
	}
	return nil
}
