package entity

import (
	"errors"
	"fmt"
	"time"
)

type ConditionLog struct {
	ID        int64
	LoggedAt  time.Time
	Overall   int
	Mental    *int
	Physical  *int
	Energy    *int
	Note      string
	Tags      []string
	CreatedAt time.Time
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
