from cgPriceQuery import cgPriceQuery
import json

def main():
	verbose = False;
	pq = cgPriceQuery.priceQuery(verbose=verbose);

	# Midnight Jan 1 2022, UTC
	timeStart = 1640995200;
	
	# some time in the future
	timeEnd = timeStart + 3*60;

	# network, token
	network = "ethereum"
	BAL = "0xba100000625a3754423978a60c9317c58a424e3D";
	token = BAL;

	pricesDuration = 	pq.queryPricesInDuration(network, token, timeStart, timeEnd);
	priceAtTime = 		pq.queryPriceAtTime(network, token, timeStart);
	priceNow = 			pq.queryPriceCurrent(network, token);

	print();
	print("Token:", token)
	print();

	print("----- Prices in Duration Query -----")
	print("Price from", timeStart, "to", timeEnd)
	print(json.dumps(pricesDuration, indent=4))
	print();

	print("----- Price at Past Time Query -----")
	print("Price at", timeStart)
	print(json.dumps(priceAtTime, indent=4))
	print();

	print("----- Prices Now Query -----")
	print("Price now:", priceNow)
	print();

if __name__ == '__main__':
	main()
