# TabPy Deployment for Tableau Cloud (AWS)
The goal of this document is to walk through the end-to-end solution building process. While in the document we are using AWS cloud, the architecture and solution can be generalized to any cloud platform. The solution building process comprises three main steps: 

* Running TabPy on EC2 instance
* Request SSL certification with a registered domain 
* Set up an application load balancer with HTTPS

## 1. Running TabPy on EC2 Instance
AWS EC2 instance is employed as a virtual server to host python and run TabPy. The most important point in this part is while we are not going to configure TabPy with HTTPS, it still should be configured with authentication. Below is the walk through process to set-up an EC2 instance and install and configure TabPy. If you already have EC2 instance with TabPy up and run you may skip this section. You can find the official AWS documentation on set up Amazon EC2 [here](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/get-set-up-for-amazon-ec2.html).

## 1.1. EC2 Instance Set-up

From your AWS console go to EC2 and lunch an instance. 
In the Lunch an instance section, select a name and the OS for your instance (ubuntu is recommended) as well as the instance type:

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/1-Create_EC2.png)

Then you have the option to create key pair for your instance. That would be most useful when you want to transfer files from your local machine to your EC2 instance. So it is recommended to create the key with ppk format and store in the safe location:

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/2-EC2_Keypair.png)
![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/3-EC2_Create_Keypair.png)

Next step is to create the security group. To do that click the edit bottom for security group section:

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/4-Network_Setting.png)

Pick a meaningful name and description for the security group and make sure two inbound rules are added: 

* ssh type with port 22 (Assuming the OS for your VM is Linux then we should enable ssh port othewise it should be the port consitent to the OS for example if the OS was Window the we would need to enable RDP)
* Custom TCP type with port 9004. 

Although TabPy by default runs on port 9004 the port number can be configured on the TabPy configuration. If you want to run TabPy with a different port number, make sure you have the corresponding inbound rule a.k.a. Custom TCP with your desirable port number.

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/5-TCP_Setting.png)

In the last part you have the option to increase the storage or number of instance as well. Then go ahead a click ‘Lunch instance’. It may take few mins for AWS to lunch the instance. You can see the list of running instance by going to EC2 dashboard and Instance (running):

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/6-EC2_Running_1.png)

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/7-EC2_Running_2.png)

## 1.2. Install Python and TabPy

To install any software or package you need to connect to your EC2 instance. There are multiple ways to connect to your instance including [ssh connection](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AccessingInstancesLinux.html) (for mac) and [putty](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/putty.html) (for windows) however the most straight forward method is using the AWS UI:

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/8-EC2_Connect.png)

After connecting to the EC2 you need to run the following commands.  

`sudo apt update`

`sudo apt install python3-pip`

`sudo python3 –m pip install —upgrade pip`

`sudo pip3 install tabpy`

This commands basically install the latest version of Python and install TabPy package. If you need any other python package you can install it similarly with pip command:

'sudo pip3 install [your-python-package]'

## 1.3. TabPy Configuration

The next step is to set authentication for TabPy which is mandatory for Tableau Cloud. To do that you may create `.conf` file by stating the location of `.txt` file to store the user names and password (Please note TabPy supports basic authentication.). In the below example the file name is `pass.txt`:

`[TabPy]`

`TABPY_PWD_FILE = pass.txt`

