from BinaryClassifier import BinaryClassifier
from NN import NN
from BinaryClassifierNNCV import BinaryClassifierNNCV

class BinaryClassifierNN(BinaryClassifier):

    def get_classifier(self, X, y):

        epsilon = None
        nn_iterations=10000
        reg_lambda = 0.0005
        # Number of elements per hidden layer.
        nn_hidden = [5, 3]

        # Find out the best epsilon value.
        if hasattr(self, 'epsilon') == False:
            epsilon_values = [0.000001, 0.000005, 0.00001, 0.00005, 0.0001, 0.0005, 0.001,
                 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10]
            cv = BinaryClassifierNNCV(epsilon_values, reg_lambda, nn_hidden)
            cv.fit(X, y)
            self.epsilon = cv.get_best_epsilon()

        # Return the classifier using the epsilon value we selected.
        return NN(nn_iterations, self.epsilon, reg_lambda, nn_hidden)

    def store_learning_curve(self):
        pass
