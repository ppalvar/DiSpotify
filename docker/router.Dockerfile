FROM alpine:3.20

RUN echo "net.ipv4.ip_forward=1" | tee -a /etc/sysctl.conf
RUN sysctl -p

CMD /bin/sh