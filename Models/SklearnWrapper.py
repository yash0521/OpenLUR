import numpy as np
import pandas as pd
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.model_selection import KFold, train_test_split
from scipy.stats import shapiro

from utils.MyPool import MyPool as Pool
from utils.color import Color

import utils.paths
import pickle
from os.path import join

class SklearnWrapper:
	def __init__(self, njobs, niter=40, verbosity=0):
		self.njobs = njobs
		self.niter = niter
		self.verbosity = verbosity
		self.out = utils.paths.modeldatadir


	def test_model(self, data, feat_columns, target):



		# Hasenfratz does the 10 fold cross validation 40 times to get a better coverage
		# of the model variables
		inputs = []

		for i in range(self.niter):

			kf = KFold(n_splits=10, shuffle=True)

			for train_index_calib, test_index_calib in kf.split(data):

				train_calib_data = data.iloc[train_index_calib]
				test_calib_data = data.iloc[test_index_calib]

				# First gather all the inputs for each GAM calculation in a list
				inputs_single = (train_calib_data, test_calib_data, target, feat_columns)
				inputs.append(inputs_single)


		# Compute in parallel
		#cm = self.getCalculateModel()
		cm = self.calculateModel
		pool = Pool(processes=int(self.njobs))
		results = pd.DataFrame(pool.map(cm, inputs))
		pool.close()
		pool.join()

		results.columns = ['rmse', 'r2']

		# Calculate Root-mean-square error model
		rmse_model = results.rmse.mean()
		# Get R² from summary
		rsq_model = results.r2.mean()

		self.print('Mean root-mean-square error: {} particles/cm^3'.format(rmse_model), 1)
		self.print('Mean R2: {}'.format(rsq_model), 1)
		self.print('The RMSE is normally distributed with W={}'.format(shapiro(results.rmse.values)[0]), 1)
		self.name = self.name + "_smallData"

		pickle.dump(results, open(join(self.out + self.name + ".p"), "wb"))

		return rmse_model, rsq_model


	#def getCalculateModel(self):
	def calculateModel(self, inputs):
		train_data, test_data, target, columns = inputs

		X_train = train_data[columns]
		X_test = test_data[columns]

		y_train = train_data[target]
		y_test = test_data[target]

		# train on smaller dataset
		X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.33)

		# self.print("Doing {}".format(path), 1)

		m = self.model()
		m.fit(X_train, y_train)

		pred = m.predict(X_test)

		rmse = np.sqrt(mean_squared_error(y_test, pred))
		r2 = r2_score(y_test, pred)

		self.print('Root-mean-square error: {} particles/cm^3'.format(rmse), 2)
		self.print('R2: {}'.format(r2), 2)

		return rmse, r2
		#return calculateModel


	def print(self, message, verbosity):
		if verbosity <= self.verbosity:
			if verbosity==0:
				print(Color.CYAN + message + Color.END)
			elif verbosity==1:
				print(Color.RED + message + Color.END)
			elif verbosity==2:
				print(Color.BOLD + message + Color.END)