you can find more about TabPy configuration [here](https://github.com/tableau/TabPy/blob/master/docs/server-config.md)

the `pass.txt` file needs to be created and be available on the same server as TabPy server. The next step is add user(s) for TabPy with below command: 

`tabpy-user add -u <username> -p <password> -f <pwdfile>`

 you can find more about TabPy authentication command [here](https://github.com/tableau/TabPy/blob/master/docs/server-config.md#authentication)

At this stage, If we run TabPy from the current terminal then TabPy will be attached to the current terminal. On the other word, as soon as you close your borrower/terminal then TabPy will be shut down. Hence, we need to make sure TabPy is running as a service on background. Depend on the OS of your EC2 instance there are multiple ways to run TabPy at background. For ubuntu one of the most useful application to create sessions at background is [Tmux](https://github.com/tmux/tmux/wiki). Below is the summary of steps to run TabPy at background in ubuntu using Tmux. You can find more comprehensive reference for Tumx [here](https://tmuxcheatsheet.com/). 

* Create a new session: `tmux new-session -s [session_name]`
* Connect to the session: `tmux attach-session -t [session_name]`
* Run TabPy with the custom configuration `tabpy --config [configuration file name.conf]`
* Disconnect from the session `Crtl + b + d`


Now TabPy is up and running on your EC2 instance and you are able to connect Tableau Desktop and Server with host-name as the pubic IP address for EC2 instance and port number as 9004. However, connecting to Tableau Cloud still is not possible as it requires SSL connection which we are going to discuss in the next parts 

# 2. Domain Name Registeration and SSL Certification

Tableau Cloud establishes a connection only with external servers that are configured with a trusted 3rd party certificate authority (CA) and not with a self-signed certificate, a certificate from a private PKI, or a certificate that is not trusted by an established 3rd party CA. Hence, we need to have a valid TLS/SSL certificate from a trusted 3rd party certificate authority (CA) which required having a registered domain. 
Request SSL TLS/SSL can be done with AWS certificate manager however requesting the certificate requires a registered domain. Below is the walk though process to registered a domain (if you do not have one) with AWS Route 53 and request a SSL certificate.You can find AWS official documentation about registering a new domain  [here](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-register.html) and about requesting a public certificate [here](https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-request-public.html).

## 2.1.Register a Domain

A registered domain to host the SSL certification is mandatory. If you already have a register domain you may skip this section otherwise you can register one with AWS Route 53 as follow:
From AWS console go to AWS Route 53 and select a domain name (usually there is a yearly fee associate to the domain)

After submitting the request it may take couple of mins for AW to verify the domain registration. You will get a notification email when the domain is registered successfully. And then you will see it as part of ‘Registered domain“ 

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/9-Domain_Registory.png)

## 2.2. Request SSL Certificate 

The next step is to request the SSL certification via AWS certificate manager. To do that, From AWS console go to AWS Certificate Manager and select request and then submit a request for a public certificate:

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/10-Request%20Certificate.png)

Then you need to pick a valid name for your domain. When you pick the name, make sure you select ‘Add another name to this certificate’ and add *.your-domain as below:

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/11-Public_Certificate.png)

When you submit the request may see the domain request as pending. Go back to AWS certificate manager portal and click on the ‘certification ID’ correspond to the registered domain and select ‘Create records’:

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/12-AWS_DNS_Record.png)

Few mins after creating record the status of certificate will turn into ‘issued’:

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/13-AWD_DNS_Issued.png)

# 3. Application Load Balancer

Application load balancer is used to route the requests to the EC2 instance on which TabPy is running. Below is the walk though process to create an application load balancer and use it as proxy for the TabPy server. You can learn more application load balancer [here](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html).

## 3.1. Create Load Balancer

From AWS console go to EC2 and then scroll down and find “Load Balancers” and create an “application load balancer”

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/14-Application_Load_Balancer.png)

Pick a name for your load balancer and make sure the VPC is the same as VPC for your EC2 instance similar for mappings (you need to pick at least two availability zones):

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/15-APB_Setting.png)


## 3.2.Security Group and Target Group

the best practice is to create a new security group instead of using default ones. To do that remove any default security group and click on ‘create security group’. Pick a name and description for the security group and make sure the VPC is the same VPC that your TabPy EC2 instance is running on. 
for the inbound and outbound rules make sure it is set to ‘HTTPS’ type with port range 443. The outbound type can be ‘All traffic’ 

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/16-APB_Security_Group_Basic.png)

You can learn more about AWS application load balancer security group [here](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-update-security-groups.html).

After creating the security group go back to the load balancer page and select the created security group;

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/17-APB_Security_Group_Setting.png)

Next set up listeners and routing by selecting HTTPS as protocol with port 443 and then select “create a target group” 

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/18-APB_Security_Group_Listener.png)

For the target group set the target type to ‘instance’, pick a name and make sure protocol is HTTP with port 9004 (This is port on which TabPy is running on EC2 instance):

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/19-APB_Security_Group_Config.png)

Finally select the instance on which your are running TabPy and ‘include as pending below“

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/20-APB_Security_Group_Target.png)

After creating the target group go back to your load balancer page and select the created target group (you should see it as part of drop down menu)

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/21-APB_Security_Group_HTTPS.png)

In the last section ‘Secure listen setting’ select your registered domain as :


## 3.2.Route Traffic to Load Balancer

The final step is to route the web traffic to the load balancer. 
From AWS console go to AWS Route 53 dashboard and under ‘DSN management’ select ‘Hosted zones’ and then select the registers domain you created. Then create a record and assign a record name (This would be the host-name for TabPy connection to Tableau Cloud) and make sure rest of the configuration is as below: 

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/22-APB_Security_Group_Final.png)

After creating the record you should have it as pat of:

![alt text](https://github.com/AmirMK/TabPy-Amir/blob/master/docs/img/AWS-Deployment/23-Create_Record_1.png)

It may take couple of mins for record to get effective and working. When the record gets effective you will be able to connect Tableau cloud/Desktop/Server to the TabPy server with secured connection via SSL. To connect to TabPy, your hostname would be the record name, port number is 443:


