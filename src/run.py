#!/usr/bin/env python
import os
import experiment
import gym
import numpy as np
import filter_env
import ddpg
import wolpertinger as wp
import fmpolicy as fmp
import tensorflow as tf
import time
flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_boolean('upload',False,'upload to gym (requires evironment variable OPENAI_GYM_API_KEY)')
flags.DEFINE_string('env','','gym environment')
# flags.DEFINE_integer('train',10000,'training time between tests. use 0 for test run only')
# flags.DEFINE_integer('test',10000,'testing time between training')
flags.DEFINE_integer('train',10,'training time between tests. use 0 for test run only')
flags.DEFINE_integer('test',1,'testing time between training')
flags.DEFINE_integer('tmax',10000,'maximum timesteps per episode')
flags.DEFINE_bool('random',False,'use random agent')
flags.DEFINE_bool('tot',False,'train on test data')
flags.DEFINE_integer('total',1000000,'total training time')
flags.DEFINE_float('monitor',.05,'probability of monitoring a test episode')
flags.DEFINE_bool('wolpertinger',False,'Train critic using the full Wolpertinger policy')
flags.DEFINE_bool('egreedy_expl',False,'Perform epsilon greedy exploration')
flags.DEFINE_float('epsilon', 0.2, 'epsilon probability for an epsilon greedy exploration')
flags.DEFINE_integer('wp_total_actions', 1000000, 'total number of actions to discretize under the Wolpertinger policy')
flags.DEFINE_string('wp_action_set_file', 'data/embeddings-movielens1m.csv', 'Embeddings file for Knn index generation')
flags.DEFINE_bool('skip_space_norm', False, 'Skip action space normalization')

flags.DEFINE_bool('fmpolicy', False, 'Train critic using the FM Policy')
# ...
# TODO: make command line options

VERSION = 'DDPG-v0'
GYM_ALGO_ID = 'alg_TmtzkcfSauZoBF97o9aQ'

if FLAGS.random:
  FLAGS.train = 0

