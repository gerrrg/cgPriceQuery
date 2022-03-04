# getHistoricalPrices.py
import os
import requests
import json

import datetime
from pathlib import Path

# timeout
import signal
import time

from alive_progress import alive_bar
import numpy as np
import matplotlib.pyplot as plt

class timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)
    def __exit__(self, type, value, traceback):
        signal.alarm(0)

class historicalQuery():
	cgLastCallTime = 0;
	cgCallRateMax = 50.0/60.0; 			#hz
	cgCallPeriodMin = 1/cgCallRateMax; 	#sec
	cgTimeoutSeconds = 10; 				#sec
	secondsPerHour = 60*60;

	networkToCoinGeckoConverters = {
									"ethereum":"ethereum",
									"mainnet":"ethereum",
									"polygon":"polygon-pos",
									"arbitrum":"arbitrum-one",
									"fantom":"fantom",
									};

	knownStablecoins = [
					"0x6b175474e89094c44da98b954eedeac495271d0f", #DAI, Ethereum
					];

	def __init__(self, networkTokens, startTime=0, endTime=9999999999, minDurationBetweenPricesHours=2.5, minDurationBetweenPricesHoursStablecoin=25, cachePath="./cache", verbose=False):
		self.networkTokens = networkTokens;
		self.cachePath = cachePath;
		self.verbose = verbose;
		self.startTime = startTime;
		self.endTime = endTime;
		if self.endTime == -1:
			if self.verbose:
				print("Running in current price mode!")
			return(None)
		self.minDurationBetweenPricesHours = minDurationBetweenPricesHours;							# hr
		self.minDurationBetweenPricesHoursStablecoin = minDurationBetweenPricesHoursStablecoin; 	# hr

		# create prices dict based on network, token contract. fill w/ cache data.
		self.pricesByNetworkToken = {};
		for network in self.networkTokens:
			self.pricesByNetworkToken[network] = {};
			for token in self.networkTokens[network]:
				self.pricesByNetworkToken[network][token] = {};
		self.initializeFromCaches();

		# get maximum price history from coingecko
		self.getSparseHistories();

		# query all time periods between already cached data to get more dense data 
		self.getDenseHistories();

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

	def initializeFromCaches(self):
		for network in self.networkTokens:
			for token in self.networkTokens[network]:
				cachedData = self.loadFromCache(network, token);
				if not cachedData is None:
					self.pricesByNetworkToken[network][token] = cachedData;

	def loadFromCache(self, network, token):
		cacheFile = os.path.join(self.cachePath, network, token + ".json");
		if os.path.isfile(cacheFile):
			if self.verbose:
				print("Reading from", cacheFile);
			stampsAsStrings = self.readFromJson(cacheFile);
			stampsAsInts = {int(d):stampsAsStrings[d] for d in stampsAsStrings.keys()};
			return(stampsAsInts);
		return(None);

	def saveToCache(self, network, token):
		Path(os.path.join(self.cachePath,network)).mkdir(parents=True, exist_ok=True)
		cacheFile = os.path.join(self.cachePath, network, token + ".json");
		data = self.pricesByNetworkToken[network][token];
		self.writeToJson(data, cacheFile);

	def getSparseHistory(self, network, token):
		cgNetworkString = self.networkToCoinGeckoConverters[network];
		historicalDataSparseUrl = 'https://api.coingecko.com/api/v3/coins/{}/contract/{}/market_chart/?vs_currency=usd&days=max'.format(cgNetworkString, token);
		data = self.callCoinGecko(historicalDataSparseUrl);
		if data is None:
			return(None);
		historicalData = {int(d[0]/1000):d[1] for d in data};
		if self.verbose:
			print(historicalData);
		return(historicalData);

	def getSparseHistories(self):
		for network in self.networkTokens:
			for token in self.networkTokens[network]:
				if self.verbose:
					print("\nQuerying sparse history");
					print("\tNetwork:", network);
					print("\tToken:\t", token);
				sparseData = self.getSparseHistory(network, token);
				if sparseData is None:
					continue;

				# find the new timestamps from coingecko that aren't already cached
				cachedTimestamps = self.pricesByNetworkToken[network][token].keys();
				cgTimestamps = sparseData.keys();
				newTimestamps = list(set(cgTimestamps) - set(cachedTimestamps));

				# add the new data to the dict
				newData = {key: sparseData[key] for key in newTimestamps};
				if self.verbose:
					print("New data from CoinGecko:")
					print(json.dumps(newData, indent=4))
				self.pricesByNetworkToken[network][token].update(newData);
				self.saveToCache(network, token);

	def getDenseHistory(self, network, token):
		cgNetworkString = self.networkToCoinGeckoConverters[network];
		minDurationHours = self.minDurationBetweenPricesHours;
		if token in self.knownStablecoins:
			minDurationHours = self.minDurationBetweenPricesHoursStablecoin;

		times = list(self.pricesByNetworkToken[network][token].keys());
		times.sort();

		if self.verbose:
			print("\nQuerying dense history");
			print("\tNetwork:", network);
			print("\tToken:\t", token);

		with alive_bar(len(times)) as bar:
			for i in range(len(times) - 1):
				t1 = times[i];
				t2 = times[i + 1];
				timeGap = t2 - t1;

				# skip times that weren't requested
				if t2 < self.startTime:
					bar();
					continue;
				if t1 > self.endTime:
					return();

				if self.verbose:
					print();
					print("--------------------------------");
					print("Time between last two data points:", float(timeGap)/self.secondsPerHour, "hours")
				if timeGap > minDurationHours * self.secondsPerHour:
					rangeDataUrl = 'https://api.coingecko.com/api/v3/coins/{}/contract/{}/market_chart/range?vs_currency=usd&from={}&to={}'.format(cgNetworkString, token, t1, t2);
					data = self.callCoinGecko(rangeDataUrl);
					if not data is None:
						newData = {int(d[0]/1000):d[1] for d in data};

					self.pricesByNetworkToken[network][token].update(newData);
					self.saveToCache(network, token);
				bar();

	def getDenseHistories(self):
		for network in self.networkTokens:
			for token in self.networkTokens[network]:
				self.getDenseHistory(network, token);

	def getCurrentPrice(self, network, token):
		cgNetworkString = self.networkToCoinGeckoConverters[network];
		priceUrl = "https://api.coingecko.com/api/v3/simple/token_price/{network}?contract_addresses={token}&vs_currencies=usd".format(network=cgNetworkString, token=token)
		data = self.callCoinGecko(priceUrl);
		newData = None;
		if not data is None:
			price = data[list(data.keys())[0]]
		return(price["usd"]);

	def callCoinGecko(self, url, maxRetries=5):
		data=None;
		retries = 0;
		while data is None and retries < maxRetries:
			try:
				with timeout(seconds=self.cgTimeoutSeconds):
					if (time.time() - self.cgLastCallTime) < self.cgCallPeriodMin:
						time.sleep(self.cgCallPeriodMin - (time.time() - self.cgLastCallTime));
					if self.verbose:
						print("Calling", url);
					r = requests.get(url);
					if self.verbose:
						print(r);
					if r.status_code == 200:
						try:
							data = r.json()["prices"];
							if self.verbose:
								print(data);
						except KeyError:
							return(r.json())
					else:
						if self.verbose:
							print("Call Failed! Status code:", r.status_code);
					self.cgLastCallTime = time.time();
			except (TimeoutError, requests.exceptions.ReadTimeout) as e:
				print("Query timed out, attempting to continue with cached data...");
			except json.decoder.JSONDecodeError:
				print("Bad or no return from CG, attempting to continue with cached data...");
			retries += 1;
		return(data);

	def getPriceDataNumpy(self, network, token):
		data = self.pricesByNetworkToken[network][token.lower()];

		stamps = list(data.keys());
		stamps.sort();

		prices = [float(data[stamp]) for stamp in stamps];
		stamps = [int(stamp) for stamp in stamps];

		npStamps = np.array(stamps);
		npPrices = np.array(prices);

		return(npStamps, npPrices);

def main():
	networkTokens = {
		# "polygon":["0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270",
		# 			"0x85955046df4668e1dd369d2de9f3aeb98dd2a369",
		# 			"0x580a84c73811e1839f75d86d75d88cca0c241ff4"],
		"ethereum":[
					"0xaa6e8127831c9de45ae56bb1b0d4d4da6e5665bd",
					"0x6b175474e89094c44da98b954eedeac495271d0f"
					]
				}
	hq = historicalQuery(networkTokens, minDurationBetweenPricesHours=2.5, verbose=False);

	for network in networkTokens:
		for token in networkTokens[network]:

			(npStamps, npPrices) = hq.getPriceDataNumpy(network,token)
			plt.plot(npStamps, npPrices)
			plt.title(token)
			plt.show()

if __name__ == '__main__':
	main()
