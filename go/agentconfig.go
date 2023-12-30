package _go

// AgentInfo used for setting up agent info on the device
type AgentInfo struct {
	AgentDID           string              `yaml:"DID,omitempty"`
	ApprovalKey        string              `yaml:"ApprovalKey,omitempty"`
	IntegrationDetails *IntegrationDetails `yaml:"IntegrationDetails"`
}

type IntegrationDetails struct {
	HawkbitTargetSecretKey   string             `yaml:"HawkbitTargetSecretKey"`
	AppKeyForThingWorxDevice string             `yaml:"AppKeyForThingWorxDevice,omitempty"`
	IntegrationStatus        *IntegrationStatus `yaml:"IntegrationStatus,omitempty"`
	CsrCustom                *CsrCustom         `yaml:"CsrCustom,omitempty"`
}
type IntegrationStatus struct {
	ThingWorxEnabled bool `yaml:"ThingWorxEnabled,omitempty"`
	HawkbitEnabled   bool `yaml:"HawkbitEnabled,omitempty"`
	AzureEnabled     bool `yaml:"AzureEnabled,omitempty"`
}

type CsrCustom struct {
	CommonName         string `yaml:"CommonName"`
	Country            string `yaml:"Country"`
	Province           string `yaml:"Province"`
	Locality           string `yaml:"Locality"`
	Organization       string `yaml:"Organization"`
	OrganizationalUnit string `yaml:"OrganizationalUnit"`
	LifeTimeDays       int32  `yaml:"LifeTimeDays"`
	EmailAddress       string `yaml:"EmailAddress"`
}
type ReqRequest struct {
	DeviceDID   string `json:"deviceDID"`
	RequestedOn int64  `json:"requestedOn"`
	VInfo       string `json:"vInfo"`
	Device_name string `json:"device_name"`
}
