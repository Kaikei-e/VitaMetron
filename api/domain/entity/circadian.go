package entity

import (
	"encoding/json"
	"time"
)

type CircadianScore struct {
	Date                    time.Time       `json:"Date"`
	CHSScore                float32         `json:"CHSScore"`
	CHSConfidence           float32         `json:"CHSConfidence"`
	CosinorMesor            *float32        `json:"CosinorMesor"`
	CosinorAmplitude        *float32        `json:"CosinorAmplitude"`
	CosinorAcrophaseHour    *float32        `json:"CosinorAcrophaseHour"`
	NPARIS                  *float32        `json:"NPARIS"`
	NPARIV                  *float32        `json:"NPARIV"`
	NPARRA                  *float32        `json:"NPARRA"`
	NPARM10                 *float32        `json:"NPARM10"`
	NPARM10Start            *float32        `json:"NPARM10Start"`
	NPARL5                  *float32        `json:"NPARL5"`
	NPARL5Start             *float32        `json:"NPARL5Start"`
	SleepMidpointHour       *float32        `json:"SleepMidpointHour"`
	SleepMidpointVarMin     *float32        `json:"SleepMidpointVarMin"`
	SocialJetlagMin         *float32        `json:"SocialJetlagMin"`
	NocturnalDipPct         *float32        `json:"NocturnalDipPct"`
	DaytimeMeanHR           *float32        `json:"DaytimeMeanHR"`
	NighttimeMeanHR         *float32        `json:"NighttimeMeanHR"`
	ZRhythmStrength         *float32        `json:"ZRhythmStrength"`
	ZRhythmStability        *float32        `json:"ZRhythmStability"`
	ZRhythmFragmentation    *float32        `json:"ZRhythmFragmentation"`
	ZSleepRegularity        *float32        `json:"ZSleepRegularity"`
	ZPhaseAlignment         *float32        `json:"ZPhaseAlignment"`
	SRIValue                *float32        `json:"SRIValue"`
	BaselineWindowDays      int             `json:"BaselineWindowDays"`
	BaselineMaturity        string          `json:"BaselineMaturity"`
	ContributingFactors     json.RawMessage `json:"ContributingFactors"`
	MetricsIncluded         []string        `json:"MetricsIncluded"`
	ComputedAt              time.Time       `json:"ComputedAt"`
}
