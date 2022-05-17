# gr-tacmac Installation

This is a rather detailed description of how to install the polarGFDM demo.
The final outcome should be a runnable demo.

## Prerequisites
The demo requires you to install a few libraries.

You'll probably want to follow the [Ansible](https://www.ansible.com/) approach for a user local install via [PyBOMBS](https://github.com/gnuradio/pybombs).
This step is simple. Just use the [ANT Ansible configuration](https://github.com/ant-uni-bremen/ansible).
You probably want the roles

- network-tooling
- gnuradio-cpp-dependencies
- scientific-python
- gnuradio-tooling
- common-python-pip
- uhd

However, it should be noted that this is the approach to install all these dependencies system-wide.
The prefered approach to install GNU Radio with UHD and VOLK, and later on all OOT modules, is a local install.

## Installation options

First off, there are multiple approaches to install the demo.
We need to choose one option.

- GNU Radio package install
- Conda install
- PyBOMBS install

All approaches come with pros and cons. Choose one and stick with it. The GNU Radio package install will certainly interfere with your other approaches.
In case of issues: If the "solution" mentions SWIG, it is not the solution but obsolete.

### GNU Radio package

Use the [GNU Radio Ubuntu PPA](https://wiki.gnuradio.org/index.php/InstallingGR#Ubuntu_PPA_Installation).
Use GNU Radio 3.9 or newer. Do not look back to any older releases. They are not supported. And obviously will never be.

This will get you a GNU Radio installation with UHD and VOLK.

#### Pros

- few commands to install
- fewest possible obstacles now. FUBAR system later.

#### Cons

- System-wide installation interferes with other users and installs. This will bite you later.
- Using this path for any OOTs will most certainly fail.
- You can't change anything in GNU Radio itself.
- Some system specific optimizations are missing.

### Conda install

The GNU Radio recommended path for a user install is via [Conda](https://wiki.gnuradio.org/index.php/CondaInstall).
It will give you a nice and clean install with defined environments.
You can swap between different versions with conda activate commands.


#### Pros

- simple installation.
- integrates well with Python and Conda.
- user local installation -> you won't wreck the system for everyone.

#### Cons

- Another install of all the dependencies etc. on your system.
- Installing OOTs etc. is more error-prone. Which dependencies do you use? Where are they installed?



### PyBOMBS install

For historical reasons, this is the approach I use [PyBOMBS installation](https://github.com/gnuradio/pybombs).

#### Pros

- Picks up system installed libraries where possible.
- Fully supports user local installation -> you won't wreck the system for everyone.
- Gives you a simple system to switch between local installs.

#### Cons

- Initial development did not follow new GNU Radio versions.
- Recipes are possibly out of date.
- Updates after initial installation possibly require manual work.

