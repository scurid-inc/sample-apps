package main

import (
	edgeApi "bitbucket.org/scurid/edgeagentapis/pkg/grpc/edgeagent/v1"
	"context"
	"log"
)

func DownloadPkg(client edgeApi.ScuridEdgeAgentAPIClient, deviceID, path string) (*edgeApi.DownloadFilesRes, error) {
	res, err := client.DownloadFiles(context.Background(), &edgeApi.DownloadFilesReq{Identity: deviceID, Path: path})
	if err != nil {
		log.Println("Error downloading files: ", err)
		return nil, err
	} else {
		return res, nil
	}
}
