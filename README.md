# University College London - MSc Thesis Project #

# Collaborative Filtering using a Deep Reinforcement Learning Approach

******

Author
======

* [Santiago Gonzalez Toral](hernan.toral.15@ucl.ac.uk) | MSc WSBDA Candidate

Supervisors
======

* [PhD. Jun Wang]() | MSc WSBDA Director & Senior Lecturer


Overview
======

.. contents:: **Contents of this document**
   :depth: 2

System Requirements and Setup
======

- `Python 2.7`
- `Virtualenv`
- `Tensorflow`
- `Jupyter notebook`


Dependencies
======

Installation
======

```bash
$ git clone https://santteegt@bitbucket.org/msc_drl/ucl-cfdrl-msc.git
$ git submodule update --init --recursive

$ cd ucl-cfdrl-msc
$ mkdir .venv
$ virtualenv --system-site-packages --python=python2.7 .venv/
$ source .venv/bin/activate

(venv)$ cd gym
(venv)$ pip install -e .
# installation for Mac OS X. For other platforms, refer to https://www.tensorflow.org/versions/r0.9/get_started/os_setup.html#virtualenv-installation
(venv)$ export TF_BINARY_URL=https://storage.googleapis.com/tensorflow/mac/tensorflow-0.9.0-py2-none-any.whl
(venv)$ pip install --upgrade $TF_BINARY_URL
```

Running the environment
======

```bash
(venv)$ cd src
(venv)$ mkdir ../ddpg-results
(venv)$ python run.py --outdir ../ddpg-results/experiment1 --env InvertedDoublePendulum-v1
```

License and Version
======