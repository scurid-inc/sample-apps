package main

import (
	edgeApi "bitbucket.org/scurid/edgeagentapis/pkg/grpc/edgeagent/v1"
	"context"
	"log"
	"time"
)

func CreateAndRegisterDeviceID(client edgeApi.ScuridEdgeAgentAPIClient, name string) (*edgeApi.CreateDeviceIdentityRes, error) {
	res, err := client.CreateDeviceIdentity(context.Background(), &edgeApi.CreateDeviceIdentityReq{})
	if err != nil {
		log.Print("Error creating device identity: ", err)
		return nil, err
	} else {
		reqRes, err := client.RegisterDeviceIdentity(context.Background(), &edgeApi.RegisterDeviceIdentityReq{
			Did:        res.GetDid(),
			UnixTime:   time.Now().Unix(),
			DeviceName: name,
		})
		if err != nil {
			log.Print("Error registering device identity: ", err)
			return nil, err
		} else {
			log.Print("Device ID registered: ", reqRes.GetResult())
		}
		return res, nil
	}
}
