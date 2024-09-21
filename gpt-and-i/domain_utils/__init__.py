# To add a new domain, create a module in this subfolder, and then add it to the following:
from domain_utils import graph_coloring
from domain_utils import color_verification, game24, game24_verification
__all__ = ["graph_coloring","color_verification", "game24", "game24_verification"]
domains = {"graph_coloring":graph_coloring,"color_verification":color_verification, "game24":game24, "game24_verification":game24_verification}

# A domain module must contain three functions:
#   1. file_ending: None -> str
#   2. generate: instance_text, problem_type -> str
#       (returns natural language translations of a formal language instance)
#   3. evaluate: instance_text, response_trace, problem_type -> dict
#       (returns a dict summarizing results. must contain "correct" bool key)
#       (the type of response_trace is a dictionary containing "query", "response", and for backprompting "backprompt {n}" and "response {n}" for as many rounds as were necessary. The maximum n "response {n}" value will be extracted as the final answer)
#   4. backprompt: instance_text, model_response, backprompt_type -> str
#       (returns natural language backprompt in response to a query)
#
# Instance data for the ith instance must be stored in data/{domain_name}/instance-{i}.{file_ending()}
