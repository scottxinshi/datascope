import time
import mlflow

# Point to the same database the UI uses
mlflow.set_tracking_uri("sqlite:///mlflow.db")

# Start MLflow experiment
mlflow.set_experiment("datascope")

def track_llm_call(question, route, answer, tokens_used, start_time):
    """Log every LLM interaction to MLflow"""
    
    duration = time.time() - start_time
    
    estimated_cost = (tokens_used * 0.59) / 1_000_000

    with mlflow.start_run():
        mlflow.log_param("question", question[:250])
        mlflow.log_param("route", route)
        mlflow.log_param("answer", answer[:250])
        
        mlflow.log_metric("duration_seconds", round(duration, 2))
        mlflow.log_metric("tokens_used", tokens_used)
        mlflow.log_metric("estimated_cost_usd", round(estimated_cost, 6))