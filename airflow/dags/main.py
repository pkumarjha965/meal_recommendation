import sys

# from opt.airflow.plugins.meal_predict_main import suggest_meal

sys.path.append('/home/prashant.jha/PycharmProjects/pythonProject/opt/airflow/plugins', )
from  meal_predict_main import suggest_meal

suggest_meal()