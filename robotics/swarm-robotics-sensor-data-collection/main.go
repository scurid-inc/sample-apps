package main

import (
	edgeApi "bitbucket.org/scurid/edgeagentapis/pkg/grpc/edgeagent/v1"
	"flag"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

func main() {
	zerolog.SetGlobalLevel(zerolog.InfoLevel)
	var agentConfig = flag.String("agentconfig", "", "usage: -agentconfig ./store/config.yaml this is created by the Scurid Edge Agent when it starts up for the first time.")
	var agentURL = flag.String("url", "", "usage: -url localhost:4040 this is the URL of the Scurid Edge Agent.")

	flag.Parse()
	// dial the connection to the Scurid Edge Agent running on the device
	conn, err := grpc.Dial(*agentURL, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Error().Msgf("did not connect: %v", err)
		return
	}
	cl := edgeApi.NewScuridEdgeAgentAPIClient(conn)

	issDataEgress(cl, *agentConfig)
}
