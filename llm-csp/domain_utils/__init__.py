# To add a new domain, create a module in this subfolder, and then add it to the following:
from domain_utils import random_sat, graph_coloring
__all__ = ["random_sat","graph_coloring"]
domains = {"random_sat":random_sat,"graph_coloring":graph_coloring}

# A domain module must contain three functions:
#   1. file_ending: None -> str
#   2. generate: instance_text -> str
#       (returns natural language translations of a formal language instance)
#   3. evaluate: instance_text, model_response -> bool
#       (returns success/failure of model on an instance)
#
# Instance data for the ith instance must be stored in data/{domain_name}/instance-{i}.{file_ending()}
