package handler

import "time"

var jst = time.FixedZone("JST", 9*3600)

// parseDate parses "YYYY-MM-DD" as midnight in JST.
func parseDate(s string) (time.Time, error) {
	return time.ParseInLocation("2006-01-02", s, jst)
}
