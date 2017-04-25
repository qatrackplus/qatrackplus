docker stop $(docker ps -a -q) && docker rm $(docker ps -a -q) && echo 'y' | docker volume prune
