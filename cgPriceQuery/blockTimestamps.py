import os
import json
from alive_progress import alive_bar
import numpy as np
from pathlib import Path

# thegraph queries
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

class blockQuery():
	networkUrl = {
		"ethereum":"https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks",
		"mainnet":"https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks",
		"polygon":"https://api.thegraph.com/subgraphs/name/sameepsi/maticblocks",
		"arbitrum":"https://api.thegraph.com/subgraphs/name/ianlapham/arbitrum-one-blocks",
		"fantom":"https://api.thegraph.com/subgraphs/name/matthewlilley/fantom-blocks"
	}

	def __init__(self, network="ethereum", cachePath="./cache", verbose=False, forceReload=False):
		self.cachePath = cachePath;
		self.verbose = verbose;
		self.network = network;

		self.blockData = {};
		if not forceReload:
			self.initializeFromCache();

		self.url = self.networkUrl[network];
		self.client = None;
		self.initializeGraph(self.url);

	def initializeGraph(self, url):
		transport=RequestsHTTPTransport(
		    url=url,
		    verify=True,
		    retries=3
		)
		self.client = Client(transport=transport)

	def getBlockTimestampQuery(self, first, startTime, endTime, maxRetries=10):
		if self.verbose:
			print("Querying", startTime, "to", endTime);

		query = '''
			query {{
				blocks(first: {first}, orderBy: timestamp, orderDirection: asc, where: {{timestamp_gt: "{startTime}", timestamp_lt: "{endTime}"}}) {{
			    number
			    timestamp
			  }}
			}}
			'''
		retries = 0;
		while retries < maxRetries:
			try:
				formattedQuery = query.format(first=first, startTime=startTime, endTime=endTime);
				response = self.client.execute(gql(formattedQuery));
				return(response);
			except KeyboardInterrupt:
				print("Caught Ctrl+C! Quitting...")
				quit();
			except:
				print("Subgraph call failed on attempt", retries + 1, "of", maxRetries);
				retries += 1;
		print("Failed to get data from subgraph. Please try again! Quitting...");
		quit();

	# json read/write
	def readFromJson(self, filename):
		try:
			with open(filename) as json_file:
				data = json.load(json_file);
				return(data);
		except json.decoder.JSONDecodeError:
			print("Unable to read", filename);
			return({})

	def writeToJson(self, data, filename):
		with open(filename, 'w') as f:
			finished = False;
			caughtSig = False;
			while not finished:
				try:
					json.dump(data, f, indent=4);
					finished = True;
				except KeyboardInterrupt:
					print("Will quit once file is saved to", path);
					caughtSig = True;
			if caughtSig:
				quit();

	def initializeFromCache(self):
		cachedData = self.loadFromCache();
		if not cachedData is None:
			self.blockData = cachedData;

	def loadFromCache(self):
		cacheFile = os.path.join(self.cachePath, self.network, "blocks.json");
		if os.path.isfile(cacheFile):
			if self.verbose:
				print("Reading from", cacheFile);
			data = self.readFromJson(cacheFile);
			return(data);
		return(None);
	
	def saveToCache(self):
		done = False;
		quitWhenDone = False;
		while not done:
			try:
				cacheFile = os.path.join(self.cachePath, self.network, "blocks.json");
				Path(os.path.join(self.cachePath,self.network)).mkdir(parents=True, exist_ok=True);
				self.writeToJson(self.blockData, cacheFile);
				done = True;
			except KeyboardInterrupt:
				print("Caught Ctrl+C! Will quit when done writing to cache")
				quitWhenDone = True;
		if quitWhenDone:
			quit();

	def queryData(self, startTime, endTime, bufferTime=300):
		if startTime > endTime:
			print("Your start time is after your end time! Flip them?")
			print("Start:\t", startTime)
			print("End:  \t", endTime)
			quit();

		if self.verbose:
			print("\nQuerying", self.network, "block times from", startTime, "to", endTime)
		endTimeRetrieved = startTime - bufferTime;
		endTimeGoal = endTime + bufferTime
		lastStartTime = endTimeRetrieved;
		lastBlockRetrieved = None;
		lastTimeRetrieved = 0;

		with alive_bar(endTime - startTime) as bar:
			while endTimeRetrieved < endTime:
				
				# handle pre-cached data, skip over until you hit something new
				doubleBreak = False;
				if not lastBlockRetrieved is None:
					cacheCounter = 0;
					while str(lastBlockRetrieved) in self.blockData.keys():
						lastTimeRetrieved = int(self.blockData[str(lastBlockRetrieved)]);
						endTimeRetrieved = lastTimeRetrieved; #maybe?
						# print("Block", lastBlockRetrieved, "is cached!")
						cacheCounter += 1;

						t1 = int(self.blockData[str(lastBlockRetrieved)])
						t0 = int(self.blockData[str(lastBlockRetrieved - 1)])
						
						lastBlockRetrieved += 1;
						bar(t1-t0);

						if lastTimeRetrieved >= endTimeGoal:
							doubleBreak = True;
							break;
					if self.verbose:
						print("Skipped", cacheCounter, "cached values!")
				if doubleBreak:
					break;

				if self.verbose:
					print("Querying between", endTimeRetrieved, "and", endTimeGoal);
				data = self.getBlockTimestampQuery(first=1000, startTime = endTimeRetrieved, endTime=endTimeGoal);
				if len(data["blocks"]) == 0:
					bar();
					break;

				# stampToBlockNumber = {entry["timestamp"]:entry["number"] for entry in data["blocks"]};
				blockNumberToStamp = {entry["number"]:entry["timestamp"] for entry in data["blocks"]};
				lastBlockRetrieved = int(max(list(blockNumberToStamp.keys())));

				self.blockData.update(blockNumberToStamp);
				self.saveToCache();

				lastStartTime = endTimeRetrieved;
				endTimeRetrieved = int(max(list(blockNumberToStamp.values())))
				bar(endTimeRetrieved - lastStartTime);

	def getNumpyData(self):
		blocks = list(self.blockData.keys())
		blocks.sort;

		blockInts = [int(block) for block in blocks];
		timestampInts = [int(self.blockData[block]) for block in blocks];

		npBlocks = np.array(blockInts)
		npStamps = np.array(timestampInts)

		return(npStamps, npBlocks);

def main():
	# network = "ethereum";
	# bq = blockQuery(network, verbose=False);
	# bq.queryData(startTime = 1609459200, endTime = 1638317800)

	network = "fantom";
	bq = blockQuery(network, verbose=False);
	bq.queryData(startTime = 1638316800, endTime = 1640995200)

if __name__ == '__main__':
	main()