package main

import (
	edgeApi "bitbucket.org/scurid/edgeagentapis/pkg/grpc/edgeagent/v1"
	"context"
	"github.com/rs/zerolog/log"
	"time"
)

// issListener listens to the ISS API and sends data to the server
func issListener(agentid string, agentClient edgeApi.ScuridEdgeAgentAPIClient) {

	for {
		issRes, err := fetchIssData()
		if err != nil {
			log.Error().Msgf("Error fetching ISS data: %v", err)
			break
		}
		// calls the agent client to send the data to the Scurid Edge Agent
		res, err := agentClient.SendDeviceDataWithCustomFields(context.Background(), &edgeApi.SendDeviceDataWithCustomFieldsReq{
			AgentDID: agentid,
			Data:     []string{issRes},
		})
		if err != nil {
			log.Error().Msgf("issListener failed to send %v", err)
			break
		} else {
			log.Info().Msgf("Sent ISS data to server: %v", res)
		}

		time.Sleep(5 * time.Second)
	}

}
