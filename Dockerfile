FROM centos:7
ENV container docker
RUN (cd /lib/systemd/system/sysinit.target.wants/; for i in *; do [ $i == \
	systemd-tmpfiles-setup.service ] || rm -f $i; done); \
	rm -f /lib/systemd/system/multi-user.target.wants/*;\
	rm -f /etc/systemd/system/*.wants/*;\
	rm -f /lib/systemd/system/local-fs.target.wants/*; \
	rm -f /lib/systemd/system/sockets.target.wants/*udev*; \
	rm -f /lib/systemd/system/sockets.target.wants/*initctl*; \
	rm -f /lib/systemd/system/basic.target.wants/*;\
	rm -f /lib/systemd/system/anaconda.target.wants/*;
VOLUME [ "/sys/fs/cgroup" ]
CMD ["/usr/sbin/init"]



WORKDIR /code

# ソースコードコピー・モジュールのインストール
ADD . /code/
# RUN conda install -y mysqlclient && \
#     conda install -y -c bioconda bowtie gmap blast && \
#     pip install -r requirements.txt

RUN yum install -y httpd httpd-devel && \
  systemctl enable httpd.service

RUN yum install -y postfix && \
  systemctl enable postfix.service


RUN rpm -Uvh ftp://ftp.tu-chemnitz.de//.SAN0/pub/linux/dag/redhat/el6/en/x86_64/dag/RPMS/rpmforge-release-0.5.3-1.el6.rf.x86_64.rpm && \
  rpm -Uvh http://dev.mysql.com/get/mysql-community-release-el7-5.noarch.rpm


RUN yum install -y wget less gcc.x86_64 perl-core  perl-URI-Escape-XS perl-JSON-XS perl-XML-LibXML.x86_64 perl-DBD-MySQL.x86_64 perl-App-cpanminus perl-GD gd-devel.x86_64 mysql-community-client

RUN cpanm SVG CGI URI::Escape::XS Math::Trig JSON JSON::XS GD GD::Text::Wrap Bio::Seq

RUN  cp -r /code/htdocs /var/www/html/lims && \
  cp  -r /code/cgi-bin /var/www/cgi-bin/lims && \
  cp /code/htdocs/index.html.tmpl /var/www/html/lims/index.html && \
  cp /code/docker_resources/httpd.cgi.conf /etc/httpd/conf.d && \
  cp /code/docker_resources/main.conf.docker.tmpl /var/www/cgi-bin/lims/main.conf

RUN curl -LO https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/ncbi-blast-2.10.1+-x64-linux.tar.gz && \
  tar xvfz ncbi-blast-2.10.1+-x64-linux.tar.gz && \
  mkdir -p /var/www/cgi-bin/lims/blast+/bin/ && \
  cp ncbi-blast-2.10.1+/bin/* /var/www/cgi-bin/lims/blast+/bin/ && \
  rm -rf ncbi-blast-2.10.1+ ncbi-blast-2.10.1+-x64-linux.tar.gz


RUN mkdir -p /var/www/html/lims/data/tmp /var/www/html/lims/data/jobs && \
	chmod -R 777 /var/www/html/lims/data


EXPOSE 80
