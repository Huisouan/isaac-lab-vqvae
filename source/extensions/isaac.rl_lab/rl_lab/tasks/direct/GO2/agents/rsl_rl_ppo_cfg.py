# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

from omni.isaac.lab.utils import configclass

from tasks.utils.wappers.rsl_rl import (
    RslRlOnPolicyRunnerCfg,
    RslRlPpoActorCriticCfg,
    RslRlPpoAlgorithmCfg,
    RslRlPpoPMCCfg,
    Z_settings,
)


@configclass
class UnitreeGo2RoughPMCPPORunnerCfg(RslRlOnPolicyRunnerCfg):
    num_steps_per_env = 24
    max_iterations = 9000
    save_interval = 50
    experiment_name = "unitree_go2_rough"
    empirical_normalization = False
    policy = RslRlPpoPMCCfg(
        class_name="PMC",
        init_noise_std=0.1,
        actor_hidden_dims=[256, 256],
        encoder_hidden_dims=[256, 256],
        decoder_hidden_dims=[256, 256],
        critic_hidden_dims=[256, 256],
        activation="relu",
        State_Dimentions = 45
        
    )
    z_settings = Z_settings(
            z_length = 64,
            num_embeddings = 256,
            norm_z = False,
            bot_neck_z_embed_size = 64,
            bot_neck_prop_embed_size = 64,
    )
    algorithm = RslRlPpoAlgorithmCfg(
        value_loss_coef=1.0,
        use_clipped_value_loss=True,
        clip_param=0.1,
        entropy_coef=0.00,
        num_learning_epochs=16,
        num_mini_batches=4,
        learning_rate=0.00001,
        schedule="fixed",
        gamma=0.95,
        lam=0.95,
        desired_kl=0.01,
        max_grad_norm=0.5,
    )


@configclass
class UnitreeGo2FlatPMCPPORunnerCfg(UnitreeGo2RoughPMCPPORunnerCfg):
    def __post_init__(self):
        super().__post_init__()

        self.max_iterations = 900000000
        self.experiment_name = "unitree_go2_flat"
        #self.policy.actor_hidden_dims = [256, 256, 256]
        #self.policy.critic_hidden_dims = [256, 256, 256]

@configclass
class UnitreeGo2RoughCVQVAEPPORunnerCfg(UnitreeGo2FlatPMCPPORunnerCfg):
    
    def __post_init__(self):
        super().__post_init__()
        self.policy.class_name = "CVQVAE"



@configclass
class UnitreeGo2RoughAMPPPORunnerCfg(RslRlOnPolicyRunnerCfg):
    num_steps_per_env = 24
    max_iterations = 9000
    save_interval = 50
    experiment_name = "unitree_go2_rough"
    empirical_normalization = False
    policy = RslRlPpoPMCCfg(
        class_name="PMC",
        init_noise_std=1.0,
        actor_hidden_dims=[256, 256],
        encoder_hidden_dims=[256, 256],
        decoder_hidden_dims=[256, 256],
        critic_hidden_dims=[256, 256],
        activation="relu",
        
    )
    algorithm = RslRlPpoAlgorithmCfg(
        value_loss_coef=1.0,
        use_clipped_value_loss=True,
        clip_param=0.1,
        entropy_coef=0.00,
        num_learning_epochs=16,
        num_mini_batches=4,
        learning_rate=0.00001,
        schedule="fixed",
        gamma=0.95,
        lam=0.95,
        desired_kl=0.01,
        max_grad_norm=0.5,
    )


@configclass
class UnitreeGo2FlatAMPPPORunnerCfg(UnitreeGo2RoughAMPPPORunnerCfg):
    def __post_init__(self):
        super().__post_init__()

        self.max_iterations = 900000000
        self.experiment_name = "unitree_go2_flat"
        #self.policy.actor_hidden_dims = [256, 256, 256]
        #self.policy.critic_hidden_dims = [256, 256, 256]

