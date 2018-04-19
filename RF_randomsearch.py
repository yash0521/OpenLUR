import argparse
import numpy as np
import pandas as pd
import time
import pickle
import logging

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.model_selection import KFold, train_test_split

from utils.DataLoader import loadData
from utils.MyPool import MyPool as Pool
import utils.paths

from os.path import isdir, join
from os import mkdir

logger = logging.getLogger('RF_optimizer')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)


global refit
refit = False

def randomSearchSingle(X_train, y_train, X_test, y_test):

	n_estimators = int(np.random.uniform(1, 1000, size=1))
	max_features = float(np.random.uniform(0., 1., size=1))
	min_samples_leaf = int(np.random.uniform(1, 100, size=1))
	min_samples_split = int(np.random.uniform(2, 20, size=1))
	bootstrap = bool(np.random.choice([True, False], size=1))


	rf = RandomForestRegressor(n_estimators=n_estimators,
							   #max_features=max_features,
							   #min_samples_leaf=min_samples_leaf,
							   #min_samples_split=min_samples_split,
							   bootstrap=bootstrap)
	rf.fit(X_train, y_train)

	return rf, np.sqrt(mean_squared_error(rf.predict(X_test), y_test))


def randomSearchFold(data):
	train_data, test_data, maxtime, feat_columns, target = data

	X_search = train_data[feat_columns].values
	X_test = test_data[feat_columns].values

	y_search = train_data[target].values
	y_test = test_data[target].values

	X_train, X_val, y_train, y_val = train_test_split(X_search, y_search, test_size=0.33)



	starttime =  time.time()

	bestModel = None
	bestScore = 1000000
	numModels = 0

	while (time.time() - starttime) < maxtime:
		model, score = randomSearchSingle(X_train, y_train, X_val, y_val)
		logger.debug(str(score))
		numModels += 1
		if score < bestScore:
			bestModel = model
			bestScore = score

	if refit:
		bestModel.fit(X_search, y_search)

	logger.info(bestModel.get_params())
	pred = bestModel.predict(X_test)
	rmse = np.sqrt(mean_squared_error(y_test, pred))
	rsq = r2_score(y_test, pred)

	logger.info("Fold score: RMSE: {:.2f}\tR2: {:.2f}\tNumber of models: {}".format(rmse/1000, rsq, numModels))

	return rmse, rsq



def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("-n", "--seasonNumber", help="Number of season", type=int, default=1)
	parser.add_argument("-f", "--features",
					  help="Dataset to build model on: (1) OpenSense, (2) OSM, (3) OSM + distances", type=int, default=1)
	parser.add_argument("-i", "--iterations", help="Number of iterations to mean on", type=int, default=40)
	parser.add_argument("-p", "--processes", help="Number of parallel processes", type=int, default=4)
	parser.add_argument("-t", "--time", help="Give time for parametertuning of each fold in seconds", type=int, default=60)
	parser.add_argument("-r", "--refit", help="determines, if the model should be refittet", action='store_true')

	args = parser.parse_args()

	refit = args.refit

	data, feat_columns, target, feat = loadData(args.seasonNumber, args.features)

	inputs = []

	for i in range(args.iterations):
		kf = KFold(n_splits=10, shuffle=True)
		for train_index, test_index in kf.split(data):
			train_data = data.iloc[train_index]
			test_data = data.iloc[test_index]

			inputs.append((train_data, test_data, args.time, feat_columns, target))

	pool = Pool(processes=int(args.processes))
	results = pd.DataFrame(pool.map(randomSearchFold, inputs))
	pool.close()
	pool.join()

	results.columns = ['rmse', 'r2']

	print("Final score: RMSE: {:.2f}\tR2: {:.2f}".format(results.rmse.mean()/1000, results.r2.mean()))

	f = join(utils.paths.modeldatadir + join(str(args.seasonNumber), feat + "_RFOptimized_{}s".format(args.time)))
	if refit:
		f = f + "_refit"

	f = f + ".p"

	pickle.dump(results, open(f, "wb"))


if __name__=="__main__":
	main()