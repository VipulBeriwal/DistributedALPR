#!/usr/bin/env python
import zmq, threading, thread
from controller_utils import StoppableThread, ClientConnectRule

class ManageClients(StoppableThread):
	def __init__(self, config):
		StoppableThread.__init__(self)
		self.thread = threading.Thread(name="Listen_client_requests", target=self.run, args=(config,))
		self.thread.start()

	def run(self, config):
		while self.stop_event.is_set()==False:
			self._scan(config)

	def _scan(self, config):
		client, empty, msg, ID = config.client_control.recv_multipart()
		print("Client: "+msg+ID)
		#Ensure the 'connect' request is from a new client
		if msg == "CONNECT!" and ID=="0":
			'''
			- find_server is a list that is sorted as per the rule specified
			- rule 0 is the default rule which does load balancing based on number of clients connected to each server
			'''
			find_server = ClientConnectRule.connect_rule(config,0)

			if find_server:
				#print("came inside find_server")
				print(find_server)
				if not config.client_list:
					clientID = "100000"
					#print("assigned 1st client ID")
				else:
					clientID = str(int(config.client_list[-1]) + 1)

				err_count = 0
				for server in find_server:
					print("Controller: Connecting to "+config.serv_meta[server][0]+":"+config.serv_meta[server][1])
					config.command.connect("tcp://"+config.serv_meta[server][0]+":"+config.serv_meta[server][1])
					config.command.send("CONNECT!"+clientID)
					reply = config.command.recv()


					#for reliable working of REQ-REP
					config.command.disconnect("tcp://"+config.serv_meta[server][0]+":"+config.serv_meta[server][1])

					#reply consists of server's pull-port
					print("Server "+server+": "+reply)
					if(reply[:4]=="200!"):
						config.client_list.append(clientID)
						config.serv_meta[server].append(clientID)
						config.serv_load[server] += 1
						data_port = reply[4:8]
						print("Controller: Sending reply 200!"+clientID+config.serv_meta[server][0]+":"+data_port)

						#reply_msg = "200!"+clientID+config.serv_meta[server][0]+":"+data_port

						#200 - SUCCESS
						config.client_control.send_multipart([client, "", "200!", clientID, config.serv_meta[server][0], data_port])
						print(config.client_list)
						break
					elif reply[:4]=="503!":
						err_count += 1

					elif reply[:4]=="400!":
						config.client_control.send_multipart([client, "", "400!","","",""])
				
				#503 - Service Unavailable, connection limit reached
				if err_count==len(find_server):
					config.client_control.send_multipart([client, "", "503!","","",""])

			else:
				print("Controller: No server joined")
				config.client_control.send_multipart([client, "", "503!","","",""])

		#Ensure the 'disconnect' request is from a valid client
		elif msg == "DISCONNECT!" and ID!="0":
			clientID = ID
			for servID in config.serv_meta:
				#check for client id in servID key of serv_meta dictionary
				if clientID in config.serv_meta[servID]:
					config.command.connect("tcp://"+config.serv_meta[servID][0]+":"+config.serv_meta[servID][1])
					config.command.send("DISCONNECT!"+clientID)
					reply = config.command.recv()

					#for reliable working of REQ-REP
					config.command.disconnect("tcp://"+config.serv_meta[servID][0]+":"+config.serv_meta[servID][1])

					if(reply=="200!"):
						config.serv_meta[servID].remove(clientID)
						config.serv_load[servID] -= 1
						#print(config.serv_meta)
						#print(config.serv_load)

						config.client_list.remove(clientID)
						config.client_control.send_multipart([client, "", "200!"])
						print("Controller: Disconnected client "+clientID)
						break

					else:
						config.client_control.send_multipart([client, "", "400!"])
						print("Controller: ERROR while disconnecting "+clientID)

		#400 - Bad request
		else:
			config.client_control.send_multipart([client, "", "400!"])