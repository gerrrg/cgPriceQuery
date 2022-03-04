# priceQuery.py
from cgPriceQuery.historicalPriceQuery import historicalQuery
from cgPriceQuery.blockTimestamps import blockQuery
import numpy as np

class priceQuery():
	networks = [
		"ethereum",
		"polygon",
		"arbitrum",
		"fantom",
		];

	def __init__(self, timeBufferSeconds=46800, verbose=False):
		self.verbose = verbose;
		self.timeBufferSeconds = timeBufferSeconds; #default=13h

	def queryPriceAtTime(self, network, token, time):
		if network not in self.networks:
			print("Network", network, "not supported!");
			return(None);

		networkTokens = {network:[token.lower()]};
		startTime = time - self.timeBufferSeconds;
		endTime = time + self.timeBufferSeconds;

		if self.verbose:
			print("Time requested:\t", time);
			print("Time buffer:   \t", self.timeBufferSeconds);
			print("Start Time:    \t", startTime);
			print("End Time:      \t", endTime);
		
		hq = historicalQuery(networkTokens, startTime=startTime, endTime=endTime, minDurationBetweenPricesHours=2.5, verbose=self.verbose);
		(npStamps, npPrices) = hq.getPriceDataNumpy(network, token);
		# if np.amin(npStamps) > startTime:
			# startTime = np.amin(npStamps);
		priceAtTime = np.interp(np.array([time]), npStamps, npPrices);
		return({time:priceAtTime[0]});

	def queryPricesInDuration(self, network, token, timeStart, timeEnd):
		networkTokens = {network:[token.lower()]};
		hq = historicalQuery(networkTokens, startTime=timeStart, endTime=timeEnd, verbose=self.verbose);
		bq = blockQuery(network, verbose=self.verbose);
		bq.queryData(startTime=timeStart, endTime=timeEnd);
		(blockStamps, blockNumbers) = bq.getNumpyData();

		earliestStartTime = 0;
		tokenPrices = [];

		(npStamps, npPrices) = hq.getPriceDataNumpy(network, token);
		if np.amin(npStamps) > earliestStartTime:
			earliestStartTime = np.amin(npStamps);
		pricesAtBlockTime = np.interp(blockStamps, npStamps, npPrices);

		# crop datasets to only include timeframes that have data for all assets, blocks
		earliestStartTime = max(earliestStartTime, timeStart);
		idxsWithAllDataFront = np.argwhere(blockStamps > earliestStartTime);
		idxsWithAllDataBack = np.argwhere(blockStamps < timeEnd);
		idxsWithAllData = np.intersect1d(idxsWithAllDataFront, idxsWithAllDataBack);

		blockStamps = blockStamps[idxsWithAllData];
		blockNumbers = blockNumbers[idxsWithAllData];
		pricesAtBlockTime = pricesAtBlockTime[idxsWithAllData];

		# print(pricesAtBlockTime)
		outputPrices = [el for el in pricesAtBlockTime.tolist()]
		outputStamps = [el for el in blockStamps.tolist()]

		output = {outputStamps[i]:outputPrices[i] for i in range(len(outputPrices))}
		return(output)

	def queryPriceCurrent(self, network, token):
		networkTokens = {network:[token.lower()]};
		hq = historicalQuery(networkTokens, endTime=-1, verbose=self.verbose);
		return(hq.getCurrentPrice(network, token));

def main():

	verbose = False;
	pq = priceQuery(verbose=verbose);

	# Midnight Jan 1 2022, UTC
	timeStart = 1640995200;
	
	# some time in the future
	timeEnd = timeStart + 1*60;

	# network, token
	network = "ethereum"
	BAL = "0xba100000625a3754423978a60c9317c58a424e3D";

	pricesDuration = 	pq.queryPricesInDuration(network, BAL, timeStart, timeEnd);
	priceAtTime = 		pq.queryPriceAtTime(network, BAL, timeStart);
	priceNow = 			pq.queryPriceCurrent(network, BAL);

	print(pricesDuration)
	print(priceAtTime);
	print(priceNow);
if __name__ == '__main__':
	main()