class Experiment:
  def run(self):
    self.t_train = 0
    self.t_test = 0

    # create filtered environment
    self.env = filter_env.makeFilteredEnv(gym.make(FLAGS.env), skip_space_norm=FLAGS.skip_space_norm,
                                          wolpertinger=FLAGS.wolpertinger)
    # self.env = gym.make(FLAGS.env)
    
    self.env.monitor.start(FLAGS.outdir+'/monitor/',video_callable=lambda _: False)
    # self.env.monitor.start(FLAGS.outdir+'/monitor/',video_callable=lambda _: True)
    gym.logger.setLevel(gym.logging.WARNING)

    dimO = self.env.observation_space.shape
    dimA = self.env.action_space.shape
    print(dimO,dimA)

    import pprint
    pprint.pprint(self.env.spec.__dict__,width=1)

    wolp = None
    if FLAGS.wolpertinger:
        wolp = wp.Wolpertinger(self.env, i=FLAGS.wp_total_actions,
                               action_set=wp.load_action_set(FLAGS.wp_action_set_file,
                                                             i=FLAGS.wp_total_actions, action_shape=dimA[0])
                               ).g
    elif FLAGS.fmpolicy:
        wolp = fmp.FMPolicy(self.env).g

    self.agent = ddpg.Agent(dimO=dimO, dimA=dimA, custom_policy=FLAGS.wolpertinger or FLAGS.fmpolicy,
                            env_dtype=str(self.env.action_space.high.dtype))

    returns = []

    # main loop
    while self.t_train < FLAGS.total:

      # test
      T = self.t_test
      R = []
      if self.t_train - T > 0 or FLAGS.train == 0:
        while self.t_test - T < FLAGS.test:
          R.append(self.run_episode(test=True, monitor=(self.t_test - T < FLAGS.monitor * FLAGS.test), custom_policy=wolp))
          self.t_test += 1
        avr = np.mean(R)
        # print('Average test return\t{} after {} timesteps of training'.format(avr,self.t_train))
        with open(os.path.join(FLAGS.outdir, "output.log"), mode='a') as f:
          # f.write('Average test return\t{} after {} timesteps of training\n'.format(avr, self.t_train))
          f.write('Average test return\t{} after {} timesteps\n'.format(avr, self.t_train + FLAGS.test))
        # save return
        returns.append((self.t_train, avr))
        np.save(FLAGS.outdir+"/returns.npy",returns)

        s = self.agent.checkpoint_session()
        with open(os.path.join(FLAGS.outdir, "output.log"), mode='a') as f:
            f.write('Checkpoint saved at {} \n'.format(s))

        # evaluate required number of episodes for gym and end training when above threshold
        if self.env.spec.reward_threshold is not None and avr > self.env.spec.reward_threshold:
          # TODO: it is supposed that when testing the model does not have to use the full wolpertinger policy?
          # TODO: to avoid the item not found exception in environment, custom policy is being sent to the run_episode
          avr = np.mean([self.run_episode(test=True, custom_policy=wolp) for _ in range(self.env.spec.trials)]) # trials???
          # print('TRIALS => Average return{}\t Reward Threshold {}'.format(avr, self.env.spec.reward_threshold))
          with open(os.path.join(FLAGS.outdir, "output.log"), mode='a') as f:
            f.write('TRIALS => Average return{}\t Reward Threshold {}\n'.format(avr, self.env.spec.reward_threshold))
          if avr > self.env.spec.reward_threshold:
            s = self.agent.checkpoint_session()
            with open(os.path.join(FLAGS.outdir, "output.log"), mode='a') as f:
                f.write('Final Checkpoint saved at {} \n'.format(s))
            break

      # train
      T = self.t_train
      R = []
      start_time = time.time()
      while self.t_train - T < FLAGS.train:
        R.append(self.run_episode(test=False, custom_policy=wolp))
        self.t_train += 1
      end_time = time.time()
      avr = np.mean(R)
      # print('Average training return\t{} after {} timesteps of training'.format(avr,self.t_train))
      with open(os.path.join(FLAGS.outdir, "output.log"), mode='a') as f:
        f.write('Average training return\t{} after {} timesteps of training. Batch time: {} sec.\n'
                .format(avr, self.t_train, end_time - start_time))

    self.env.monitor.close()
    f.close()
    # upload results
    if FLAGS.upload:
      gym.upload(FLAGS.outdir+"/monitor",algorithm_id = GYM_ALGO_ID)

  def run_episode(self,test=True,monitor=False, custom_policy=None):
    self.env.monitor.configure(lambda _: test and monitor)
    observation = self.env.reset()
    self.agent.reset(observation)
    R = 0. # return
    t = 1
    term = False
    # count = expl = 0
    while not term:
      # self.env.render(mode='human')

      if FLAGS.random: #use random agent
        action_to_perform = self.env.action_space.sample()
        self.agent.action = action_to_perform
        g_action = action_to_perform
      else:
        if FLAGS.egreedy_expl and np.random.uniform() < FLAGS.epsilon:
          action_to_perform = self.env.action_space.sample()
          g_action = action_to_perform
          # expl += 1
        else:
          # count += 1
          action = self.agent.act(test=test)

          # Run Wolpertinger discretization
          action_to_perform = action
          if (FLAGS.wolpertinger or FLAGS.fmpolicy) and custom_policy is not None:
            assert getattr(self.env, "obs_id", None) is not None, "Environment does not have obs_id attribute"
            A_k = custom_policy(action) if FLAGS.wolpertinger else custom_policy(self.env.obs_id, action)
            rew_g = R * np.ones(len(A_k), dtype=self.env.action_space.high.dtype)
            term_g = np.zeros(len(A_k), dtype=np.bool)
            # for i in range(len(A_k)):
            #   _, rew_g[i], term_g[i], _ = self.env.step(A_k[i])
            maxq_index = self.agent.wolpertinger_policy(action, A_k, rew_g, term_g)
            # g_action = A_k[maxq_index[0]]
            g_action = A_k[maxq_index]
            action_to_perform = g_action
            # res = self.agent.wolpertinger_policy(action, A_k, rew_g, term_g)
            # print('continuous action: {} discretized action: {}'.format(action, g_action))


      # observation, reward, term, info = self.env.step(action)
      observation, reward, term, info = self.env.step(action_to_perform)
      term = (t >= FLAGS.tmax) or term

      r_f = self.env.filter_reward(reward)
      self.agent.observe(r_f,term,observation,test = test and not FLAGS.tot, g_action=g_action)

      # if test:
      #   self.t_test += 1
      # else:
      #   self.t_train += 1

      R += reward
      t += 1

    # with open(os.path.join(FLAGS.outdir, "output.log"), mode='a') as f:
    #     f.write('Wolpertinger actions: {} Exploration actions: {}\n'.format(count, expl))
    print "<<=={} {}".format("TEST" if test else "TRAIN", self.t_test if test else self.t_train)
    self.env.render(mode='human')
    print ">>=={}".format("TEST" if test else "TRAIN")

    return R


def main():
  Experiment().run()

if __name__ == '__main__':
  os.environ['PATH'] += ':/usr/local/bin' # to be able to run under gym ffmpeg dependency under IDE
  experiment.run(main)
