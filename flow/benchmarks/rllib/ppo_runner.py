"""Runs the environments located in flow/benchmarks.
The environment file can be modified in the imports to change the environment
this runner script is executed on. This file runs the PPO algorithm in rllib
and utilizes the hyper-parameters specified in:
Proximal Policy Optimization Algorithms by Schulman et. al.
"""
import json

import ray
from ray.rllib.agents.agent import get_agent_class
from ray.tune import run_experiments
from ray.tune.registry import register_env
from ray.tune import grid_search

from flow.utils.registry import make_create_env
from flow.utils.rllib import FlowParamsEncoder

# use this to specify the environment to run
from flow.benchmarks.merge0 import flow_params

# number of rollouts per training iteration
N_ROLLOUTS = 15
# number of parallel workers
N_CPUS = 15

if __name__ == "__main__":
    # get the env name and a creator for the environment
    create_env, env_name = make_create_env(params=flow_params, version=0)

    # initialize a ray instance
    ray.init("localhost:6379")

    alg_run = "PPO"

    horizon = flow_params["env"].horizon
    agent_cls = get_agent_class(alg_run)
    config = agent_cls._default_config.copy()
    config["num_workers"] = min(N_CPUS, N_ROLLOUTS)
    config["horizon"] = 750
    config["train_batch_size"] = horizon * N_ROLLOUTS
    config["use_gae"] = True
    config["horizon"] = horizon
    config["lambda"] = .97 #grid_search([0.97, 1.0])
    config["lr"] = 5e-4
    config["num_sgd_iter"] = 10
    config["model"]["fcnet_hiddens"] = [100, 50, 25]
    config["observation_filter"] = "NoFilter"

    # save the flow params for replay
    flow_json = json.dumps(
        flow_params, cls=FlowParamsEncoder, sort_keys=True, indent=4)
    config['env_config']['flow_params'] = flow_json
    config['env_config']['run'] = alg_run

    # Register as rllib env
    register_env(env_name, create_env)

    trials = run_experiments({
        flow_params["exp_tag"]: {
            "run": alg_run,
            "env": env_name,
            "config": {
                **config
            },
            "checkpoint_freq": 25,
            "max_failures": 999,
            "stop": {
                "training_iteration": 500
            },
            "num_samples": 6,
            "upload_dir": "s3://eugene.experiments/sa_merge_test_oldsumo_raymaster"
        },
    })
