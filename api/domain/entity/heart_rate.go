package entity

import "time"

type HeartRateSample struct {
	Time       time.Time
	BPM        int
	Confidence int
}
