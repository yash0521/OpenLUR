import csv
import math
import pickle

import numpy as np
import scipy.io as sio
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.model_selection import train_test_split, KFold

import paths
#from LUR_preprocessing import query_osm_polygone, query_osm_highway
from wgs84_ch1903 import *


class Regressor:
	def __init__(self):
		self.regressionModel = None
		self.features = []

	def fit(self, X_train, y_train):
		self.total_features = X_train.shape[1]
		features_to_test = [i for i in range(self.total_features)]
		chosen_features = []
		#print("count of features: {}".format(len(features_to_test)))

		dr2 = 100.0
		r2prev = 0.0

		while dr2 > 0.01:

			scores = []
			for feature in features_to_test:
				regressionModel = LinearRegression()
				feats = [i for i in chosen_features]
				feats.append(feature)
				regressionModel.fit(X_train[:, feats], y_train)
				scores.append(regressionModel.score(X_train[:, feats], y_train))

			r2 = max(scores)

			#print("r squared: {}".format(r2))
			dr2 = r2 - r2prev
			r2prev = r2
			#print("difference to previous r squared: {}".format(dr2))

			if dr2 > 0.01:
				chosen_features.append(features_to_test[scores.index(r2)])
				features_to_test.pop(scores.index(r2))

		#print("Chosen features for r2 of {} on test data:".format(r2prev))
		#print(chosen_features)

		self.features = chosen_features

		self.regressionModel = LinearRegression()
		self.regressionModel.fit(X_train[:, chosen_features], y_train)


	def predict(self, X):
		if X.shape[1] == self.total_features:
			X_predict = X[:, self.features]
		else:
			X_predict = X
		return self.regressionModel.predict(X_predict)

	def score(self, X, y):
		if X.shape[1] == self.total_features:
			X_predict = X[:, self.features]
		else:
			X_predict = X
		return self.regressionModel.score(X_predict, y)

	def adj_score(self, X, y):
		if X.shape[1] == self.total_features:
			X_predict = X[:, self.features]
		else:
			X_predict = X
		score = self.regressionModel.score(X_predict, y)
		score  = 1-((1-score)*(y.shape[0] - 1))/(y.shape[0] - len(self.features) - 1)
		return score

	def giveModel(self):
		return self



def plot_map(plotModel, features):
	bounds = sio.loadmat(paths.rootdir + "bounds")['bounds']
	indus_buffer = []
	highway_buffer = []
	for feature in features:
		if feature <= 29:
			indus_buffer.append(feature * 50)
		if (feature > 29) & (feature <= 58):
			highway_buffer.append((feature - 29) * 50)

	num_indus = len(indus_buffer)
	num_highway = len(highway_buffer)
	num_features = len(features)

	gridsize = 100
	gridhalf = gridsize / 2
	x = [i for i in range(bounds[0, 0], bounds[0, 1], gridsize)]
	y = [i for i in range(bounds[0, 2], bounds[0, 3], gridsize)]

	data_plot = np.zeros((len(x), len(y), (3 + num_features)))

	for i in range(len(x)):
		for j in range(len(y)):
			data_plot[i, j, 0] = x[i]
			data_plot[i, j, 1] = y[j]

			lat = CHtoWGSlat(x[i] + gridhalf, y[j] + gridhalf)
			lon = CHtoWGSlng(x[i] + gridhalf, y[j] + gridhalf)

			for k in range(num_indus):
				try:
					temp = query_osm_polygone(lon, lat, indus_buffer[k], "landuse", "industrial")
				except Exception as e:
					print(e)
					print("error")
					print(lon, lat)
					temp = 0
				data_plot[i, j, k + 2] = temp

			for k in range(num_highway):
				try:
					temp = query_osm_highway(lon, lat, highway_buffer[k])
				except Exception as e:
					print(e)
					print("error")
					print(lon, lat)
					temp = 0
				data_plot[i, j, k + 2 + num_indus] = temp

				data_plot[i, j, -1] = plotModel.predict(
					data_plot[i, j, 2:(2 + num_features)].reshape(1, num_features))

	pickle.dump(data_plot, open(paths.lurdata + "pm_01072012_31092012_predicted.p", "wb"))


def cross_validation(X_t, y_t):
	kf = KFold(n_splits=10, shuffle=True)
	score = []
	features = []

	for train, test in kf.split(X_t):
		X_train, y_train = X_t[train, :], y_t[train]
		X_test, y_test = X_t[test, :], y_t[test]
		model = Regressor()
		model.fit(X_train, y_train)
		score.append(model.score(X_test, y_test))
		features.append(model.features)

	scoreMean = np.mean(score)
	print(score)
	print(scoreMean)
	return scoreMean, features

def adjust_Rsq(model, X_test, y_test):
	try:
		score  = 1-((1-model.score(X_test, y_test))*(y_test.shape[0] - 1))/(y_test.shape[0] - len(model.features) - 1)
	except:
		score  = 1-((1-model.score(X_test, y_test))*(y_test.shape[0] - 1))/(y_test.shape[0] - X_test.shape[1] - 1)

	return score

if __name__ == "__main__":

	file = "pm_ha_ext_01012013_31032013_landUse.csv"
	# file = "pm_ha_ext_01042012_30062012_landUse.csv"
	# file = "pm_ha_ext_01072012_31092012_landUse.csv"
	# file = "pm_ha_ext_01102012_31122012_landUse.csv"

	data = []
	with open(paths.lurdata + file, 'r') as myfile:
		reader = csv.reader(myfile)
		for row in reader:
			data.append([float(i) for i in row])

	train_data_np = np.array(data)
	#X_train, X_val, y_train, y_val = train_test_split(train_data_np[:, 3:], train_data_np[:, 2], test_size=0.1)

	#model = cross_validation(X_train, y_train)
	#model, features = regression(X_train, y_train)
	#features = model.features

	#pred = model.predict(X_val[:, features])

	#r2 = model.score(X_val[:, features], y_val)
	#rmse = math.sqrt(mean_squared_error(y_val, pred))
	#print("r2 on validation data: {}".format(r2))
	#print("rmse on validation data: {}".format(rmse))

	#pickle.dump({'model': model, 'features': features, 'r2': r2, 'rmse': rmse, 'X_train': X_train, 'X_val':X_val, 'y_train': y_train, 'y_val':y_val, 'predictions':pred, 'data':train_data_np},
	#            open(paths.lurdata + "models/" + file[:-4] + "_Model.p", 'wb'))

	X_train, y_train = train_data_np[:,3:], train_data_np[:,2]

	scoreTotal = []
	featuresTotal = []
	for i in range(40):
		score, features = cross_validation(X_train, y_train)
		scoreTotal.append(score)
		featuresTotal.append(features)

	print(np.mean(scoreTotal))
