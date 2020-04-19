rm sdp*
if [ ! -d "$HOME/pkgs" ]; then
    mkdir $HOME/pkgs
fi
if [ ! -d "$HOME/pkgs/libjuice" ]; then
    git clone https://github.com/paullouisageneau/libjuice.git $HOME/pkgs/libjuice
fi
cd $HOME/pkgs/libjuice
sudo apt-get install nettle-dev
if [ ! -d "build" ]; then
    mkdir build
fi
cd build
cmake -DUSE_NETTLE=1 ..
make
