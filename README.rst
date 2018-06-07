======================================================================================
vmware-sexigraf-exporter - Additional vmware performance metric exporter for sexigraf
======================================================================================


What is this?
*************
``vmware-sexigraf-exporter`` provides an executable called ``vmware_sexigraf_exporter``.


Installation
************
*on most UNIX-like systems, you'll probably need to run the following
`install` commands as root or by using sudo*

**from source**

::

  pip install git+http://github.com/verdel/vmware-sexigraf-exporter

**or**

::

  git clone git://github.com/verdel/vmware-sexigraf-exporter.git
  cd vmware-sexigraf-exporter
  python setup.py install

as a result, the ``vmware_sexigraf_exporter`` executable will be installed into
a system ``bin`` directory

Usage
-----
::
    vmware_sexigraf_exporter --help
    usage: vmware_sexigraf_exporter.py [-h] -c CONFIG [--debug]

    Squid external acl blacklist helper

    optional arguments:
      -h, --help            show this help message and exit
      -c CONFIG, --config CONFIG
                            configuration file
      --debug
