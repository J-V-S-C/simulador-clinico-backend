from models import InteractionClassification
from ports.evaluator import Evaluation


class FakeEvaluator:
    def __init__(self):
        self.calls = []
        self.response = "Estou melhor."
        self.classification = InteractionClassification.CORRECT
        self.error = None
        self.on_evaluate = None

    async def evaluate(self, simulation, student_text, symptom_name):
        self.calls.append((student_text, symptom_name))
        if self.error:
            raise self.error
        if self.on_evaluate:
            self.on_evaluate()
        return Evaluation(self.response, self.classification)
