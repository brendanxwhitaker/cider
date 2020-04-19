if [ ! -d "~/pkgs" ]; then
    mkdir ~/pkgs
fi
git clone https://github.com/paullouisageneau/libjuice.git ~/pkgs/libjuice
cd ~/pkgs/libjuice
sudo apt-get install nettle-dev
mkdir build
cd build
cmake -DUSE_NETTLE=1 ..
make
