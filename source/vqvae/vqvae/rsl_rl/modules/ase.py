#  Copyright 2021 ETH Zurich, NVIDIA CORPORATION
#  SPDX-License-Identifier: BSD-3-Clause


from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal
from torch.nn import RMSNorm
from ...tasks.utils.wappers.rsl_rl import (
    ASECfg,ASENetcfg,
)



class AMPNet(nn.Module):
    is_recurrent = False

    def __init__(
        self,
        mlp_input_num,
        num_actions,
        mlp_hidden_dims=[1024, 1024, 512],

        activation="relu",
        value_activation="tanh",
        init_noise_std=1,
        # 正确的方式是先声明类型，然后创建对象
        State_Dimentions = 45*3,
        rms_momentum = 0.0001,
        seperate_actor_critic = True,
        **kwargs,
    ):
        # 检查是否有未使用的参数
        if kwargs:
            print(
                "ActorCritic.__init__ got unexpected arguments, which will be ignored: "
                + str([key for key in kwargs.keys()])
            )
        super().__init__()
        #parameter init##############################
        # 加载判别器的配置
        self.activation = get_activation(activation)
        self.mlp_input_num = mlp_input_num
        self.mlp_hidden_dims = mlp_hidden_dims

        #############################################
        self.actor_cnn = nn.Sequential()
        self.critic_cnn = nn.Sequential()
        self.actor_mlp = nn.Sequential()
        self.critic_mlp = nn.Sequential()        
        self.seperate_actor_critic = seperate_actor_critic
        
        #build actor
        self.actor_mlp = self._build_mlp(self.mlp_input_num,self.mlp_hidden_dims)   
        #build critic 
        if self.seperate_actor_critic == True:
            self.critic_mlp = self._build_mlp(self.mlp_input_num,self.mlp_hidden_dims)

        #build value
        self.value = self._build_value_layer(input_size=self.mlp_hidden_dims[-1], output_size=1)
        self.value_activation =  nn.Identity()
    
    def _build_enc(self, input_shape):
        if (self._enc_separate):
            self._enc_mlp = nn.Sequential()  # 编码器MLP
            mlp_args = {
                'input_size': input_shape[0], 
                'units': self._enc_units, 
                'activation': self._enc_activation, 
                'dense_func': torch.nn.Linear
            }
            self._enc_mlp = self._build_mlp(**mlp_args)  # 构建编码器MLP

            mlp_init = self.init_factory.create(**self._enc_initializer)  # 编码器初始化器
            for m in self._enc_mlp.modules():
                if isinstance(m, nn.Linear):
                    mlp_init(m.weight)  # 初始化权重
                    if getattr(m, "bias", None) is not None:
                        torch.nn.init.zeros_(m.bias)  # 初始化偏置
        else:
            self._enc_mlp = self._disc_mlp  # 使用判别器MLP

        mlp_out_layer = list(self._enc_mlp.modules())[-2]  # 获取MLP的倒数第二层
        mlp_out_size = mlp_out_layer.out_features  # 获取输出特征数
        self._enc = torch.nn.Linear(mlp_out_size, self._ase_latent_shape[-1])  # 编码器线性层
        
        torch.nn.init.uniform_(self._enc.weight, -ENC_LOGIT_INIT_SCALE, ENC_LOGIT_INIT_SCALE)  # 初始化权重
        torch.nn.init.zeros_(self._enc.bias)  # 初始化偏置
        
        return
        
    def _build_disc(self, input_shape):
        # 初始化判别器的MLP
        self._disc_mlp = nn.Sequential()

        mlp_args = {
            'input_size' : input_shape[0], 
            'units' : self._disc_units, 
            'activation' : self._disc_activation, 
            'dense_func' : torch.nn.Linear
        }
        self._disc_mlp = self._build_mlp(**mlp_args)
        
        # 获取MLP输出的大小
        mlp_out_size = self._disc_units[-1]
        # 初始化判别器的对数概率层
        self._disc_logits = torch.nn.Linear(mlp_out_size, 1)

        # 初始化MLP的权重
        mlp_init = self.init_factory.create(**self._disc_initializer)
        for m in self._disc_mlp.modules():
            if isinstance(m, nn.Linear):
                mlp_init(m.weight)
                if getattr(m, "bias", None) is not None:
                    torch.nn.init.zeros_(m.bias) 

        # 初始化对数概率层的权重和偏置
        torch.nn.init.uniform_(self._disc_logits.weight, -DISC_LOGIT_INIT_SCALE, DISC_LOGIT_INIT_SCALE)
        torch.nn.init.zeros_(self._disc_logits.bias) 

        return   


    def _build_mlp(self,num_input,units):
        input = num_input
        mlp_layers = []
        print('build mlp:', input)
        in_size = input        
        for unit in units:
            mlp_layers.append(nn.Linear(in_size, unit))
            mlp_layers.append(self.activation())
            in_size = unit
        return nn.Sequential(*mlp_layers)

    def _build_value_layer(self,input_size, output_size,):
        return torch.nn.Linear(input_size, output_size)

