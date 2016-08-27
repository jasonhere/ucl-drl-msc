#!/bin/sh

nohup python src/run.py --outdir ddpg-results/experiement1 --env CollaborativeFiltering-v0 --train 20 --test 1 --tmax 2314 --total 2163000 --wolpertinger --create_index --wp_total_actions 3883 --wp_action_set_file "data/embeddings-movielens1m.csv" --knn_backend sklearn --nn_index_file indexStorageTest --knn 194 >> run.log &
echo $! > pid

sleep 1

echo Process started. Logs are written in run.log