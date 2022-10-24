# coding=utf-8
# Copyright 2022 The TensorFlow Datasets Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utils common to Atari datasets."""

from __future__ import annotations

import dataclasses
from typing import Any, Dict

from tensorflow_datasets.core.utils.lazy_imports_utils import tensorflow as tf
import tensorflow_datasets.public_api as tfds

_ATARI_DESCRIPTION = """
We are releasing a large and diverse dataset of gameplay following the protocol
described by [Agarwal et al., 2020](https://arxiv.org/abs/1907.04543), which can
be used to evaluate several discrete offline RL algorithms. The dataset is
generated by running an online DQN agent and recording transitions from its
replay during training with sticky actions
[Machado et al., 2018](https://arxiv.org/abs/1709.06009). As stated in
[Agarwal et al., 2020](https://arxiv.org/abs/1907.04543), for each game we use
data from five runs with 50 million transitions each. We release datasets for 46
Atari games. For details on how the dataset was generated, please refer to the
paper.

Atari is a standard RL benchmark. We recommend you to try offline RL methods on
Atari if you are interested in comparing your approach to other state of the art
offline RL methods with discrete actions.

The reward of each step is clipped (obtained with [-1, 1] clipping) and the 
episode includes the sum of the clipped reward per episode.
"""

_CITATION = """
@misc{gulcehre2020rl,
    title={RL Unplugged: Benchmarks for Offline Reinforcement Learning},
    author={Caglar Gulcehre and Ziyu Wang and Alexander Novikov and Tom Le Paine
        and  Sergio Gómez Colmenarejo and Konrad Zolna and Rishabh Agarwal and
        Josh Merel and Daniel Mankowitz and Cosmin Paduraru and Gabriel
        Dulac-Arnold and Jerry Li and Mohammad Norouzi and Matt Hoffman and
        Ofir Nachum and George Tucker and Nicolas Heess and Nando deFreitas},
    year={2020},
    eprint={2006.13888},
    archivePrefix={arXiv},
    primaryClass={cs.LG}
}
"""


def description():
  return _ATARI_DESCRIPTION


def citation():
  return _CITATION


@dataclasses.dataclass
class BuilderConfig(tfds.core.BuilderConfig):
  """Configuration of the task.

  Attributes:
    game: name of the Atari game
    run: name of the game run
  """
  game: str = 'Asterix'
  run: int = 1


_GAMES = [
    'Alien',
    'Amidar',
    'Assault',
    'Asterix',
    'Atlantis',
    'BankHeist',
    'BattleZone',
    'BeamRider',
    'Boxing',
    'Breakout',
    'Carnival',
    'Centipede',
    'ChopperCommand',
    'CrazyClimber',
    'DemonAttack',
    'DoubleDunk',
    'Enduro',
    'FishingDerby',
    'Freeway',
    'Frostbite',
    'Gopher',
    'Gravitar',
    'Hero',
    'IceHockey',
    'Jamesbond',
    'Kangaroo',
    'Krull',
    'KungFuMaster',
    'MsPacman',
    'NameThisGame',
    'Phoenix',
    'Pong',
    'Pooyan',
    'Qbert',
    'Riverraid',
    'RoadRunner',
    'Robotank',
    'Seaquest',
    'SpaceInvaders',
    'StarGunner',
    'TimePilot',
    'UpNDown',
    'VideoPinball',
    'WizardOfWor',
    'YarsRevenge',
    'Zaxxon',
]

_SHORT_GAMES = [
    'Carnival',
    'Gravitar',
    'StarGunner',
]


# Note that rewards and episode_return are actually also clipped.
def _feature_description():
  return {
      'checkpoint_idx':
          tf.io.FixedLenFeature([], tf.int64),
      'episode_idx':
          tf.io.FixedLenFeature([], tf.int64),
      'episode_return':
          tf.io.FixedLenFeature([], tf.float32),
      'clipped_episode_return':
          tf.io.FixedLenFeature([], tf.float32),
      'observations':
          tf.io.FixedLenSequenceFeature([], tf.string, allow_missing=True),
      'actions':
          tf.io.FixedLenSequenceFeature([], tf.int64, allow_missing=True),
      'unclipped_rewards':
          tf.io.FixedLenSequenceFeature([], tf.float32, allow_missing=True),
      'clipped_rewards':
          tf.io.FixedLenSequenceFeature([], tf.float32, allow_missing=True),
      'discounts':
          tf.io.FixedLenSequenceFeature([], tf.float32, allow_missing=True),
  }


def num_shards(game: str, shards: int) -> int:
  if game in _SHORT_GAMES:
    return shards - 1
  else:
    return shards


def builder_configs():
  configs = []
  for game in _GAMES:
    for run in range(1, 6):
      # pytype: disable=wrong-keyword-args
      configs.append(
          BuilderConfig(name=f'{game}_run_{run}', game=game, run=run))
      # pytype: enable=wrong-keyword-args
  return configs


def atari_example_to_rlds(tf_example: tf.train.Example) -> Dict[str, Any]:
  """Generates an RLDS episode from an Atari TF Example.

  Args:
    tf_example: example from an Atari dataset.

  Returns:
    RLDS episode.
  """

  data = tf.io.parse_single_example(tf_example, _feature_description())
  episode_length = tf.size(data['actions'])
  is_first = tf.concat([[True], [False] * tf.ones(episode_length - 1)], axis=0)
  is_last = tf.concat([[False] * tf.ones(episode_length - 1), [True]], axis=0)

  is_terminal = [False] * tf.ones_like(data['actions'])
  discounts = data['discounts']
  if discounts[-1] == 0.:
    is_terminal = tf.concat(
        [[False] * tf.ones(episode_length - 1, tf.int64), [True]], axis=0)
    # If the episode ends in a terminal state, in the last step only the
    # observation has valid information (the terminal state).
    discounts = tf.concat([discounts[1:], [0.]], axis=0)
  episode = {
      # Episode Metadata
      'episode_id': data['episode_idx'],
      'checkpoint_id': data['checkpoint_idx'],
      'episode_return': data['episode_return'],
      'steps': {
          'observation': data['observations'],
          'action': data['actions'],
          'reward': data['unclipped_rewards'],
          'discount': discounts,
          'is_first': is_first,
          'is_last': is_last,
          'is_terminal': is_terminal,
      }
  }
  return episode


def file_prefix(prefix, run, game):
  return f'{prefix}/{game}/run_{run}'


def features_dict():
  return tfds.features.FeaturesDict({
      'steps':
          tfds.features.Dataset({
              'observation':
                  tfds.features.Image(
                      shape=(
                          84,
                          84,
                          1,
                      ), dtype=tf.uint8, encoding_format='png'),
              'action':
                  tf.int64,
              'reward':
                  tfds.features.Scalar(
                      dtype=tf.float32,
                      doc=tfds.features.Documentation(
                          desc='Clipped reward.', value_range='[-1, 1]')),
              'is_terminal':
                  tf.bool,
              'is_first':
                  tf.bool,
              'is_last':
                  tf.bool,
              'discount':
                  tf.float32,
          }),
      'checkpoint_id':
          tf.int64,
      'episode_id':
          tf.int64,
      'episode_return':
          tfds.features.Scalar(
              dtype=tf.float32,
              doc=tfds.features.Documentation(
                  desc='Sum of the clipped rewards.')),
  })


def episode_id(episode):
  return f'{episode["checkpoint_id"]}_{episode["episode_id"]}'