class ASENet(AMPNet):
    is_recurrent = False

    def __init__(
        self,
        num_actor_obs,
        num_critic_obs,
        num_actions,
        Asecfg :ASECfg = ASECfg(),
        Asenetcfg:ASENetcfg = ASENetcfg(),
        **kwargs,
    ):
        # 检查是否有未使用的参数
        if kwargs:
            print(
                "ActorCritic.__init__ got unexpected arguments, which will be ignored: "
                + str([key for key in kwargs.keys()])
            )
        super().__init__()
        #parameter init##############################
        self.initializer = get_initializer(Asenetcfg.initializer)
        self.activation = get_activation(Asenetcfg.activation)
        self._ase_latent_shape =  Asecfg.ase_latent_shape
        self.separate = Asenetcfg.separate_disc
        self.mlp_units = Asenetcfg.mlp_units
        self.value_size = 1
        self.Spacecfg = Asenetcfg.Spacecfg
        
        amp_input_shape = (num_actor_obs, num_critic_obs)   #TODO
        #build network###############################
        
        #build actor and critic net##################
        actor_out_size, critic_out_size = self._build_actor_critic_net(num_actor_obs, self._ase_latent_shape)
        
        #build value net#############################
        self.value = torch.nn.Linear(critic_out_size, self.value_size)  # 价值层
        self.value_act = get_activation('none')
        #build action head############################
        self._build_action_head(actor_out_size, num_actions)
        
        mlp_init = self.initializer  # MLP初始化器
        cnn_init = self.initializer  # CNN初始化器
        
        
        #weight init#################################
        for m in self.modules():         
            if isinstance(m, nn.Conv2d) or isinstance(m, nn.Conv1d):
                cnn_init(m.weight)  # 初始化CNN权重
                if getattr(m, "bias", None) is not None:
                    torch.nn.init.zeros_(m.bias)  # 初始化CNN偏置
            if isinstance(m, nn.Linear):
                mlp_init(m.weight)  # 初始化MLP权重
                if getattr(m, "bias", None) is not None:
                    torch.nn.init.zeros_(m.bias)  # 初始化MLP偏置       

        self.actor_mlp.init_params()  # 初始化演员MLP参数
        self.critic_mlp.init_params()  # 初始化评论家MLP参数

        #build discriminator and encoder################
        self._build_disc(amp_input_shape)  # 构建判别器
        self._build_enc(amp_input_shape)  # 构建编码器

        return
        
    def _build_action_head(self, actor_out_size, num_actions):
        if self.Spacecfg.iscontinuous:
            self.mu = torch.nn.Linear(actor_out_size, num_actions)  # 连续动作的均值层
            self.mu_act = get_activation(self.Spacecfg.mu_activation)  # 均值激活函数none
            mu_init = get_initializer(self.Spacecfg.mu_init,self.mu.weight)  # 均值初始化器
            # 标准差初始化器const_initializer ,nn.init.constant_
            sigma_init = get_initializer(self.Spacecfg.sigma_init,self.sigma,self.Spacecfg.sigma_val)  
            self.sigma_act = get_activation(self.Spacecfg.sigma_activation)  # 标准差激活函数none
            if (not self.Spacecfg.learn_sigma):
                self.sigma = nn.Parameter(torch.zeros(num_actions, requires_grad=False, dtype=torch.float32), requires_grad=False)  # 固定标准差
            elif  self.Spacecfg.fixed_sigma:
                self.sigma = nn.Parameter(torch.zeros(num_actions, requires_grad=True, dtype=torch.float32), requires_grad=True)  # 可学习的标准差
            else:
                self.sigma = torch.nn.Linear(actor_out_size, num_actions)  # 动态标准差
            
            #initialize
            mu_init(self.mu.weight)  # 初始化均值层权重
            if self.Spacecfg.fixed_sigma:
                sigma_init(self.sigma)  # 初始化固定标准差
            else:
                sigma_init(self.sigma.weight)  # 初始化动态标准差权重
        
    def _build_actor_critic_net(self, input_shape, ase_latent_shape):
        style_units = [512, 256]  # 风格单元
        style_dim = ase_latent_shape[-1]  # 风格维度

        self.actor_cnn = nn.Sequential()  # 演员CNN
        self.critic_cnn = nn.Sequential()  # 评论家CNN
        
        act_fn = self.activation  # 激活函数是一个relu class
        initializer = self.initializer  # 初始化器

        self.actor_mlp = AMPStyleCatNet1(
            obs_size=input_shape[-1],
            ase_latent_size=ase_latent_shape[-1],
            units=self.mlp_units,
            activation=act_fn,
            style_units=style_units,
            style_dim=style_dim,
            initializer=initializer
        )  # 演员MLP

        if self.separate:
            self.critic_mlp = AMPMLPNet(
                obs_size=input_shape[-1],
                ase_latent_size=ase_latent_shape[-1],
                units=self.mlp_units,
                activation=act_fn,
                initializer=initializer
            )  # 评论家MLP

        actor_out_size = self.actor_mlp.get_out_size()  # 演员输出大小
        critic_out_size = self.critic_mlp.get_out_size()  # 评论家输出大小

        return actor_out_size, critic_out_size

    @staticmethod
    # not used at the moment
    def init_weights(sequential, scales):
        [
            torch.nn.init.orthogonal_(module.weight, gain=scales[idx])
            for idx, module in enumerate(mod for mod in sequential if isinstance(mod, nn.Linear))
        ]

    def reset(self, dones=None):
        pass

    def forward(self):
        raise NotImplementedError
    @property
    def vector_z_e(self):
        return self.z_e

    @property
    def vector_z_q(self):
        return self.z_q
    @property
    def encode_one_hot(self):
        return self.one_hot
    
    @property
    def action_mean(self):
        return self.distribution.mean

    @property
    def action_std(self):
        return self.distribution.stddev

    @property
    def entropy(self):
        return self.distribution.entropy().sum(dim=-1)

    def update_distribution(self, observations):

        # 使用均值和标准差创建一个正态分布对象
        # 其中标准差为均值乘以0（即不改变均值）再加上self.std
        self.distribution = Normal(mean,self.std)
        #print(f"Distribution: {self.distribution}")
        return mean
    def act(self, observations, **kwargs):
        mean = self.update_distribution(observations)

        return self.distribution.sample()
    
    
    def get_actions_log_prob(self, actions):
        return self.distribution.log_prob(actions).sum(dim=-1)
    
    def get_codebook_embeddings(self):
        return self.codebook.weight    

    def act_inference(self, observations):
        actions_mean = self.update_distribution(observations)
        return actions_mean

    def evaluate(self, critic_observations, **kwargs):
        value = self.critic(critic_observations)
        return value


