import logging
import os
import math
import resource

import numpy as np

from sklearn.cross_validation import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_curve, auc
from sklearn.linear_model import LogisticRegressionCV

from Classifier import Classifier
from RocCurve import RocCurve
from LearningCurve import LearningCurve

class BinaryClassifier(Classifier):

    def __init__(self):

        super(BinaryClassifier, self).__init__()

        self.aucs = []
        self.classes = [1, 0]

        # Logging.
        logfile = self.get_log_filename()
        logging.basicConfig(filename=logfile,level=logging.DEBUG)


    def get_log_filename(self):
        if self.log_into_file == False:
            return False
        return os.path.join(self.dirname, self.get_id() + '.log')


    def evaluate(self, filepath, accepted_phi=0.7, accepted_deviation=0.02, n_test_runs=1):

        [self.X, self.y] = self.get_examples(filepath)
        self.scale_x()

        # Classes balance check.
        counts = []
        y_array = np.array(self.y.T[0])
        counts.append(np.count_nonzero(y_array))
        counts.append(len(y_array) - np.count_nonzero(y_array))
        logging.info('Number of examples by y value: %s' % str(counts))
        balanced_classes = self.check_classes_balance(counts)
        if balanced_classes != False:
            logging.warning(balanced_classes)

        # ROC curve.
        self.roc_curve_plot = RocCurve(self.dirname, 2)

        # Learning curve.
        if self.log_into_file != False:
            self.store_learning_curve()

        for i in range(0, n_test_runs):

            # Split examples into training set and test set (80% - 20%)
            X_train, X_test, y_train, y_test = train_test_split(self.X, self.y, test_size=0.2)

            classifier = self.train(X_train, y_train)

            self.rate_prediction(classifier, X_test, y_test)

        # Store the roc curve.
        if self.log_into_file:
            fig_filepath = self.roc_curve_plot.store(self.get_id())
            logging.info("Figure stored in " + fig_filepath)

        # Return results.
        result = self.get_bin_results(accepted_phi, accepted_deviation)

        # Add the run id to identify it in the caller.
        result['id'] = int(self.get_id())

        logging.info("Accuracy: %.2f%%" % (result['accuracy'] * 100))
        logging.info("Precision (predicted elements that are real): %.2f%%" % (result['precision'] * 100))
        logging.info("Recall (real elements that are predicted): %.2f%%" % (result['recall'] * 100))
        logging.info("Phi coefficient: %.2f%%" % (result['phi'] * 100))
        logging.info("AUC standard desviation: %.4f" % (result['auc_deviation']))

        return result


    def train(self, X_train, y_train):

        # Init the classifier.
        classifier = self.get_classifier(X_train, y_train)

        # Fit the training set. y should be an array-like.
        classifier.fit(X_train, y_train[:,0])

        return classifier


    def rate_prediction(self, classifier, X_test, y_test):

        # Calculate scores.
        y_score = self.get_score(classifier, X_test, y_test[:,0])
        y_pred = classifier.predict(X_test)

        # Transform it to an array.
        y_test = y_test.T[0]

        fpr, tpr, _ = roc_curve(y_test, y_score)
        self.aucs.append(auc(fpr, tpr))

        # Calculate accuracy, sensitivity and specificity.
        [acc, prec, rec, ph] = self.calculate_metrics(y_test == 1, y_pred == 1)
        self.accuracies.append(acc)
        self.precisions.append(prec)
        self.recalls.append(rec)
        self.phis.append(ph)

        # Draw it.
        self.roc_curve_plot.add(fpr, tpr, 'Positives')


    def get_score(self, classifier, X_test, y_test):

        probs = classifier.predict_proba(X_test)

        n_examples = len(y_test)

        # Calculated probabilities of the correct response being true.
        return probs[range(n_examples), y_test]


    def store_model(self):
        # Train the model again now with all the dataset and store the results.
        classifier = self.train(self.X, self.y)
        np.savetxt(os.path.join(self.dirname, self.get_id() + '.coef.txt'), classifier.coef_)
        np.savetxt(os.path.join(self.dirname, self.get_id() + '.intercept.txt'), classifier.intercept_)


    def calculate_metrics(self, y_test_true, y_pred_true):

        test_p = y_test_true
        test_n = np.invert(test_p)

        pred_p = y_pred_true
        pred_n = np.invert(pred_p)

        pp = np.count_nonzero(test_p)
        nn = np.count_nonzero(test_n)
        tp = np.count_nonzero(test_p * pred_p)
        tn = np.count_nonzero(test_n * pred_n)
        fn = np.count_nonzero(test_p * pred_n)
        fp = np.count_nonzero(test_n * pred_p)

        accuracy = (tp + tn) / float(pp + nn)
        if tp != 0 or fp != 0:
            precision = tp / float(tp + fp)
        else:
            precision = 0
        if tp != 0 or fn != 0:
            recall = tp / float(tp + fn)
        else:
            recall = 0

        denominator = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
        if denominator != 0:
            phi = ( ( tp * tn) - (fp * fn) ) / math.sqrt(denominator)
        else:
            phi = 0

        return [accuracy, precision, recall, phi]


    def get_bin_results(self, accepted_phi, accepted_deviation):

        avg_accuracy = np.mean(self.accuracies)
        avg_precision = np.mean(self.precisions)
        avg_recall = np.mean(self.recalls)
        avg_phi = np.mean(self.phis)
        avg_aucs = np.mean(self.aucs)

        result = dict()
        result['auc'] = avg_aucs
        result['accuracy'] = avg_accuracy
        result['precision'] = avg_precision
        result['recall'] = avg_recall
        result['phi'] = avg_phi
        result['auc_deviation'] = np.std(self.aucs)
        result['accepted_phi'] = accepted_phi
        result['accepted_deviation'] = accepted_deviation

        result['exitcode'] = 0
        result['errors'] = []

        # If deviation is too high we may need more records to report if
        # this model is reliable or not.
        auc_deviation = np.std(self.aucs)
        if auc_deviation > accepted_deviation:
            result['errors'].append('The results obtained varied too much,'
                + ' we need more examples to check if this model is valid.'
                + ' Model deviation = %f, accepted deviation = %f' \
                % (auc_deviation, accepted_deviation))
            result['exitcode'] = 1

        if avg_phi < accepted_phi:
            result['errors'].append('The model is not good enough. Model phi ='
                + ' %f, accepted phi = %f' \
                % (avg_phi, accepted_phi))
            result['exitcode'] = 1

        return result


    def store_learning_curve(self):
        lc = LearningCurve(self.get_id())
        lc.set_classifier(self.get_classifier(self.X, self.y))
        lc_filepath = lc.save(self.X, self.y, self.dirname)
        if lc_filepath != False:
            logging.info("Figure stored in " + lc_filepath)


    def get_classifier(self, X, y):

        solver = 'liblinear'
        multi_class = 'ovr'

        if hasattr(self, 'C') == False:

            # Cross validation - to select the best constants.
            lgcv = LogisticRegressionCV(solver=solver, multi_class=multi_class);
            lgcv.fit(X, y[:,0])

            if len(lgcv.C_) == 1:
                self.C = lgcv.C_[0]
            else:
                # Chose the best C = the class with more examples.
                # Ideally multiclass problems will be multinomial.
                [values, counts] = np.unique(y[:,0], return_counts=True)
                self.C = lgcv.C_[np.argmax(counts)]
                logging.info('From all classes best C values (%s), %f has been selected' % (str(lgcv.C_), C))
            print("Best C: %f" % (self.C))

        return LogisticRegression(solver=solver, tol=1e-1, C=self.C)


    def reset_rates(self):
        super(BinaryClassifier, self).reset_rates()
        self.aucs = []

        # ROC curve.
        self.roc_curve_plot = RocCurve(self.dirname, 2)
