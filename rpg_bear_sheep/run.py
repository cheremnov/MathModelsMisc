
from model import BearSheepPredation

model = BearSheepPredation()
model.run_model()
print(model.datacollector.get_model_vars_dataframe())