def get_activation(act_name):
    if act_name == "elu":
        return nn.ELU()
    elif act_name == "selu":
        return nn.SELU()
    elif act_name == "relu":
        return nn.ReLU()
    elif act_name == "crelu":
        return nn.CReLU()
    elif act_name == "lrelu":
        return nn.LeakyReLU()
    elif act_name == "tanh":
        return nn.Tanh()
    elif act_name == "sigmoid":
        return nn.Sigmoid()
    elif act_name == "none":
        return nn.Identity()
    else:
        print("invalid activation function!")
        return None

def get_initializer(initialization, **kwargs):
    initializers = {
        "xavier_uniform": lambda v: nn.init.xavier_uniform_(v, **kwargs),
        "xavier_normal": lambda v: nn.init.xavier_normal_(v, **kwargs),
        "const_initializer": lambda v: nn.init.constant_(v, **kwargs),
        "kaiming_uniform": lambda v: nn.init.kaiming_uniform_(v, **kwargs),
        "kaiming_normal": lambda v: nn.init.kaiming_normal_(v, **kwargs),
        "orthogonal": lambda v: nn.init.orthogonal_(v, **kwargs),
        "normal": lambda v: nn.init.normal_(v, **kwargs),
        "default": lambda v: v  # nn.Identity 不是一个初始化函数，这里直接返回输入
    }
    
    return initializers.get(initialization, lambda v: (print("invalid initializer function"), None))  # 返回默认处理


