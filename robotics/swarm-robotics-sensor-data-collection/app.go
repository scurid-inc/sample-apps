package main

import (
	edgeApi "bitbucket.org/scurid/edgeagentapis/pkg/grpc/edgeagent/v1"
	"github.com/rs/zerolog/log"
	"gopkg.in/yaml.v3"
	"os"
	sampleApps "scurid-inc/sample-apps"
	"time"
)

var regRequest sampleApps.ReqRequest

// issDataEgress is a wrapper used for sending the data to the Scurid Edge Agent which will then send it to the server
// Scurid Edge Agent will handle the authentication and authorization of the data also generates the signature on the raw data being sent to the server.
func issDataEgress(client edgeApi.ScuridEdgeAgentAPIClient, filename string) {

	regRequest.RequestedOn = time.Now().Unix()
retry1:

	log.Info().Msgf("reading agent config file %s", filename)
	agentConf := readAgentConfig(filename)
	// checks if there is agent identity
	if agentConf.ApprovalKey == "" {
		log.Info().Msg("Agent is not registered, will retry in 5 seconds ...")
		time.Sleep(5 * time.Second)
		goto retry1
	}
	// if there is an approval key then it is likely valid and approved, if not issListener will print out the error message
	issListener(agentConf.AgentDID, client)

}

// readAgentConfig reads the Edge agent configuration and extracts required information that is needed for this app to interact with the agent.
func readAgentConfig(filename string) *sampleApps.AgentInfo {
	var config sampleApps.AgentInfo
	// get the config file name
	b, err := os.ReadFile(filename)
	if err != nil {

		return &config
	}
	if err := yaml.Unmarshal(b, &config); err != nil {
		log.Error().Msg(err.Error())
		return &config
	}
	return &config
}
