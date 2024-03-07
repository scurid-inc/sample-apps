package main

import (
	"encoding/json"
	"github.com/rs/zerolog/log"
	"io"
	"net/http"
)

const issURL = "http://api.open-notify.org/iss-now.json"

// ISSNowResponse represents the flat response structure from the API.
type ISSNowResponse struct {
	Message   string `json:"message"`
	Timestamp int    `json:"timestamp"`
	Latitude  string `json:"latitude"`
	Longitude string `json:"longitude"`
}

func fetchIssData() (string, error) {
	// ISS current location API endpoint

	// Temporary struct to hold the API response
	var tempResponse struct {
		Message     string `json:"message"`
		Timestamp   int    `json:"timestamp"`
		IssPosition struct {
			Latitude  string `json:"latitude"`
			Longitude string `json:"longitude"`
		} `json:"iss_position"`
	}

	var issData ISSNowResponse
	resp, err := http.Get(issURL)
	if err != nil {

		log.Error().Msgf("Error fetching ISS data: %v", err)
		return "", err
	}
	defer func() {
		if err := resp.Body.Close(); err != nil {
			log.Error().Msgf("Error closing response body: %v", err)
		}
	}()

	// Read the body of the response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Error().Msgf("Error reading response body: %v", err)
		return "", err
	}

	// Unmarshal the JSON data into our temporary struct
	if err := json.Unmarshal(body, &tempResponse); err != nil {
		log.Error().Msgf("Error unmarshalling JSON: %v", err)
		return "", err
	}

	// Transfer data to the flat structure
	issData.Message = tempResponse.Message
	issData.Timestamp = tempResponse.Timestamp
	issData.Latitude = tempResponse.IssPosition.Latitude
	issData.Longitude = tempResponse.IssPosition.Longitude

	// Marshal the flat structure into JSON
	jData, err := json.Marshal(issData)
	if err != nil {
		log.Error().Msgf("Error marshalling JSON: %v", err)
		return "", err
	}
	log.Info().Msgf("The ISS is currently at latitude: %s, longitude: %s\n",
		issData.Latitude, issData.Longitude)

	return string(jData), nil
}
