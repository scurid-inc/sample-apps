package main

import (
	edgeApi "bitbucket.org/scurid/edgeagentapis/pkg/grpc/edgeagent/v1"
	"flag"
	"fmt"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"log"
	"os"
)

func main() {

	var agentConfig = flag.String("agentconfig", "", "usage: -agentconfig ./store/config.yaml this is created by the Scurid Edge Agent when it starts up for the first time.")
	var agentURL = flag.String("url", "", "usage: -url localhost:4040 this is the URL of the Scurid Edge Agent.")
	var deviceID = flag.String("did", "", "usage: -did this is the device ID of the device.")
	var path = flag.String("path", "", "usage: -path <path> this is the path of the file to download.")
	var deviceIDName = flag.String("name", "", "usage: -name provide any easy to remember name.")
	// Define the flag
	option := flag.Int("run", 0, "Specify an option:\n1 - Create Identity, ensure to provide a name for the device\n2 - Download Device File, when using this option ensure to provide valid deviceID and path\n3 - Data Egress App, shows how to send data to the Scurid Edge Agent")
	flag.Parse()
	// Display help if no option or invalid usage
	if flag.NFlag() == 0 || *option <= 0 || *option > 2 {
		fmt.Println("Usage:")
		flag.PrintDefaults()
		os.Exit(1)
	}
	// create the client connection to the Scurid Edge Agent
	conn, err := grpc.Dial(*agentURL, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Println("did not connect: ", err)
		return
	}
	cl := edgeApi.NewScuridEdgeAgentAPIClient(conn)
	// Handle options
	switch *option {
	case 1:
		fmt.Println("You selected option 1: Create Identity")
		res, err := CreateAndRegisterDeviceID(cl, *deviceIDName)
		if err != nil {
			log.Println("Error creating device identity: ", err)
			os.Exit(1)
		} else {
			fmt.Println("Device Identity created: ", res)
			fmt.Println("This is your new device device identity, independent of the Scurid Edge Agent: ")
		}
	case 2:
		fmt.Println("You selected option 2: Download Device File")
		res, err := DownloadPkg(cl, *deviceID, *path)
		if err != nil {
			log.Println("Error downloading files: ", err)
			os.Exit(1)
		} else {
			log.Println("Downloaded files: ", res)
			log.Println("Downloaded files download at path: ", *path)
		}
	case 3:
		issDataEgress(cl, *agentConfig)
	default:
		fmt.Println("Invalid option selected. Use -help to see available options.")
		os.Exit(1)

	}
}
