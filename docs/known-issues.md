#TabPy Known Issues

## Setup

### CentOS Specific Issues

For Python on CentOS you may need to rebuild it with enabling all the features.
Also you'll need `pip` and `setuptools` for TabPy startup script to work.
To install and enable all the required prerequisites follow the steps:

```sh
sudo yum update
sudo yum groupinstall -y "Development tools"
sudo yum install -y zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel expat-devel
sudo yum install -y wget
wget http://python.org/ftp/python/3.6.5/Python-3.6.5.tar.xz
tar xf Python-3.6.5.tar.xz
cd Python-3.6.5
```

Edit `./Module/Setup` file uncommenting line 
`#zlib zlibmodule.c -I$(prefix)/include -L$(exec_prefix)/lib -lz` 
(remove pound sign).

Continue the steps:

```sh
./configure --prefix=/usr/local --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib"
make
sudo make altinstall
wget https://bootstrap.pypa.io/get-pip.py
python get-pip.py
```
