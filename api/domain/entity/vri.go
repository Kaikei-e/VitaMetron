package entity

import (
	"encoding/json"
	"time"
)

type VRIScore struct {
	Date                time.Time       `json:"Date"`
	VRIScore            float32         `json:"VRIScore"`
	VRIConfidence       float32         `json:"VRIConfidence"`
	ZLnRMSSD            *float32        `json:"ZLnRMSSD"`
	ZRestingHR          *float32        `json:"ZRestingHR"`
	ZSleepDuration      *float32        `json:"ZSleepDuration"`
	ZSRI                *float32        `json:"ZSRI"`
	ZSpO2               *float32        `json:"ZSpO2"`
	ZDeepSleep          *float32        `json:"ZDeepSleep"`
	ZBR                 *float32        `json:"ZBR"`
	SRIValue            *float32        `json:"SRIValue"`
	SRIDaysUsed         int             `json:"SRIDaysUsed"`
	BaselineWindowDays  int             `json:"BaselineWindowDays"`
	BaselineMaturity    string          `json:"BaselineMaturity"`
	ContributingFactors json.RawMessage `json:"ContributingFactors"`
	MetricsIncluded     []string        `json:"MetricsIncluded"`
	ComputedAt          time.Time       `json:"ComputedAt"`
}
