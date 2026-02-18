package entity

import "time"

type DailyAdvice struct {
	Date         time.Time `json:"Date"`
	AdviceText   string    `json:"AdviceText"`
	ModelName    string    `json:"ModelName"`
	GenerationMs *int      `json:"GenerationMs"`
	Cached       bool      `json:"Cached"`
	GeneratedAt  time.Time `json:"GeneratedAt"`
}
