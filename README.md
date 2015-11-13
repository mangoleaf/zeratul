# Zeratul

## Using vagrant to setup a VM

Create the following directory structure:
* Create a top level directory for the project (Named /project/ in this example)
* Clone the repo into a folder named zeratul within the project folder. /project/zeratul/
* Copy the contents of /project/zeratul/vagrant/ to /project/

The following should be your directory structure when you are finished.

* /project/
  * VagrantFile
  * provisioning/
  * zeratul/

Finally, execute the command to setup the vm
$ vagrant up

When finished the website will be viewable at http://192.168.37.1:8080
The nginx server on the vm also listens for local.zeratul.com:8080
add an entry to your /etc/hosts file if you wish to use this hostname 
