python3 response_evaluation.py -d graph_coloring -e gpt-4_chat -i -b 15top1
python3 response_evaluation.py -d graph_coloring -e gpt-4_chat -i -b 05top0.5
python3 response_evaluation.py -d graph_coloring -e gpt-4_chat -i -b 05top1
python3 response_evaluation.py -d graph_coloring -e gpt-4_chat -i -b 05top1.5
python3 response_evaluation.py -d graph_coloring -e gpt-4_chat -i -b full
python3 response_evaluation.py -d graph_coloring -e gpt-4_chat -i -b first
python3 response_evaluation.py -d graph_coloring -e gpt-4_chat -i -b llm
python3 response_evaluation.py -d graph_coloring -e gpt-4_chat -i -b passfail

python3 stats_generation.py -e gpt-4_chat -d graph_coloring -b 15top1
python3 stats_generation.py -e gpt-4_chat -d graph_coloring -b 05top0.5
python3 stats_generation.py -e gpt-4_chat -d graph_coloring -b 05top1
python3 stats_generation.py -e gpt-4_chat -d graph_coloring -b 05top1.5
python3 stats_generation.py -e gpt-4_chat -d graph_coloring -b full
python3 stats_generation.py -e gpt-4_chat -d graph_coloring -b first
python3 stats_generation.py -e gpt-4_chat -d graph_coloring -b llm
python3 stats_generation.py -e gpt-4_chat -d graph_coloring -b passfail

python3 graph_generation.py