class AMPMLPNet(torch.nn.Module):
    def __init__(self, obs_size, ase_latent_size, units, activation, initializer):
        super().__init__()  # 调用父类的初始化方法

        input_size = obs_size + ase_latent_size  # 计算输入大小
        print('build amp mlp net:', input_size)  # 打印构建信息
        
        self._units = units  # 存储单元列表
        self._initializer = initializer  # 存储初始化器
        self._mlp = []  # 初始化MLP层列表

        in_size = input_size  # 当前输入大小
        for i in range(len(units)):
            unit = units[i]  # 当前单元大小
            curr_dense = torch.nn.Linear(in_size, unit)  # 创建线性层
            self._mlp.append(curr_dense)  # 添加线性层到列表
            self._mlp.append(activation)  # 添加激活函数到列表
            in_size = unit  # 更新当前输入大小

        self._mlp = nn.Sequential(*self._mlp)  # 将列表转换为Sequential模块
        self.init_params()  # 初始化参数
        return

    def forward(self, obs, latent, skip_style):
        inputs = [obs, latent]  # 输入列表
        input = torch.cat(inputs, dim=-1)  # 拼接输入
        output = self._mlp(input)  # 前向传播
        return output

    def init_params(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):  # 如果是线性层
                self._initializer(m.weight)  # 初始化权重
                if getattr(m, "bias", None) is not None:  # 如果有偏置
                    torch.nn.init.zeros_(m.bias)  # 初始化偏置
        return

    def get_out_size(self):
        out_size = self._units[-1]  # 获取输出大小
        return out_size


class AMPStyleCatNet1(torch.nn.Module):
    def __init__(self, obs_size, ase_latent_size, units, activation,
                 style_units, style_dim, initializer):
        super().__init__()  # 调用父类的初始化方法

        print('build amp style cat net:', obs_size, ase_latent_size)  # 打印构建信息
            
        self._activation = activation  # 存储激活函数RELU
        
        self._initializer = initializer  # 存储初始化器nn.Identity()，不对输入数据进行任何变换，而是直接将输入作为输出返回
        
        self._dense_layers = []  # 是
        self._units = units  # 存储单元列表
        self._style_dim = style_dim  # 存储风格维度
        self._style_activation = torch.tanh  # 存储风格激活函数

        self._style_mlp = self._build_style_mlp(style_units, ase_latent_size)  # 构建风格MLP
        self._style_dense = torch.nn.Linear(style_units[-1], style_dim)  # 构建风格线性层

        in_size = obs_size + style_dim  # 计算输入大小
        for i in range(len(units)):
            unit = units[i]  # 当前单元大小
            out_size = unit  # 输出大小
            curr_dense = torch.nn.Linear(in_size, out_size)  # 创建线性层
            self._dense_layers.append(curr_dense)  # 添加线性层到列表
            
            in_size = out_size  # 更新当前输入大小

        self._dense_layers = nn.ModuleList(self._dense_layers)  # 将列表转换为ModuleList

        self.init_params()  # 初始化参数
        return

    def forward(self, obs, latent, skip_style):
        if (skip_style):
            style = latent  # 如果跳过风格，则直接使用latent
        else:
            style = self.eval_style(latent)  # 否则计算风格

        h = torch.cat([obs, style], dim=-1)  # 拼接观测和风格

        for i in range(len(self._dense_layers)):
            curr_dense = self._dense_layers[i]  # 当前线性层
            h = curr_dense(h)  # 前向传播
            h = self._activation(h)  # 激活

        return h

    def eval_style(self, latent):
        style_h = self._style_mlp(latent)  # 风格MLP输出
        style = self._style_dense(style_h)  # 风格线性层输出
        style = self._style_activation(style)  # 风格激活
        return style

    def init_params(self):
        scale_init_range = 1.0  # 初始化范围

        for m in self.modules():
            if isinstance(m, nn.Linear):  # 如果是线性层
                self._initializer(m.weight)  # 初始化权重
                if getattr(m, "bias", None) is not None:  # 如果有偏置
                    torch.nn.init.zeros_(m.bias)  # 初始化偏置

        nn.init.uniform_(self._style_dense.weight, -scale_init_range, scale_init_range)  # 初始化风格线性层权重
        return

    def get_out_size(self):
        out_size = self._units[-1]  # 获取输出大小
        return out_size

    def _build_style_mlp(self, style_units, input_size):
        in_size = input_size  # 当前输入大小
        layers = []  # 初始化层列表
        for unit in style_units:
            layers.append(torch.nn.Linear(in_size, unit))  # 添加线性层
            layers.append(self._activation)  # 添加激活函数
            in_size = unit  # 更新当前输入大小

        enc_mlp = nn.Sequential(*layers)  # 将列表转换为Sequential模块
        return enc_mlp