# GPT-4 CSP Experiments Pipeline
Codebase related to paper at [NeurIPS 2023 FMDM Workshop](https://sites.google.com/view/fmdm-neurips23/). Preprint can be found [here](https://arxiv.org/abs/2310.12397). For the exact data and pipeline discussed, see [this branch](https://github.com/kstechly/gptcolor/tree/fmdm_data).

## Requirements
- Linux
- Python 3.6+
  - Install required packages with `pip install -r requirements.txt`
- OpenAI API Key

## Usage

Data must be provided by the user. Afterwards, the full pipeline proceeds from `prompt_generation.py` to `response_generation.py` to `response_evaluation.py` to `stats.generation.py`. All are intended to be run in a terminal from the `llm-csp` directory.

### Prompt Generation

This script takes instance data and converts it into a `json` file containing natural language prompts. 

**Required Arguments:**
- `--domain` Problem domain to generate for (e.g. `graph-coloring` or `color-verification`. See `llm-csp/domain_utils/__init__.py` for a list of current options.

**Optional Arguments:**
- `--start` Number of first instance to run. (Default: 1)
- `--end` Number of last instance to run. All instances in between will be processed. (Default: 100)
- `--problem` Problem variant to generate. Relevant for some domains (required for `color-verification`)

### Response Generation

For this script to work, you must have an `OpenAI_API_KEY` env var set (e.g. `echo OpenAI_API_KEY={your api key}`). The script takes the generated prompts and sends them to your engine of choice and saves the data after every response.

**Required Arguments:**
- `--engine` OpenAI engine to use. See [here](https://platform.openai.com/docs/models) for options. Only chat completion models work, and you must append `_chat` to the end of your engine name.
- `--domain` Problem domain to run (e.g. `graph-coloring` or `color-verification`. See `llm-csp/domain_utils/__init__.py` for a list of current options.

**Optional Arguments:**
- `--temperature` Temperature from 0.0 to 2.0. Default: 0
- `--problem` Problem variant to run. Relevant for some domains (required for `color-verification`)
- `--backprompt` If multiprompting, provide the type of backprompt to pass to the domain. Common types: `zero`, `passfail`, `full`, `llm`, `top`. These are defined per domain in the domain file's `backprompt` function.
- `--backprompt_num` If multiprompting, provide the maximum number of prompts to try. Double this number to get expected behavior for LLM self-critique backprompting
- `--verbose` Flag to print more details
- `--run_till_completion` Flag to force prompting to retry until all instances succeed (in the case of API errors). Default behavior is to just list failed instances.
- `--specific_instances` List of instances (labeled by their integer) to run. Use if you only want to run a scattered subset.
- `--ignore_existing` Flag to delete existing output data and overwrite it with new.
- `--end_number` For running from instance `start_number` to `end_number`. If this isn't specified, specifying `start_number` won't do anything.
- `--start_number` For running from instance `start_number` to `end_number`. You must specify `end_number` for this to work.

### Response Evaluation

This script evaluates responses and creates a `json` file of domain-relevant data. Pass the same arguments to this as you previously passed to the Response Generation script, except for `backprompt_num`.

### Stats Generation

This script prints basic statistics about the evaluated data. Use the same arguments as previously passed to response evaluation. To generate statistics specific to only the first `B` prompts, pass an integer `B` to `--backprompt_num`.

## Adding New Domains
All domains live in `llm-csp/domain_utils/`. To add a new one, create a new python module in the folder, and then modify `llm-csp/domain_utils/__init__.py` in three places to import and name it. All data must be stored in a new folder `data/{domain_name}/`, with each instance stored as a separate file labeled `instance-{i}.{file_ending()}`

A domain module must contain three functions:
   1. file_ending: None -> str
       - returns file ending used by instance data in the domain.
   2. generate: instance_text, problem_type -> str
       - returns natural language translations of a formal language instance
   3. evaluate: instance_text, response_trace, problem_type -> dict
       - returns a dict summarizing results. must contain "correct" bool key
       - the type of response_trace is a dictionary containing "query", "response", and for backprompting "backprompt {n}" and "response {n}" for as many rounds as were necessary. The maximum n "response {n}" value will be extracted as the final answer
   4. backprompt: instance_text, model_response, backprompt_type -> str
      - returns natural language backprompt in response to a query
