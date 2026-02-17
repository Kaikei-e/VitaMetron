package entity

import "time"

type WeeklyInsight struct {
	WeekStart   time.Time `json:"WeekStart"`
	WeekEnd     time.Time `json:"WeekEnd"`
	AvgScore    *float64  `json:"AvgScore"`
	Trend       string    `json:"Trend"`
	TopFactors  []string  `json:"TopFactors"`
	RiskSummary []string  `json:"RiskSummary"`
}
