import gymnasium as gym
import torch
import numpy as np
from copy import deepcopy


from config import args
from model import Actor , Critic
from REDQ import REDQ
from replay_buffer import ReplayBuffer
from learning_curve import LearningCurve



###### 建立環境 ######
env = gym.make(args.env_name)


###### 設定隨機種子 ######
np.random.seed(args.seed)
torch.manual_seed(args.seed)
env.reset(seed=args.seed)
env.action_space.seed(args.seed)


###### 確定維度 ######
state_dim = env.observation_space.shape[0]
action_dim = env.action_space.shape[0]
max_action = env.action_space.high


###### 初始化 actor 和 critic ######
actor = Actor(state_dim, action_dim, max_action).to(args.device)
actor_optimizer = torch.optim.Adam(actor.parameters(), lr=args.actor_learning_rate)

critics: list[Critic] = []
for i in range(args.critic_size):
    critic = Critic(state_dim, action_dim).to(args.device)
    critics.append(critic)

critic_targets = deepcopy(critics)

critic_optimizers: list[torch.optim.Adam] = []
for critic in critics:
    critic_optimizer = torch.optim.Adam(critic.parameters(), lr=args.critic_learning_rate)
    critic_optimizers.append(critic_optimizer)


###### 初始化 REDQ ######
redq = REDQ(action_dim)


###### 初始化 replay buffer ######
replay_buffer = ReplayBuffer()


###### 初始化 learning curve ######
learning_curve = LearningCurve(actor)


###### 初始化環境 ######
state , _ = env.reset()


###### 開始訓練 ######
for steps in range(args.max_steps):

    if steps < args.start_steps:  # 5000

        action = env.action_space.sample()  # 純隨機動作

    else:                         # 995000

        with torch.no_grad():
            state_ = torch.tensor(state, dtype=torch.float32, device=args.device)
            action , _ = actor.sample(state_)
        action = action.cpu().numpy()


    next_state , reward , done , reach_step_limit , _ = env.step(action)

    replay_buffer.push(state, action, next_state, reward, not done)

    if done or reach_step_limit:
        state , _ = env.reset()
    else:
        state = next_state


    if steps >= args.start_steps:

        redq.train(
            actor,
            critics,
            critic_targets,
            replay_buffer,
            actor_optimizer,
            critic_optimizers
        )


    learning_curve.add_step()



    if learning_curve.steps % args.test_performance_freq == 0:
        print(f"steps={learning_curve.learning_curve_steps[-1]}  score={learning_curve.learning_curve_scores[-1]:.3f}")



###### 儲存結果 ######
if args.save_result == True:
    learning_curve.save()


print("Finish")


