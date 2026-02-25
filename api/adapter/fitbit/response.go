package fitbit

// ActivityResponse represents /1/user/-/activities/date/{date}.json
type ActivityResponse struct {
	Summary struct {
		Steps             int     `json:"steps"`
		CaloriesOut       int     `json:"caloriesOut"`
		ActiveScore       int     `json:"activeScore"`
		Floors            int     `json:"floors"`
		RestingHeartRate  int     `json:"restingHeartRate"`
		ActiveZoneMinutes int     `json:"activeZoneMinutes"`
		Distances         []struct {
			Activity string  `json:"activity"`
			Distance float64 `json:"distance"`
		} `json:"distances"`
		FairlyActiveMinutes int `json:"fairlyActiveMinutes"`
		LightlyActiveMinutes int `json:"lightlyActiveMinutes"`
		SedentaryMinutes    int `json:"sedentaryMinutes"`
		VeryActiveMinutes   int `json:"veryActiveMinutes"`
		CaloriesBMR         int `json:"caloriesBMR"`
		HeartRateZones      []struct {
			Name    string `json:"name"`
			Minutes int    `json:"minutes"`
		} `json:"heartRateZones"`
	} `json:"summary"`
	Activities []struct {
		LogID              int64   `json:"logId"`
		ActivityName       string  `json:"activityName"`
		StartTime          string  `json:"startTime"`
		Duration           int64   `json:"duration"`
		Calories           int     `json:"calories"`
		AverageHeartRate   int     `json:"averageHeartRate"`
		Distance           float64 `json:"distance"`
		DistanceUnit       string  `json:"distanceUnit"`
		ActiveZoneMinutes  *struct {
			TotalMinutes       int `json:"totalMinutes"`
			ActiveZoneMinutes  []struct {
				MinuteInZone int    `json:"minuteInZone"`
				Type         string `json:"type"`
			} `json:"activeZoneMinutes"`
		} `json:"activeZoneMinutes"`
	} `json:"activities"`
	Goals struct {
		CaloriesOut int     `json:"caloriesOut"`
		Distance    float64 `json:"distance"`
		Steps       int     `json:"steps"`
	} `json:"goals"`
}

// SleepResponse represents /1.2/user/-/sleep/date/{date}.json
type SleepResponse struct {
	Sleep []struct {
		LogID              int64  `json:"logId"`
		DateOfSleep        string `json:"dateOfSleep"`
		StartTime          string `json:"startTime"`
		EndTime            string `json:"endTime"`
		Duration           int64  `json:"duration"`
		MinutesAsleep      int    `json:"minutesAsleep"`
		MinutesAwake       int    `json:"minutesAwake"`
		MinutesAfterWakeup int    `json:"minutesAfterWakeup"`
		TimeInBed          int    `json:"timeInBed"`
		Type               string `json:"type"`
		IsMainSleep        bool   `json:"isMainSleep"`
		Levels             struct {
			Summary struct {
				Deep  *struct{ Minutes int `json:"minutes"` } `json:"deep"`
				Light *struct{ Minutes int `json:"minutes"` } `json:"light"`
				REM   *struct{ Minutes int `json:"minutes"` } `json:"rem"`
				Wake  *struct{ Minutes int `json:"minutes"` } `json:"wake"`
			} `json:"summary"`
			Data []struct {
				DateTime string `json:"dateTime"`
				Level    string `json:"level"`
				Seconds  int    `json:"seconds"`
			} `json:"data"`
		} `json:"levels"`
	} `json:"sleep"`
	Summary struct {
		TotalMinutesAsleep int `json:"totalMinutesAsleep"`
		TotalTimeInBed     int `json:"totalTimeInBed"`
	} `json:"summary"`
}

// HRIntradayResponse represents /1/user/-/activities/heart/date/{date}/1d/1min.json
type HRIntradayResponse struct {
	ActivitiesHeartIntraday struct {
		Dataset []struct {
			Time  string `json:"time"`
			Value int    `json:"value"`
		} `json:"dataset"`
	} `json:"activities-heart-intraday"`
	ActivitiesHeart []struct {
		Value struct {
			RestingHeartRate int `json:"restingHeartRate"`
		} `json:"value"`
	} `json:"activities-heart"`
}

// HRVResponse represents /1/user/-/hrv/date/{date}.json
type HRVResponse struct {
	HRV []struct {
		HRV struct {
			DailyRMSSD float32 `json:"dailyRmssd"`
			DeepRMSSD  float32 `json:"deepRmssd"`
		} `json:"value"`
	} `json:"hrv"`
}

// SpO2Response represents /1/user/-/spo2/date/{date}.json
type SpO2Response struct {
	Value struct {
		Avg float32 `json:"avg"`
		Min float32 `json:"min"`
		Max float32 `json:"max"`
	} `json:"value"`
}

// BreathingRateResponse represents /1/user/-/br/date/{date}/all.json
type BreathingRateResponse struct {
	BR []struct {
		Value struct {
			BreathingRate float32 `json:"breathingRate"`
			FullSleepSummary struct {
				BreathingRate float32 `json:"breathingRate"`
			} `json:"fullSleepSummary"`
			DeepSleepSummary struct {
				BreathingRate float32 `json:"breathingRate"`
			} `json:"deepSleepSummary"`
			LightSleepSummary struct {
				BreathingRate float32 `json:"breathingRate"`
			} `json:"lightSleepSummary"`
			RemSleepSummary struct {
				BreathingRate float32 `json:"breathingRate"`
			} `json:"remSleepSummary"`
		} `json:"value"`
	} `json:"br"`
}

// SkinTempResponse represents /1/user/-/temp/skin/date/{date}.json
type SkinTempResponse struct {
	TempSkin []struct {
		Value struct {
			NightlyRelative float32 `json:"nightlyRelative"`
		} `json:"value"`
	} `json:"tempSkin"`
}

// CardioScoreResponse represents /1/user/-/cardioscore/date/{date}.json
type CardioScoreResponse struct {
	CardioScore []struct {
		Value struct {
			VO2Max string `json:"vo2Max"`
		} `json:"value"`
	} `json:"cardioScore"`
}
