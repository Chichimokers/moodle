import os
import matplotlib.pyplot as plt
from scipy import interp

class RocCurve(object):

    dirname = ''

    def __init__(self, dirname, figid):
        self.dirname = dirname
        plt.figure(figid)

    def add(self, fpr, tpr, label):
        plt.plot(fpr, tpr, label=label)

    def store(self, runid):
        plt.plot([0, 1], [0, 1], 'k--')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('Provided data ROC curve/s')
        plt.legend(loc="lower right")

        filepath = os.path.join(self.dirname, runid + '.roc.png')
        plt.savefig(filepath, format='png')

        return filepath
