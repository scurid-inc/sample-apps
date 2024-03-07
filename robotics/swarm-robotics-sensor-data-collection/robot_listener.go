package main

import (
	"bytes"
	"context"
	"fmt"
	"os/exec"
	"strings"
	"time"

	edgeApi "bitbucket.org/scurid/edgeagentapis/pkg/grpc/edgeagent/v1"
	"github.com/rs/zerolog/log"
)

const ShellToUse = "bash"
const robotID = "fb2"

func Shellout(command string) (string, string, error) {
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd := exec.Command(ShellToUse, "-c", command)
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()
	return stdout.String(), stderr.String(), err
}

// issListener listens to the ISS API and sends data to the server
func issListener(agentid string, agentClient edgeApi.ScuridEdgeAgentAPIClient) {

	for {
		res, stderr, err := Shellout("tail -n3 /Users/roshan/argos3-examples/robot.log | head -1 ")

		if err != nil {
			fmt.Println(fmt.Sprint(err) + ": " + stderr)
			return
		}
		roboData := res
		fmt.Println("Result: " + roboData)
		if err != nil {
			fmt.Println(err.Error())
			return
		}
		if strings.Contains(roboData, robotID) {
			// Print the output
			fmt.Println("Data from robot sensor", string(roboData))
			issRes := string(roboData)
			//issRes, err := fetchIssData()
			if err != nil {
				log.Error().Msgf("Error fetching ISS data: %v", err)
				break
			}
			// calls the Scurid edge agent client to send the data to the Scurid Server
			res, err := agentClient.SendDeviceDataWithCustomFields(context.Background(), &edgeApi.SendDeviceDataWithCustomFieldsReq{
				AgentDID: agentid,
				Data:     []string{issRes},
			})
			if err != nil {
				log.Error().Msgf("issListener failed to send %v", err)
				break
			} else {
				log.Info().Msgf("Sent robot fb1 data to server: %v", res)
			}
			time.Sleep(5 * time.Second)
		}
	}

}
