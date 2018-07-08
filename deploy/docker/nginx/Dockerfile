FROM nginx:1.15

RUN apt-get update
RUN apt-get install -y wget
RUN wget https://dl.eff.org/certbot-auto
RUN chmod a+x ./certbot-auto
RUN ./certbot-auto -n --nginx --install-only