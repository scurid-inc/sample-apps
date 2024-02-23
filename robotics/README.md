# Simulating Robots with Scurid
The codebase contains code associated with ARGoS 3 simulator to simulate robotics scenario. It is one of the numerous example of applications of Scurid under sample-apps repository. 

## Pre-Requisites

### Golang

Building any golang apps requires [Go](https://golang.org/doc/install) to be installed on your machine.
Also, the Scurid Edge agent should be onboarded running on your device, if not please follow the steps [here](https://docs.scurid.com/v23.0.2.1/autonomousDeviceOnboarding/)

#### ARGoS 3
ARGoS3 is a multithreaded physics-based simulator designed to simulate large-scale robot swarms. Benchmark results show that Argos can perform physics-accurate simulations involving thousands of robots in a fraction of real-time.

1. Download ARGoS 3
```
git clone https://github.com/ilpincy/argos3.git argos3
```
2. Download dependencies
```
brew install pkg-config cmake libpng freeimage lua qt
docbook asciidoc graphviz doxygen
```
3.  Build ARGoS 3

```
cd argos3 mkdir build_simulator cd build_simulator cmake ../src make

```

##### Running the simulation
```
argos3 -c robotics/robots.argos

```
