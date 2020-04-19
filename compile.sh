gcc -o connect -I $HOME/pkgs/libjuice/include/ -L$HOME/pkgs/libjuice/build/ -ljuice src/peer$1.c src/utils.c src/handshake.c
